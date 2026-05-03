"""PRIIPs validation probe — single-shot TQQQ submit during US RTH.

Validates the assumption load-bearing in
[ADR-047](../docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043)
that **IB error 201 with the PRIIPs / KID reason text is a hard regulatory
block, not a market-time artefact**. The 2026-05-03 M2-IB.6.1 wire run
that surfaced 104 PRIIPs / KID rejections happened on a Sunday (all
markets closed); the substitution to UK-listed analogues was justified
on the strength of the error-message *text*, not on independent verification
under different market conditions.

This probe submits **one** LMT BUY for 1 share of TQQQ at $1 (well below
market — won't fill if accepted) during **US RTH** (NYSE/NASDAQ open
13:30–20:00 UTC during US daylight time). Three possible outcomes:

1. **REJECTED with reason text containing "KID"** → ADR-047's PRIIPs
   premise is empirically validated; UK-listed substitution is correct.
   Proceed to LSE RTH validation Tuesday with confidence; ADR-048 stays
   load-bearing; INV-14 v0.5 is correct.
2. **REJECTED with different reason text** → market / precaution issue
   we mis-attributed to PRIIPs. Stop and re-investigate ADR-047 before
   proceeding.
3. **ACCEPTED (or filled)** → PRIIPs is somehow not enforced on this
   account in IB Paper. Major surprise. Cancel immediately, stop, and
   investigate before deciding whether to revert ADR-047.

The probe issues exactly one order. The cancel step (when applicable)
is symmetric with `scripts/probe_ib_submit.py`. No state is persisted;
nothing is committed; the answer is in the printed terminal block.

Operator prereqs:

- IB Gateway running on the configured port (default 4002 paper).
- "Read-Only API" unchecked (Configuration → API → Settings).
- ``~/.blive/secrets/ib.env`` populated with the operator's UK retail
  paper account (the same account class that surfaced the original
  PRIIPs rejection on 2026-05-03; PRIIPs is enforced per account-class).
- **Run during US RTH**: NYSE/NASDAQ Mon–Fri 13:30–20:00 UTC during
  US daylight saving (which 2026-05-04 is in). Outside RTH the probe
  becomes inconclusive — IB may surface different reason text for
  pre/post-RTH submission and we lose the signal we're after.

Usage::

    uv run python scripts/probe_tqqq_us_rth.py

Exit codes:

    0  PRIIPs / KID reason text observed (assumption validated; expected
       outcome — proceed to LSE RTH Tuesday)
    1  REJECTED with non-PRIIPs reason text (mis-attribution; stop)
    2  credentials / args / file-not-found
    3  IB Paper connect / network failure
    4  ACCEPTED / FILLED (PRIIPs not enforced — major surprise; stop)
    5  no terminal event observed (timeout; retry under cleaner conditions)
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
    IBInstrumentResolver,
)
from blive.adapters.ib.broker import IBBroker
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.events import OrderEvent
from blive.domain.types import (
    AssetClass,
    ClientOrderId,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
    OrderType,
    TimeInForce,
)


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_step(label: str, detail: str = "") -> None:
    suffix = f" -- {detail}" if detail else ""
    print(f"  - {label}{suffix}")


# Original ADR-043 universe — TQQQ on NASDAQ. Routes via SMART per ADR-046
# (the production IBInstrumentResolver maps XNAS + ETF → SMART/NASDAQ).
# If PRIIPs is the load-bearing constraint (per ADR-047), this submission
# rejects with error 201 reason text containing "KID" regardless of
# whether SMART routing is in play — PRIIPs enforcement is at the broker's
# order-acceptance layer, before the order reaches any exchange.
_TQQQ = Instrument(
    symbol="TQQQ",
    venue="XNAS",
    currency="USD",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)


# IB Paper typically pushes orderStatus within a few hundred ms during
# RTH; 5s is generous.
_EVENT_WAIT_SECONDS = 5.0


# Reason-text fragments we treat as evidence of PRIIPs / KID enforcement.
# Lowercased substring match against the broker's `event.reason` (which
# the broker formats as ``"ib:201 {message}"`` per INV-14 v0.5).
_PRIIPS_REASON_FRAGMENTS: tuple[str, ...] = (
    "kid in english",
    "language approved for your country",
    "customer ineligible",
    "no trading permission",
)


async def _wait_for_kinds(
    broker: IBBroker,
    *,
    kinds: frozenset[OrderEventKind],
    timeout: float = _EVENT_WAIT_SECONDS,
) -> OrderEvent | None:
    """Mirror of `probe_ib_submit._wait_for_kinds` — drains the broker's
    internal event queue until any of the requested kinds arrives or the
    timeout fires. Direct queue access (not the async-iterator) so cancel-
    on-timeout doesn't corrupt generator state.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    queue = broker._events  # noqa: SLF001 — probe-only direct access
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return None
        try:
            event = await asyncio.wait_for(queue.get(), timeout=remaining)
        except asyncio.TimeoutError:
            return None
        if isinstance(event, OrderEvent) and event.kind in kinds:
            return event


