"""IB instrument-resolve smoke test.

Manual smoke test that exercises ``IBInstrumentResolver.resolve()``
against the live IB Paper Gateway. Resolves the Phase 1 instrument
(``CAC.PA`` ETF on Euronext Paris per [ADR-021](../docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf))
and prints the qualified Contract details.

Successful run is the trigger for two substrate flips:

- [ADR-032](../docs/decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract)
  PROPOSED → ACCEPTED (instrument resolution policy validated by
  behaviour).
- [DD-7](../docs/dd/instrument_dictionary.md) DRAFT → STABLE (the
  ``Instrument`` ↔ ``Contract`` mapping has been empirically verified).

Prerequisites — same as :mod:`scripts.probe_ib_handshake`, plus the IB
Paper account must hold a valid (or at least subscribable)
``CAC.PA`` market-data tier (delayed data is sufficient for
``qualifyContractsAsync`` since it queries the contract definition, not
prices).

Run:

    uv run python scripts/probe_ib_resolve_contract.py

Exits 0 on success; non-zero with a diagnostic on failure.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
)
from blive.adapters.ib.instrument_resolver import (
    IBInstrumentResolver,
    InstrumentAmbiguous,
    InstrumentNotResolvable,
)
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.types import AssetClass, Instrument


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_step(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"  • {label}{suffix}")


# Phase 1 instrument per ADR-021 (CAC ETF proxy on Euronext Paris).
# tradability=spot is the default; explicit here for clarity.
_PHASE_1_INSTRUMENT = Instrument(
    symbol="CAC.PA",
    venue="XPAR",
    currency="EUR",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)


async def _run_probe() -> int:
    _print_header("IB instrument-resolve probe")

    # Step 1: load credentials.
    _print_step("loading IBCredentials from ~/.blive/secrets/ib.env / env")
    try:
        credentials = IBCredentials.load()
    except CredentialsMissing as exc:
        print(f"\nFAILED: {exc}")
        return 2
    except ValueError as exc:
        print(f"\nFAILED: invalid credentials value — {exc}")
        return 2

    print(
        f"    host={credentials.host} port={credentials.port} "
        f"client_id={credentials.client_id} account_id=[REDACTED]"
    )
    if credentials.account_id == "replace-with-your-ib-paper-account-id":
        print("\nFAILED: IB_PAPER_ACCOUNT_ID is still the template placeholder.")
        return 2

    # Step 2: connect.
    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)

    _print_step("connecting to IB Paper Gateway")
    try:
        await client.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        return 3
    print(f"    is_connected={client.is_connected}")

    # Step 3: resolve.
    started_at = datetime.now(tz=timezone.utc)
    _print_step("resolving Instrument(CAC.PA / XPAR / EUR / ETF / spot) — qualifyContractsAsync")
    print(f"    instrument: {_PHASE_1_INSTRUMENT}")

    try:
        contract = resolver.to_contract(_PHASE_1_INSTRUMENT)
    except InstrumentNotResolvable as exc:
        print(f"\nFAILED at to_contract: {exc}")
        await client.disconnect()
        return 4

    print(
        f"    constructed contract: symbol={contract.symbol} secType={contract.secType} "
        f"exchange={contract.exchange} currency={contract.currency}"
    )

    try:
        conid = await resolver.resolve(_PHASE_1_INSTRUMENT)
    except InstrumentNotResolvable as exc:
        elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
        print(f"\nFAILED after {elapsed:.2f}s — {exc}")
        await client.disconnect()
        return 5
    except InstrumentAmbiguous as exc:
        elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
        print(f"\nFAILED after {elapsed:.2f}s — {exc}")
        for c in exc.candidates:
            print(
                f"    candidate: conId={c.conId} primaryExchange={c.primaryExchange} "
                f"currency={c.currency} symbol={c.symbol}"
            )
        await client.disconnect()
        return 6
    elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
    print(f"    resolved in {elapsed:.2f}s; conId={conid}")

    # Step 4: cache hit on second resolve (no second wire call).
    _print_step("verifying cache hit on second resolve")
    started_at = datetime.now(tz=timezone.utc)
    cached_conid = await resolver.resolve(_PHASE_1_INSTRUMENT)
    elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
    print(f"    cache lookup returned conId={cached_conid} in {elapsed * 1000:.2f}ms")
    if cached_conid != conid:
        print(f"\nFAILED: cache returned different conId ({cached_conid} != {conid})")
        await client.disconnect()
        return 7

    # Step 5: rate-limiter usage.
    metrics = rate_limiter.metrics()
    global_metrics = metrics["global"]
    print(
        f"    rate_limiter.global available={global_metrics.available:.2f}"
        f"/{global_metrics.capacity} after resolve"
    )

    # Step 6: disconnect.
    _print_step("disconnecting")
    await client.disconnect()
    print(f"    is_connected={client.is_connected}")

    _print_header("OK -- instrument resolve clean")
    print(
        "ADR-032 ready to flip PROPOSED -> ACCEPTED; DD-7 ready to flip "
        "DRAFT -> STABLE. Paste output to the agent for the substrate-flip "
        "commit."
    )
    print(f"\n    CAC.PA conId = {conid}")
    return 0


def main() -> int:
    try:
        return asyncio.run(_run_probe())
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
