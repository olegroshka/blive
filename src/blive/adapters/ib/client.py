"""IB driver wrapper — TCP socket + callback model.

Implements the IB-side analogue of [ADR-002](../../../../docs/decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver):
``ib_async.IB`` instantiated only inside this adapter. The wire-level
mechanics differ from M2-IG.3's :class:`blive.adapters.ig.client.IGClient`:
IG is REST request-response over HTTPS, IB is a persistent TCP socket
with event callbacks that ``ib_async`` exposes via ``eventkit``.

What this module owns (M2-IB.2 surface):

- The :class:`ib_async.IB` instance itself (one per :class:`IBClient`).
- Connection lifecycle (:meth:`connect` / :meth:`disconnect` /
  :attr:`is_connected`).
- Rate-limited acquire of the ``global`` bucket on connect (per
  [KB-3 §1](../../../../docs/kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle)
  and [ADR-031](../../../../docs/decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters)).
- Typed exception hierarchy at the connection boundary
  (:class:`IBError` / :class:`IBConnectionError`).

What is **not** here (lands at M2-IB.3 / .4):

- ``IBInstrumentResolver`` — :class:`Instrument` ↔ ``Contract`` /
  ``ConID`` per [DD-7 §4](../../../../docs/dd/instrument_dictionary.md#4-conid-resolution--caching).
- ``IBBroker`` read methods — ``positions`` / ``account_snapshot`` /
  ``open_orders`` / ``events``.
- ``IBBroker`` write methods + FSM event emission via ``orderStatusEvent``
  / ``execDetailsEvent`` / ``commissionReportEvent`` callbacks.
- ``IBMarketData`` — ``subscribe_bars`` via ``ib_async.reqMktData`` /
  ``reqHistoricalData``.
- INV-14 IB-error-code inventory — populated by observed-rejects at
  M2-IB.4.

Higher-level adapters (when they land) construct one of these and access
the underlying ``ib_async.IB`` via :attr:`ib` for method dispatch + event
wiring. Outbound API calls acquire from the appropriate
:class:`TokenBucketRateLimiter` bucket before invoking ``ib_async`` methods
(``global`` for most calls; ``historical`` for ``reqHistoricalData``;
extra tokens for ``BID_ASK`` per [KB-3 §2](../../../../docs/kb/ib_pacing_spec.md#2-historical-data-pacing)).

The :attr:`ib` property is the load-bearing escape hatch — adapters need
to register event handlers on the underlying ``ib_async`` event objects
(``ib.orderStatusEvent += handler`` etc.); a generic dispatch wrapper
would obscure that. The hexagonal-architecture contract holds because
this module lives under ``blive.adapters.ib.*`` and is only imported by
sibling IB modules + :mod:`blive.runtime.broker_registry` per
[ADR-004](../../../../docs/decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) +
[ADR-034](../../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004).
"""

from __future__ import annotations

import asyncio
import logging

import ib_async

from blive.adapters.ib.credentials import IBCredentials
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.ports import ClockPort

log = logging.getLogger(__name__)


# --- Typed exception hierarchy ----------------------------------------------


