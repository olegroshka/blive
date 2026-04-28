"""IG REST client core.

Implements the REST half of [ADR-036](../../../../docs/decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer):
HTTPS via :class:`httpx.AsyncClient`, 3-step session auth + token refresh,
typed exception hierarchy, rate-limited via :mod:`blive.adapters.shared.rate_limiter`.

Lightstreamer (the streaming half of ADR-036) lives in
:mod:`blive.adapters.ig.market_data` — the IGClient holds the auth state
both halves share. Endpoint-specific helpers (``positions()``,
``account_snapshot()``, etc.) live in :class:`blive.adapters.ig.broker.IGBroker`
and :class:`blive.adapters.ig.instrument_resolver.IGInstrumentResolver`;
this module is the pure transport.

The class is constructed from :class:`IGCredentials` + a
:class:`TokenBucketRateLimiter` (typically configured with the
``IG_DEFAULT_RATE_LIMITS`` from M2-IG.3 follow-up; for now callers
compose their own). Responses are parsed as JSON and returned as plain
``dict`` — caller code does the typed-dataclass marshalling. The error
mapping ([KB-17 §6](../../../../docs/kb/ig_pacing_spec.md#6-error-codes-at-the-pacing-boundary))
turns IG ``errorCode`` strings into the typed-exception hierarchy below.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

import httpx

from blive.adapters.ig.credentials import IGCredentials
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.ports import ClockPort

log = logging.getLogger(__name__)


# --- URL routing per environment (KB-16 §1) ----------------------------------

_DEMO_BASE_URL = "https://demo-api.ig.com/gateway/deal"
_LIVE_BASE_URL = "https://api.ig.com/gateway/deal"


def _base_url_for(environment: str) -> str:
    if environment == "demo":
        return _DEMO_BASE_URL
    if environment == "live":
        return _LIVE_BASE_URL
    raise ValueError(f"unknown IG environment: {environment!r}")


# --- Typed exception hierarchy (ADR-036 §"Decision") ------------------------


class IGError(Exception):
    """Base for all IG-specific errors. Every subclass carries the IG
    ``errorCode`` (when present) and the HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.http_status = http_status


class IGAuthError(IGError):
    """Bad credentials or revoked API key. Do **not** retry; surface to operator."""


class IGSessionExpired(IGError):
    """Session token expired or invalidated. Internal-only — `IGClient` catches
    this in its request loop and triggers a refresh-then-retry."""


class IGRateLimited(IGError):
    """API rate-limit exceeded. Caller should back off."""


class IGOrderRejected(IGError):
    """Order rejected with a venue reason. Caller maps to an FSM transition."""


class IGRequestInvalid(IGError):
    """Programming error: bad request shape, unknown instrument, bad version, etc."""


class IGConnectionError(IGError):
    """Transient network / 5xx error. Caller may retry with backoff."""


# IG ``errorCode`` → exception type mapping (KB-17 §6).
_AUTH_ERROR_CODES = frozenset(
    {
        "error.security.invalid-details",
        "error.security.api-key-revoked",
        "error.public-api.failure.kyc.required",
    }
)
_SESSION_EXPIRED_CODES = frozenset(
    {
        "error.security.client-token-invalid",
        "error.public-api.client-token-invalid",
    }
)
_RATE_LIMIT_CODES = frozenset(
    {
        "error.public-api.exceeded-api-key-allowance",
        "error.public-api.exceeded-account-allowance",
        "error.public-api.exceeded-trading-allowance",
        "error.public-api.exceeded-historical-data-allowance",
    }
)
_REJECTED_CODES = frozenset({"error.confirms.deal-rejected"})


def _classify_error(error_code: str | None, http_status: int) -> type[IGError]:
    if error_code in _AUTH_ERROR_CODES:
        return IGAuthError
    if error_code in _SESSION_EXPIRED_CODES:
        return IGSessionExpired
    if error_code in _RATE_LIMIT_CODES:
        return IGRateLimited
    if error_code in _REJECTED_CODES:
        return IGOrderRejected
    if http_status >= 500:
        return IGConnectionError
    return IGRequestInvalid


# --- The client --------------------------------------------------------------


