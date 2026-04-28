"""IB Gateway handshake smoke test.

Manual smoke test for the M2-IB.3 first-handshake prereq. Verifies that:

1. ``~/.blive/secrets/ib.env`` is populated correctly (per [ADR-035](../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets)).
2. IB Gateway / TWS is listening on the configured TCP port.
3. The 3-step TWS-API handshake (connect → ``nextValidId`` push → ack) completes.
4. ``IBClient`` can ``disconnect`` cleanly.

Not part of the unit-test suite — the unit tests cover the ``IBClient``
contract using ``MagicMock(spec=ib_async.IB)``. This script is the
*wire-level* counterpart, run manually by the operator before M2-IB.3
substrate-flips can land.

Per [ADR-040](../docs/decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway)
the expected deployment target is Windows host with native IB Gateway:

1. Install IB Gateway (offline installer) from the IB website.
2. Launch IB Gateway, log in to the paper account, leave running.
3. Edit ``~/.blive/secrets/ib.env`` and replace
   ``IB_PAPER_ACCOUNT_ID=replace-with-your-ib-paper-account-id`` with
   the actual paper account id (something like ``DUxxxxxxx``).
4. Run ``uv run python scripts/probe_ib_handshake.py``.

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
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_step(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"  • {label}{suffix}")


async def _run_probe() -> int:
    _print_header("IB Gateway handshake probe")

    # Step 1: load credentials.
    _print_step("loading IBCredentials from ~/.blive/secrets/ib.env / env")
    try:
        credentials = IBCredentials.load()
    except CredentialsMissing as exc:
        print(f"\nFAILED: {exc}")
        print("\nFix:")
        print("  - Ensure ~/.blive/secrets/ib.env exists and contains all four")
        print("    required keys (IB_HOST, IB_PORT, IB_CLIENT_ID, IB_PAPER_ACCOUNT_ID).")
        print("  - Or export them as environment variables.")
        return 2
    except ValueError as exc:
        print(f"\nFAILED: invalid credentials value — {exc}")
        return 2

    print(
        f"    host={credentials.host} port={credentials.port} "
        f"client_id={credentials.client_id} "
        f"account_id=[REDACTED]"
    )
    if credentials.account_id == "replace-with-your-ib-paper-account-id":
        print("\nFAILED: IB_PAPER_ACCOUNT_ID is still the template placeholder.")
        print("Edit ~/.blive/secrets/ib.env and replace the placeholder with")
        print("your actual IB paper account id (e.g. DUxxxxxxx).")
        return 2

    # Step 2: build the rate limiter + clock + client.
    _print_step("constructing IBClient with IB_DEFAULT_RATE_LIMITS + WallClock")
    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)

    # Step 3: connect.
    started_at = datetime.now(tz=timezone.utc)
    _print_step("calling IBClient.connect() — TCP handshake to IB Gateway")
    try:
        await client.connect()
    except IBConnectionError as exc:
        elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
        print(f"\nFAILED after {elapsed:.2f}s: {exc}")
        if exc.__cause__ is not None:
            print(f"  underlying: {type(exc.__cause__).__name__}: {exc.__cause__}")
        print("\nFix:")
        print("  - Confirm IB Gateway / TWS is running and logged in to the paper account.")
        print(f"  - Confirm it is listening on TCP {credentials.host}:{credentials.port}.")
        print("  - Confirm 'Enable ActiveX and Socket Clients' is checked under")
        print("    File > Global Configuration > API > Settings.")
        print(f"  - Confirm clientId={credentials.client_id} is not in use by another")
        print("    process (TWS desktop, another blive instance, an old gateway, etc.).")
        return 3
    elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
    print(f"    connected in {elapsed:.2f}s; is_connected={client.is_connected}")

    # Step 4: introspect rate-limiter usage.
    metrics = rate_limiter.metrics()
    global_metrics = metrics["global"]
    available_decimal: Decimal = global_metrics.available
    print(
        f"    rate_limiter.global available={available_decimal:.2f}"
        f"/{global_metrics.capacity} after handshake"
    )

    # Step 5: disconnect.
    _print_step("calling IBClient.disconnect()")
    await client.disconnect()
    print(f"    is_connected={client.is_connected}")

    _print_header("OK — handshake clean")
    print(
        "M2-IB.3 first-handshake prereq satisfied. ADR-032 + DD-7 STABLE flips "
        "remain pending, but the wire is alive."
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