class IBError(Exception):
    """Base for all IB-specific errors. Subclasses carry the IB error code
    (when present) and the request id (when applicable).

    Mirrors the :class:`blive.adapters.ig.client.IGError` shape so call
    sites can treat broker-specific exceptions uniformly. The full IB
    error-code inventory ([INV-14](../../../../docs/inv/ib_error_codes.md))
    is MISSING; populated as observed-rejects accumulate at M2-IB.4.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: int | None = None,
        request_id: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.request_id = request_id


class IBConnectionError(IBError):
    """TCP-level / Gateway-not-running. Caller may retry with backoff.

    Maps from raw socket errors at :meth:`IBClient.connect` time:
    ``ConnectionRefusedError`` (Gateway not listening on the configured
    port), ``asyncio.TimeoutError`` (port reachable but Gateway slow to
    respond), generic ``OSError`` (other socket failures). Once connected,
    transient mid-session disconnects surface via ``ib_async``'s
    ``disconnectedEvent`` rather than this exception.
    """


# --- The client --------------------------------------------------------------


# Default connect timeout — IB Gateway typically responds within ~1-2s on a
# healthy local connection; 10s gives generous headroom for cold-start
# scenarios (Gateway recently launched, DNS lookup, etc.) without leaving
# blive hung indefinitely on a misconfigured port.
_DEFAULT_CONNECT_TIMEOUT_SECONDS: float = 10.0


class IBClient:
    """Low-level IB driver wrapper per ADR-002 (TCP socket + callback model).

    Owns connection lifecycle and the underlying ``ib_async.IB`` instance.
    Higher-level adapters (``IBBroker``, ``IBMarketData``,
    ``IBInstrumentResolver`` — all M2-IB.3+) construct one of these and
    access ``ib_async`` via :attr:`ib` for method dispatch and event-handler
    wiring.

    Construct from :class:`IBCredentials` + a :class:`TokenBucketRateLimiter`
    configured per :data:`blive.adapters.ib.rate_limiter.IB_DEFAULT_RATE_LIMITS`.
    Tests inject a mock ``ib_async.IB`` via the ``ib=`` kwarg; production
    callers omit it and let the constructor allocate a fresh instance.
    """

    def __init__(
        self,
        *,
        credentials: IBCredentials,
        rate_limiter: TokenBucketRateLimiter,
        clock: ClockPort,
        ib: ib_async.IB | None = None,
        connect_timeout_seconds: float = _DEFAULT_CONNECT_TIMEOUT_SECONDS,
    ) -> None:
        self._credentials = credentials
        self._rate_limiter = rate_limiter
        self._clock = clock
        # Tests inject a mock; production allocates a fresh IB.
        self._ib = ib if ib is not None else ib_async.IB()
        self._connect_timeout_seconds = connect_timeout_seconds

    # --- Public surface -----------------------------------------------------

    @property
    def ib(self) -> ib_async.IB:
        """The underlying ``ib_async.IB`` instance.

        Adapter modules use this for method dispatch (``client.ib.reqPositions()``
        etc.) and event-handler wiring (``client.ib.orderStatusEvent += handler``).
        Outside the ``blive.adapters.ib.*`` package this attribute is not
        accessed — the import-linter contract forbids it.
        """
        return self._ib

    @property
    def credentials(self) -> IBCredentials:
        return self._credentials

    @property
    def rate_limiter(self) -> TokenBucketRateLimiter:
        return self._rate_limiter

    @property
    def is_connected(self) -> bool:
        """Whether the underlying ``ib_async.IB`` reports an active socket."""
        return bool(self._ib.isConnected())

    # --- Connection lifecycle ------------------------------------------------

    async def connect(self) -> None:
        """Open the TCP socket to IB Gateway / TWS.

        Idempotent: re-calling on a connected client is a no-op (no second
        ``acquire`` from the rate limiter). Acquires one token from the
        ``global`` bucket per [KB-3 §1](../../../../docs/kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle).

        Raises :class:`IBConnectionError` if the socket cannot be
        established (Gateway not running, wrong port, ``clientId`` already
        in use, network partition). The exception preserves the
        underlying error as ``__cause__`` for diagnostics.
        """
        if self.is_connected:
            return

        await self._rate_limiter.acquire("global")
        try:
            await asyncio.wait_for(
                self._ib.connectAsync(
                    host=self._credentials.host,
                    port=self._credentials.port,
                    clientId=self._credentials.client_id,
                ),
                timeout=self._connect_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise IBConnectionError(
                f"IB connect timed out after {self._connect_timeout_seconds}s "
                f"(host={self._credentials.host}, port={self._credentials.port}); "
                f"is the IB Gateway / TWS running?"
            ) from exc
        except ConnectionRefusedError as exc:
            raise IBConnectionError(
                f"IB connect refused at "
                f"{self._credentials.host}:{self._credentials.port}; "
                f"is the IB Gateway / TWS listening on that port?"
            ) from exc
        except OSError as exc:
            raise IBConnectionError(
                f"IB connect failed at " f"{self._credentials.host}:{self._credentials.port}: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Close the TCP socket (best-effort).

        Idempotent: calling on a disconnected client is a no-op.
        ``ib_async.IB.disconnect()`` is synchronous; the ``async`` shape
        here mirrors :meth:`IGClient.disconnect` for symmetry across
        broker adapters and lets future buffered-flush logic land without
        a signature change.
        """
        if not self.is_connected:
            return
        try:
            self._ib.disconnect()
        except Exception as exc:  # noqa: BLE001 — best-effort logout
            log.warning("IB disconnect raised; suppressing: %s", exc)


__all__ = [
    "IBClient",
    "IBError",
    "IBConnectionError",
]