class IGClient:
    """Low-level IG REST client per ADR-036.

    Owns auth state (CST + X-SECURITY-TOKEN headers) and dispatches
    rate-limited HTTP requests. Higher-level adapters (`IGBroker`,
    `IGMarketData`, `IGInstrumentResolver`) construct one of these and
    call its :meth:`get` / :meth:`post` / :meth:`put` / :meth:`delete`
    methods.
    """

    def __init__(
        self,
        *,
        credentials: IGCredentials,
        rate_limiter: TokenBucketRateLimiter,
        clock: ClockPort,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._credentials = credentials
        self._rate_limiter = rate_limiter
        self._clock = clock
        self._base_url = _base_url_for(credentials.environment)
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "X-IG-API-KEY": credentials.api_key,
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json; charset=UTF-8",
            },
        )
        self._cst: str | None = None
        self._security_token: str | None = None

    # --- Connection lifecycle ------------------------------------------------

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def is_connected(self) -> bool:
        return self._cst is not None and self._security_token is not None

    async def connect(self) -> None:
        """Authenticate via 3-step ``POST /session``; cache CST + X-SECURITY-TOKEN.

        Raises :class:`IGAuthError` on bad credentials. The 3-step refers to
        IG's auth flow: client sends API key + identifier + password →
        server returns CST and X-SECURITY-TOKEN headers + an account list
        in the body. Subsequent calls must include all three headers.
        """
        if self.is_connected:
            return  # idempotent

        await self._rate_limiter.acquire("general")
        response = await self._http.post(
            "/session",
            headers={"Version": "2"},
            json={
                "identifier": self._credentials.username,
                "password": self._credentials.password,
            },
        )
        self._handle_response(response, raise_on_session_expired=False)
        self._cst = response.headers.get("CST")
        self._security_token = response.headers.get("X-SECURITY-TOKEN")
        if not self._cst or not self._security_token:
            raise IGAuthError(
                "IG /session returned 200 but missing CST / X-SECURITY-TOKEN headers",
                http_status=response.status_code,
            )

    async def disconnect(self) -> None:
        """``DELETE /session`` (best-effort) and close the underlying httpx client."""
        if self.is_connected:
            try:
                await self._rate_limiter.acquire("general")
                await self._http.delete("/session", headers=self._auth_headers())
            except Exception as exc:  # noqa: BLE001 — best-effort logout
                log.warning("IG /session DELETE failed during disconnect: %s", exc)
            finally:
                self._cst = None
                self._security_token = None
        await self._http.aclose()

    # --- Public request surface ---------------------------------------------

    async def get(
        self,
        path: str,
        *,
        version: int = 1,
        params: Mapping[str, Any] | None = None,
        bucket: str = "general",
    ) -> Any:
        return await self._request("GET", path, version=version, params=params, bucket=bucket)

    async def post(
        self,
        path: str,
        *,
        version: int = 1,
        json: Mapping[str, Any] | None = None,
        bucket: str = "trading",
    ) -> Any:
        return await self._request("POST", path, version=version, json=json, bucket=bucket)

    async def put(
        self,
        path: str,
        *,
        version: int = 1,
        json: Mapping[str, Any] | None = None,
        bucket: str = "trading",
    ) -> Any:
        return await self._request("PUT", path, version=version, json=json, bucket=bucket)

    async def delete(
        self,
        path: str,
        *,
        version: int = 1,
        bucket: str = "trading",
    ) -> Any:
        return await self._request("DELETE", path, version=version, bucket=bucket)

    # --- Internals ----------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        if not self.is_connected:
            raise IGAuthError("IGClient is not connected; call connect() first")
        # Type-narrowing: the is_connected check ensures these are non-None.
        assert self._cst is not None
        assert self._security_token is not None
        return {
            "CST": self._cst,
            "X-SECURITY-TOKEN": self._security_token,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        version: int,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        bucket: str,
    ) -> Any:
        """Single dispatch entry point for GET / POST / PUT / DELETE.

        Honours the rate limiter; sends auth + version headers; on 401 with
        a session-expired error code, attempts ``POST /session/refresh-token``
        and retries once. If the refresh itself fails, falls back to a full
        ``POST /session`` re-auth and retries once. Persistent auth failure
        bubbles as :class:`IGAuthError`.
        """
        if not self.is_connected:
            raise IGAuthError(f"IGClient.{method.lower()}({path!r}) called before connect()")

        return await self._dispatch_with_refresh(
            method, path, version=version, params=params, json=json, bucket=bucket
        )

    async def _dispatch_with_refresh(
        self,
        method: str,
        path: str,
        *,
        version: int,
        params: Mapping[str, Any] | None,
        json: Mapping[str, Any] | None,
        bucket: str,
    ) -> Any:
        """Send the request; on session-expired, try refresh-then-retry; if
        that also fails with session-expired, fall back to full re-auth and
        retry once more. Persistent failure raises :class:`IGAuthError`.

        Bad-credential / API-key-revoked / KYC errors at any point raise
        :class:`IGAuthError` immediately (no retry — operator action required).
        """
        refresh_attempted = False
        reauth_attempted = False
        while True:
            try:
                return await self._send_once(
                    method, path, version=version, params=params, json=json, bucket=bucket
                )
            except IGSessionExpired:
                pass  # fall through to recovery

            if not refresh_attempted:
                refresh_attempted = True  # mark before attempting; loop on failure
                try:
                    await self._refresh_session_or_reauth()
                    continue  # retry the original request with the new token
                except IGSessionExpired:
                    pass  # refresh endpoint itself returned session-expired; try full re-auth
                # Note: IGAuthError from refresh (bad-creds / api-key-revoked) propagates
                # out unchanged — that's a hard error, not a recoverable one.

            if not reauth_attempted:
                reauth_attempted = True
                self._cst = None
                self._security_token = None
                await self.connect()  # raises IGAuthError on bad creds (no retry)
                continue  # retry with fresh session

            # Both refresh and full re-auth tried; still session-expired.
            raise IGAuthError(
                f"IG session could not be re-established after refresh + full re-auth; "
                f"last call: {method} {path}"
            )

    async def _send_once(
        self,
        method: str,
        path: str,
        *,
        version: int,
        params: Mapping[str, Any] | None,
        json: Mapping[str, Any] | None,
        bucket: str,
    ) -> Any:
        await self._rate_limiter.acquire(bucket)
        headers: dict[str, str] = {
            "Version": str(version),
            **self._auth_headers(),
        }
        response = await self._http.request(
            method,
            path,
            params=params,
            json=json,
            headers=headers,
        )
        return self._handle_response(response)

    async def _refresh_session_or_reauth(self) -> None:
        """Attempt ``POST /session/refresh-token``.

        Raises :class:`IGSessionExpired` if the refresh endpoint itself
        returns session-expired (so the caller can fall through to full
        re-auth). Raises :class:`IGAuthError` on hard auth failures
        (bad credentials, revoked API key) — those don't recover from
        a re-auth either.
        """
        await self._rate_limiter.acquire("general")
        response = await self._http.post(
            "/session/refresh-token",
            headers={
                "Version": "1",
                **self._auth_headers(),
            },
            json={"refreshToken": ""},  # IG refresh-token is header-driven; payload empty
        )
        # Default ``raise_on_session_expired=True`` so a 401 with
        # ``error.security.client-token-invalid`` raises IGSessionExpired
        # — the caller's loop catches that and falls through to full
        # re-auth. Bad-creds / KYC errors map to IGAuthError directly.
        self._handle_response(response)
        # Refresh returns new CST + X-SECURITY-TOKEN as headers.
        new_cst = response.headers.get("CST")
        new_token = response.headers.get("X-SECURITY-TOKEN")
        if not new_cst or not new_token:
            # 200 OK but headers missing — refresh effectively failed;
            # raise IGSessionExpired so the caller falls through to full re-auth.
            raise IGSessionExpired(
                "IG /session/refresh-token returned 200 but missing CST / X-SECURITY-TOKEN",
                http_status=response.status_code,
            )
        self._cst = new_cst
        self._security_token = new_token

    def _handle_response(
        self,
        response: httpx.Response,
        *,
        raise_on_session_expired: bool = True,
    ) -> Any:
        """Parse a response. Returns the JSON body for 2xx; raises typed
        exceptions for 4xx / 5xx.

        ``raise_on_session_expired=False`` is used during ``connect()`` and
        ``_refresh_session_or_reauth`` so the caller controls whether to
        treat session-expired as a recoverable signal vs a hard error.
        """
        if 200 <= response.status_code < 300:
            if response.content:
                try:
                    return response.json()
                except ValueError as exc:
                    raise IGRequestInvalid(
                        f"IG response was not JSON: {response.text[:200]!r}",
                        http_status=response.status_code,
                    ) from exc
            return {}

        # Error path — try to extract IG's structured error.
        error_code: str | None = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                code = payload.get("errorCode")
                if isinstance(code, str):
                    error_code = code
        except ValueError:
            pass  # non-JSON error body; leave error_code None

        exc_type = _classify_error(error_code, response.status_code)
        if exc_type is IGSessionExpired and not raise_on_session_expired:
            # During connect/refresh: a 401 means the credentials path
            # itself failed. Surface as IGAuthError so the operator sees
            # a clear message.
            raise IGAuthError(
                f"IG auth failed during connection step: HTTP {response.status_code} "
                f"{error_code!r}",
                error_code=error_code,
                http_status=response.status_code,
            )
        raise exc_type(
            f"IG request returned HTTP {response.status_code} (errorCode={error_code!r})",
            error_code=error_code,
            http_status=response.status_code,
        )


__all__ = [
    "IGClient",
    "IGError",
    "IGAuthError",
    "IGSessionExpired",
    "IGRateLimited",
    "IGOrderRejected",
    "IGRequestInvalid",
    "IGConnectionError",
]
