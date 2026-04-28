"""IB credential schema + typed loader.

Declares :data:`IB_SCHEMA`, the per-broker
:class:`blive.adapters.shared.credentials.CredentialSchema` for IB. Field
set lifted from [ADR-035 §3](../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets):
``IB_HOST``, ``IB_PORT``, ``IB_CLIENT_ID``, ``IB_PAPER_ACCOUNT_ID``. **No
password** — IB Gateway handles authentication via IBC per [KB-3 §5](../../../../docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events);
blive only needs the connection coordinates plus the account id for
account-scoped queries.

The :class:`IBCredentials` dataclass wraps :func:`load_credentials` with a
typed result. Construction validates that ``IB_PORT`` is parseable as an
integer in the valid TCP-port range and that ``IB_CLIENT_ID`` is a
non-negative integer (semantic validation that the generic loader does not
perform — the loader returns string values).

Per [ADR-035](../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets):
``IB_PAPER_ACCOUNT_ID`` is marked ``secret=True`` so it enters the
log-redaction list (the account id identifies the account, even though it's
visible in TWS to the operator). ``IB_HOST`` / ``IB_PORT`` / ``IB_CLIENT_ID``
are marked ``secret=False`` — they're connection coordinates (typically
``127.0.0.1`` / ``4002`` / ``1``), not sensitive data. The example template
at ``secrets/ib.env.example`` carries the same convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from blive.adapters.shared.credentials import (
    CredentialField,
    CredentialSchema,
    load_credentials,
)

# --- Schema (consumed by load_credentials) ----------------------------------

IB_SCHEMA: CredentialSchema = CredentialSchema(
    broker_name="ib",
    fields=(
        CredentialField(name="IB_HOST", required=True, secret=False),
        CredentialField(name="IB_PORT", required=True, secret=False),
        CredentialField(name="IB_CLIENT_ID", required=True, secret=False),
        CredentialField(name="IB_PAPER_ACCOUNT_ID", required=True, secret=True),
    ),
)


# --- Typed wrapper -----------------------------------------------------------


# TCP port range: 1..65535. IB defaults: 4001 (live gw) / 4002 (paper gw) /
# 7496 (live tws) / 7497 (paper tws). We validate generic port range only;
# paper-vs-live is determined by the operator wiring the right port.
_MIN_TCP_PORT = 1
_MAX_TCP_PORT = 65535


@dataclass(frozen=True, slots=True)
class IBCredentials:
    """Typed credentials bundle for the IB adapter.

    Construct via :meth:`load` to read from env / dotenv. The dataclass
    itself is dumb data — validation happens once at :meth:`load` time so
    the rest of the adapter can trust the values.
    """

    host: str
    port: int
    client_id: int
    account_id: str

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("IBCredentials.host must be non-empty")
        if not (_MIN_TCP_PORT <= self.port <= _MAX_TCP_PORT):
            raise ValueError(
                f"IBCredentials.port must be in [{_MIN_TCP_PORT}, {_MAX_TCP_PORT}], "
                f"got {self.port}"
            )
        if self.client_id < 0:
            raise ValueError(f"IBCredentials.client_id must be >= 0, got {self.client_id}")
        if not self.account_id:
            raise ValueError("IBCredentials.account_id must be non-empty")

    @classmethod
    def load(
        cls,
        *,
        secrets_dir: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> "IBCredentials":
        """Load from ``~/.blive/secrets/ib.env`` (or env vars) per ADR-035.

        Raises :class:`blive.adapters.shared.credentials.CredentialsMissing`
        if any required field is unavailable; raises :class:`ValueError`
        if ``IB_PORT`` / ``IB_CLIENT_ID`` are not parseable as integers
        or fall outside their valid ranges.
        """
        raw = load_credentials(IB_SCHEMA, secrets_dir=secrets_dir, env=env)
        return cls(
            host=raw["IB_HOST"],
            port=_parse_int(raw["IB_PORT"], field_name="IB_PORT"),
            client_id=_parse_int(raw["IB_CLIENT_ID"], field_name="IB_CLIENT_ID"),
            account_id=raw["IB_PAPER_ACCOUNT_ID"],
        )


def _parse_int(value: str, *, field_name: str) -> int:
    """Parse a numeric env-var value to int with a clear error.

    The shared loader returns string values; we coerce here so
    ``IBCredentials`` can carry strongly-typed fields.
    """
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer, got {value!r}") from exc


__all__ = [
    "IB_SCHEMA",
    "IBCredentials",
]