def _classify_reason(reason: str | None) -> str:
    """Return one of {"priips", "other-rejection", "no-reason"}.

    Used to choose the exit code + diagnostic message. The broker's
    reason format is ``"ib:201 {message}"``; we normalize-lower and
    substring-search for the PRIIPs fragments.
    """
    if not reason:
        return "no-reason"
    lowered = reason.lower()
    if any(frag in lowered for frag in _PRIIPS_REASON_FRAGMENTS):
        return "priips"
    return "other-rejection"


async def _run_probe() -> int:
    _print_header("PRIIPs validation probe (TQQQ during US RTH)")

    # Quick sanity-check: warn if the wall clock isn't roughly in US RTH.
    # Doesn't block — operator may want to probe pre/post-open for
    # diagnostic reasons. Just surfaces the assumption.
    now_utc = datetime.now(tz=timezone.utc)
    is_weekday = now_utc.weekday() < 5  # Mon-Fri
    is_us_rth = is_weekday and (
        (now_utc.hour > 13 or (now_utc.hour == 13 and now_utc.minute >= 30)) and now_utc.hour < 20
    )
    print(f"  current time UTC: {now_utc.isoformat(timespec='seconds')}")
    print(f"  weekday + within 13:30-20:00 UTC?  {is_us_rth}")
    if not is_us_rth:
        print(
            "  WARNING: not currently within US RTH (NYSE/NASDAQ 13:30-20:00 UTC,\n"
            "  Mon-Fri). Outside RTH IB may surface different reason text for\n"
            "  rejections — running anyway, but the signal may be inconclusive."
        )

    _print_step("loading IBCredentials from ~/.blive/secrets/ib.env / env")
    try:
        credentials = IBCredentials.load()
    except CredentialsMissing as exc:
        print(f"\nFAILED: {exc}")
        return 2
    except ValueError as exc:
        print(f"\nFAILED: invalid credentials value -- {exc}")
        return 2

    print(
        f"    host={credentials.host} port={credentials.port} "
        f"client_id={credentials.client_id} account_id=[REDACTED]"
    )
    if credentials.account_id == "replace-with-your-ib-paper-account-id":
        print("\nFAILED: IB_PAPER_ACCOUNT_ID is still the template placeholder.")
        return 2

    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)

    _print_step("connecting to IB Paper Gateway")
    try:
        await broker.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        return 3
    print(f"    is_connected={broker.is_connected}")

    # Drain the connect ConnectionStatus from the broker's queue.
    await asyncio.wait_for(broker._events.get(), timeout=2.0)  # noqa: SLF001

    # Tiny LMT BUY at $1 — well below TQQQ market (~$80-90 historically).
    # Won't fill if accepted; cancel cycle handles ACCEPTED outcome.
    cid = ClientOrderId(uuid4())
    order = Order(
        client_order_id=cid,
        strategy_id="probe-priips",
        instrument=_TQQQ,
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.LMT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("1.00"),  # well below market; won't fill
        stop_price=None,
        parent_id=None,
        tags={"probe": "priips-validation"},
        created_at=datetime.now(tz=timezone.utc),
    )

    _print_step(
        f"submitting LMT BUY {order.quantity} {order.instrument.symbol} @ "
        f"{order.instrument.currency} {order.limit_price}",
        f"client_order_id={str(cid)[:8]}... venue={order.instrument.venue} (SMART/NASDAQ per ADR-046)",
    )
    try:
        await broker.submit(order)
    except Exception as exc:
        print(f"\nFAILED on submit: {type(exc).__name__}: {exc}")
        if "Read-Only" in str(exc) or "API order placement" in str(exc):
            print(
                "  HINT: IB Gateway has 'Read-Only API' checked. Uncheck it "
                "under Configuration > API > Settings, then re-run."
            )
        await broker.disconnect()
        return 3

    # Wait for SUBMITTED (synchronous emit by submit()).
    event = await _wait_for_kinds(broker, kinds=frozenset({OrderEventKind.SUBMITTED}), timeout=2.0)
    if event is None:
        print("\nFAILED: did not observe SUBMITTED event within 2s")
        await broker.disconnect()
        return 5
    print(f"    SUBMITTED received (venue_order_id={event.venue_order_id})")

    # Wait for the actual broker decision: ACCEPTED, REJECTED, or CANCELED.
    # Include CANCELED defensively (some IB rejection paths surface as
    # Cancelled-with-zero-errorCode → CANCELED rather than REJECTED;
    # we treat both as outcome-relevant).
    event = await _wait_for_kinds(
        broker,
        kinds=frozenset(
            {
                OrderEventKind.ACCEPTED,
                OrderEventKind.REJECTED,
                OrderEventKind.CANCELED,
            }
        ),
        timeout=_EVENT_WAIT_SECONDS,
    )
    if event is None:
        print(
            f"\nFAILED: did not observe ACCEPTED / REJECTED / CANCELED within "
            f"{_EVENT_WAIT_SECONDS}s of SUBMITTED"
        )
        await broker.disconnect()
        return 5

    if event.kind == OrderEventKind.REJECTED:
        # The path we expect under ADR-047's premise: PRIIPs / KID reason
        # text in event.reason, surfaced via the broker's
        # _rejected_reason_from_log_entry helper from IB error 201.
        classification = _classify_reason(event.reason)
        print(f"    REJECTED received  reason={event.reason!r}")
        print(f"    classification: {classification}")
        await broker.disconnect()
        if classification == "priips":
            _print_header("OK -- ADR-047 PRIIPs premise empirically validated")
            print(
                "Reason text contains PRIIPs / KID fragments: the original\n"
                "TQQQ universe is genuinely blocked at the broker layer for\n"
                "this UK retail account, independent of market hours.\n"
                "Proceed with LSE RTH validation Tuesday 2026-05-05 against\n"
                "QQL3 / IBTL / IBTM (per ADR-047). ADR-048 PROPOSED stays\n"
                "load-bearing; flip to ACCEPTED after Tuesday's fills land."
            )
            return 0
        elif classification == "other-rejection":
            _print_header("STOP -- non-PRIIPs rejection")
            print(
                "Reason text does NOT contain PRIIPs / KID fragments. The\n"
                "M2-IB.6.1 rejection may have been mis-attributed. Capture\n"
                "this reason text and re-investigate ADR-047 before any\n"
                "further substrate edits or live runs."
            )
            return 1
        else:
            _print_header("INCONCLUSIVE -- REJECTED with no reason text")
            print(
                "Broker emitted REJECTED with no parseable reason. Likely a\n"
                "harness issue — re-run during cleanest US RTH window and\n"
                "capture the raw IB trade-log entry for analysis."
            )
            return 5

    if event.kind == OrderEventKind.CANCELED:
        # Less common in practice — a Cancelled-with-zero-errorCode would
        # land here. Capture for diagnostics; treat as inconclusive.
        print(f"    CANCELED received  reason={event.reason!r}")
        await broker.disconnect()
        _print_header("INCONCLUSIVE -- CANCELED before ACCEPTED")
        print(
            "Broker emitted CANCELED before ACCEPTED. This is unusual on\n"
            "submit and warrants inspection. Capture the IB trade-log entry\n"
            "and re-run."
        )
        return 5

    # event.kind == ACCEPTED — the surprising outcome. Cancel immediately
    # to avoid carrying the position any longer than needed; report.
    print(f"    ACCEPTED received  venue_order_id={event.venue_order_id}")
    _print_step("cancelling order (ACCEPTED outcome — cancelling to avoid exposure)")
    try:
        await broker.cancel(cid)
    except Exception as exc:
        print(f"\nWARNING: cancel raised {type(exc).__name__}: {exc} -- proceeding anyway")
    await _wait_for_kinds(
        broker,
        kinds=frozenset({OrderEventKind.CANCELED, OrderEventKind.REJECTED}),
        timeout=_EVENT_WAIT_SECONDS,
    )
    await broker.disconnect()
    _print_header("STOP -- TQQQ ACCEPTED on UK retail paper account")
    print(
        "ADR-047's PRIIPs premise appears to NOT be enforced under this\n"
        "wire path. Major surprise — possible causes:\n"
        "  - IB Paper relaxes PRIIPs vs IB Production\n"
        "  - account class is not actually 'UK retail' in IB's records\n"
        "  - reason-text quirk masked the real M2-IB.6.1 cause\n"
        "Stop and investigate before any further substrate or strategy work.\n"
        "If this persists, ADR-047 + ADR-048 PROPOSED need revisiting and\n"
        "the original TQQQ / TMF / IEF universe may still be in play."
    )
    return 4


def main() -> int:
    try:
        return asyncio.run(_run_probe())
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
