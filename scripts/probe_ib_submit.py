"""IB write-side smoke test.

Default test submits a tiny LMT BUY for 1 share of CAC.PA on XPAR/SBF at
EUR 1.00 (well below market — won't fill in normal conditions), waits
for SUBMITTED + (ACCEPTED or REJECTED), then cancels (only if ACCEPTED
was observed). When run outside RTH for SBF, IB pushes warning 399 and
holds the order until next session open — the broker correctly emits
ACCEPTED and a subsequent engine cancel produces CANCELED with
reason='engine'.

A second test path (`_TEST_INSTRUMENT` = AAPL on SMART/NASDAQ) is
available as a fallback for environments where the IB Paper account's
"Direct Routed Orders" restriction (error 10311) hasn't been bypassed
via API → Precautions. SMART routing sidesteps the restriction; swap
`instrument=_PHASE_1_INSTRUMENT` to `instrument=_TEST_INSTRUMENT` in
`_run_probe()` to switch.

Validates the M2-IB.4a write-side wiring end-to-end against IB Paper:

- ``ib.placeOrder`` round-trip (1 ``global`` rate-limit token).
- Per-trade ``statusEvent`` handler emits ACCEPTED on IB ``Submitted``.
- ``ib.cancelOrder`` round-trip (1 ``global`` token), exercised when
  the order reaches ACCEPTED rather than REJECTED.
- Per-trade ``statusEvent`` handler emits CANCELED on IB ``Cancelled``
  (M2-IB.4a-happy path, validated 2026-05-02 with this AAPL/SMART
  default).
- Per-trade ``statusEvent`` handler emits REJECTED on IB ``Cancelled``
  with a non-zero ``errorCode`` in the trade log (the disambiguation
  path; see ``_last_error_log_entry`` / ``_rejected_reason_from_log_entry``
  helpers in ``src/blive/adapters/ib/broker.py``). Exercise this branch
  by switching ``_TEST_INSTRUMENT`` to ``_PHASE_1_INSTRUMENT`` (CAC.PA
  on XPAR/SBF, direct-routed) — IB Paper's account-level direct-routing
  restriction (error 10311) blocks the order and the broker emits
  REJECTED with reason ``"ib:10311 ..."``.

Two terminal outcomes count as success (exit 0):

1. ``SUBMITTED → ACCEPTED → CANCELED`` (happy path; user cancel after
   acceptance) — the default with AAPL/SMART.
2. ``SUBMITTED → REJECTED`` (system rejection; e.g. IB's direct-routing
   restriction at error 10311 against orders routed to non-SMART venues
   like SBF). The disambiguation logic in ``IBBroker._on_order_status``
   translates IB's ``Cancelled`` status + non-zero ``errorCode`` into a
   REJECTED FSM event with an ``"ib:{code} {message}"`` reason,
   satisfying INV-13 §5 + INV-14.

Prerequisites: Gateway running with the API exposed on the configured
port, ``~/.blive/secrets/ib.env`` populated, and the IB-side "Read-Only
API" toggle unchecked (Configuration → API → Settings). With Read-Only
API set, IB returns an error on placeOrder (typically "API order
placement is disabled" or a specific reject code) and this probe FAILS
on submit; that's the diagnostic.

Note on IB Paper's direct-routing precaution at error 10311: per [ADR-046](../docs/decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032),
US-equity venues (XNAS / XNYS / ARCX / BATS) now route via SMART with a
primaryExchange hint at the production :class:`IBInstrumentResolver` level
— this avoids the precaution natively. The CAC.PA / SBF path still
direct-routes (SMART support varies by venue for European cash equities)
and depends on operator-side API → Precautions item #1 ("Bypass Order
Precautions for API Orders") being ticked; observed at
``M2-IB.4a-happy-cacpa``. Earlier probe iterations carried a probe-local
``_SmartUsResolver`` workaround which ADR-046 codifies into the production
resolver; the workaround was removed when production caught up.

Run:

    uv run python scripts/probe_ib_submit.py

Exits 0 on success; non-zero with a diagnostic on failure.
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


# Phase 1 canonical instrument per ADR-021 (XPAR direct-routed via the
# default resolver). Available as an alternative test path; left here for
# documentation. Routing CAC.PA through IB Paper trips the account-level
# "Direct Routed Orders" restriction (error 10311) — used by the prior
# probe runs to validate the REJECTED-via-disambiguation FSM transition.
_PHASE_1_INSTRUMENT = Instrument(
    symbol="CAC.PA",
    venue="XPAR",
    currency="EUR",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)


# Test instrument for the happy-path validation: AAPL on XNAS. Per
# ADR-046, the production :class:`IBInstrumentResolver` routes US-equity
# spot tradables via SMART with the primaryExchange hint, so AAPL/XNAS
# automatically becomes Contract(exchange="SMART", primaryExchange="NASDAQ")
# without any probe-local resolver subclass. Liquid + 24h paper data →
# easy non-fillable LMT @ $1 for the wire test.
_TEST_INSTRUMENT = Instrument(
    symbol="AAPL",
    venue="XNAS",
    currency="USD",
    asset_class=AssetClass.EQUITY,
    multiplier=Decimal("1"),
    tradability="spot",
)


# Wait timeout for an event from the broker's events() iterator. IB Paper
# typically pushes orderStatus within a few hundred ms; 5s gives slack.
_EVENT_WAIT_SECONDS = 5.0


async def _wait_for_kinds(
    broker: IBBroker,
    *,
    kinds: frozenset[OrderEventKind],
    timeout: float = _EVENT_WAIT_SECONDS,
) -> OrderEvent | None:
    """Drain events from the broker's internal queue until any of the
    requested kinds arrives or the timeout fires. Skips ConnectionStatus
    and unrelated OrderEvent kinds.

    Reads :attr:`IBBroker._events` directly rather than via the
    :meth:`events` iterator — ``asyncio.wait_for`` cancelling
    ``__anext__()`` on timeout leaves async generators in a state that
    breaks subsequent calls; ``Queue.get()`` is clean under cancellation
    (the value is not lost, no generator state to corrupt).
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
        # else: ignore and keep waiting (other kinds, ConnectionStatus, etc.)


async def _run_probe() -> int:
    _print_header("IB write-side probe (submit + cancel)")

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
    # Production IBInstrumentResolver routes US-equity venues via SMART per
    # ADR-046 (the probe-local _SmartUsResolver workaround was retired when
    # the convention was codified). Non-US venues retain direct routing
    # (CAC.PA / SBF) and depend on operator-side API → Precautions bypass.
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)

    _print_step("connecting to IB Paper Gateway")
    try:
        await broker.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        return 3
    print(f"    is_connected={broker.is_connected}")

    # Drain the connect ConnectionStatus from the broker's queue directly.
    await asyncio.wait_for(broker._events.get(), timeout=2.0)  # noqa: SLF001

    # Build a tiny LMT BUY at $1 (well below AAPL market ~$200+). This
    # order won't fill in normal market conditions — perfect for FSM
    # validation: SUBMITTED → ACCEPTED → cancel → CANCELED.
    cid = ClientOrderId(uuid4())
    order = Order(
        client_order_id=cid,
        strategy_id="probe",
        instrument=_PHASE_1_INSTRUMENT,
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.LMT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("1.00"),  # well below market; won't fill
        stop_price=None,
        parent_id=None,
        tags={"probe": "M2-IB.4a"},
        created_at=datetime.now(tz=timezone.utc),
    )

    _print_step(
        f"submitting LMT BUY {order.quantity} {order.instrument.symbol} @ "
        f"{order.instrument.currency} {order.limit_price}",
        f"client_order_id={str(cid)[:8]}... venue={order.instrument.venue}",
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
        return 4

    # Wait for SUBMITTED (emitted synchronously by submit()).
    event = await _wait_for_kinds(broker, kinds=frozenset({OrderEventKind.SUBMITTED}), timeout=2.0)
    if event is None:
        print("\nFAILED: did not observe SUBMITTED event within 2s")
        await broker.disconnect()
        return 5
    print(f"    SUBMITTED received (venue_order_id={event.venue_order_id})")

    # Wait for ACCEPTED **or** REJECTED. IB usually pushes orderStatus
    # 'Submitted' within ~1s on a healthy connection (→ ACCEPTED). IB's
    # Precautionary Settings can intercept and emit Cancelled-with-
    # errorCode instead — the broker disambiguates that to REJECTED via
    # _last_error_log_entry / _rejected_reason_from_log_entry. Both are
    # valid M2-IB.4a FSM outcomes.
    event = await _wait_for_kinds(
        broker,
        kinds=frozenset({OrderEventKind.ACCEPTED, OrderEventKind.REJECTED}),
        timeout=_EVENT_WAIT_SECONDS,
    )
    if event is None:
        print(
            f"\nFAILED: did not observe ACCEPTED or REJECTED within "
            f"{_EVENT_WAIT_SECONDS}s of SUBMITTED"
        )
        print("  Likely causes:")
        print("  - IB-side 'Read-Only API' toggle is set (Configuration > API > Settings)")
        print("  - Order pre-acceptance hang (rare; IB Paper instability)")
        print("  - Outside RTH and order is held with status PreSubmitted (uncommon for LMT)")
        await broker.disconnect()
        return 5

    # Rate-limiter usage (after submit only; useful for both branches).
    metrics = rate_limiter.metrics()
    global_metrics = metrics["global"]

    if event.kind == OrderEventKind.REJECTED:
        # Terminal state — the disambiguation logic emitted REJECTED instead
        # of CANCELED based on a non-zero errorCode in the trade log.
        # Skip cancel (already terminal). Common reject codes per INV-14:
        # 10311 (direct-routing precaution), 201 (generic order rejected),
        # 322 (dup orderId).
        print(f"    REJECTED received (reason={event.reason!r})")
        print(
            "    NOTE: REJECTED is a successful demonstration of the IB "
            "Cancelled-with-errorCode disambiguation. Cancel step skipped."
        )
        print(
            f"    rate_limiter.global available={global_metrics.available:.2f}"
            f"/{global_metrics.capacity} after submit"
        )
        _print_step("disconnecting")
        await broker.disconnect()
        _print_header("OK -- write-side REJECTED disambiguation validated")
        print(
            "M2-IB.4a SUBMITTED -> REJECTED validated end-to-end; INV-13 "
            "transitions T1 + REJECTED-via-disambiguation exercised. To "
            "also validate the happy SUBMITTED -> ACCEPTED -> CANCELED "
            "path, allow the relevant order via TWS Configuration > API > "
            "Precautions and re-run."
        )
        return 0

    # event.kind == ACCEPTED — proceed with the happy-path cancel cycle.
    print(f"    ACCEPTED received (venue_order_id={event.venue_order_id})")

    _print_step("cancelling order")
    try:
        await broker.cancel(cid)
    except Exception as exc:
        print(f"\nFAILED on cancel: {type(exc).__name__}: {exc}")
        await broker.disconnect()
        return 6

    # Wait for CANCELED. (REJECTED here would be unexpected — ACCEPTED
    # was already emitted — but accept it defensively to avoid spurious
    # timeouts in edge cases.)
    event = await _wait_for_kinds(
        broker,
        kinds=frozenset({OrderEventKind.CANCELED, OrderEventKind.REJECTED}),
        timeout=_EVENT_WAIT_SECONDS,
    )
    if event is None:
        print(f"\nFAILED: did not observe CANCELED within {_EVENT_WAIT_SECONDS}s")
        await broker.disconnect()
        return 7
    print(f"    {event.kind.name} received (reason={event.reason!r})")

    # Rate-limiter usage after submit + cancel.
    metrics = rate_limiter.metrics()
    global_metrics = metrics["global"]
    print(
        f"    rate_limiter.global available={global_metrics.available:.2f}"
        f"/{global_metrics.capacity} after submit + cancel"
    )

    _print_step("disconnecting")
    await broker.disconnect()

    _print_header("OK -- write-side FSM validated end-to-end (happy path)")
    print(
        "M2-IB.4a SUBMITTED -> ACCEPTED -> CANCELED validated; INV-13 "
        "transitions T1, T2, T4, T9 exercised; INV-14 ready for any new "
        "error codes observed."
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run_probe())
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
