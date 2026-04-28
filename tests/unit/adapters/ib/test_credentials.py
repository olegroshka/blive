"""Tests for :mod:`blive.adapters.ib.credentials`.

Covers the IB :class:`CredentialSchema` shape per [ADR-035 §3](../../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets)
and the typed :class:`IBCredentials` wrapper. Mirrors the
``test_credentials.py`` layout used for the IG adapter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from blive.adapters.ib.credentials import IB_SCHEMA, IBCredentials
from blive.adapters.shared.credentials import CredentialsMissing

# --- IB_SCHEMA contract ------------------------------------------------------


def test_ib_schema_broker_name_is_ib() -> None:
    """The broker_name drives the ~/.blive/secrets/{broker}.env filename."""
    assert IB_SCHEMA.broker_name == "ib"


def test_ib_schema_required_fields_match_adr035() -> None:
    """Per ADR-035 §3: IB schema is host / port / clientId / paper account
    id; no password (IB Gateway handles auth via IBC per KB-3 §5)."""
    assert set(IB_SCHEMA.required_field_names()) == {
        "IB_HOST",
        "IB_PORT",
        "IB_CLIENT_ID",
        "IB_PAPER_ACCOUNT_ID",
    }


def test_ib_schema_only_account_id_is_secret() -> None:
    """ADR-035: account id identifies the account; host/port/clientId are
    connection coordinates, not sensitive."""
    assert set(IB_SCHEMA.secret_field_names()) == {"IB_PAPER_ACCOUNT_ID"}


# --- IBCredentials.load happy path ------------------------------------------


def test_load_from_env_returns_typed_credentials(tmp_path: Path) -> None:
    env = {
        "IB_HOST": "127.0.0.1",
        "IB_PORT": "4002",
        "IB_CLIENT_ID": "1",
        "IB_PAPER_ACCOUNT_ID": "DU1234567",
    }
    creds = IBCredentials.load(secrets_dir=tmp_path, env=env)
    assert creds.host == "127.0.0.1"
    assert creds.port == 4002
    assert creds.client_id == 1
    assert creds.account_id == "DU1234567"


def test_load_from_dotenv_file(tmp_path: Path) -> None:
    env_path = tmp_path / "ib.env"
    env_path.write_text(
        "\n".join(
            [
                "IB_HOST=10.0.0.5",
                "IB_PORT=4001",  # live gateway port
                "IB_CLIENT_ID=2",
                "IB_PAPER_ACCOUNT_ID=DU9999999",
            ]
        ),
        encoding="utf-8",
    )
    creds = IBCredentials.load(secrets_dir=tmp_path, env={})
    assert creds.host == "10.0.0.5"
    assert creds.port == 4001
    assert creds.client_id == 2
    assert creds.account_id == "DU9999999"


def test_env_overrides_dotenv_file(tmp_path: Path) -> None:
    """ADR-035: env vars take priority over file values (Docker / CI injection)."""
    env_path = tmp_path / "ib.env"
    env_path.write_text(
        "IB_HOST=file-host\nIB_PORT=4002\nIB_CLIENT_ID=1\nIB_PAPER_ACCOUNT_ID=DU111\n",
        encoding="utf-8",
    )
    env = {"IB_HOST": "env-host"}  # only override host
    creds = IBCredentials.load(secrets_dir=tmp_path, env=env)
    assert creds.host == "env-host"  # env wins
    assert creds.port == 4002  # file value used (not in env)
    assert creds.account_id == "DU111"


# --- IBCredentials.load missing / invalid -----------------------------------


def test_load_missing_required_raises_credentials_missing(tmp_path: Path) -> None:
    """Generic loader raises CredentialsMissing — the typed wrapper bubbles."""
    with pytest.raises(CredentialsMissing) as excinfo:
        IBCredentials.load(secrets_dir=tmp_path, env={})
    assert excinfo.value.broker_name == "ib"
    assert set(excinfo.value.missing) == {
        "IB_HOST",
        "IB_PORT",
        "IB_CLIENT_ID",
        "IB_PAPER_ACCOUNT_ID",
    }


def test_load_non_integer_port_raises_value_error(tmp_path: Path) -> None:
    env = {
        "IB_HOST": "127.0.0.1",
        "IB_PORT": "not-a-number",
        "IB_CLIENT_ID": "1",
        "IB_PAPER_ACCOUNT_ID": "DU1234567",
    }
    with pytest.raises(ValueError, match="IB_PORT"):
        IBCredentials.load(secrets_dir=tmp_path, env=env)


def test_load_non_integer_client_id_raises_value_error(tmp_path: Path) -> None:
    env = {
        "IB_HOST": "127.0.0.1",
        "IB_PORT": "4002",
        "IB_CLIENT_ID": "abc",
        "IB_PAPER_ACCOUNT_ID": "DU1234567",
    }
    with pytest.raises(ValueError, match="IB_CLIENT_ID"):
        IBCredentials.load(secrets_dir=tmp_path, env=env)


# --- IBCredentials direct construction validation ---------------------------


def test_direct_construction_validates_host() -> None:
    with pytest.raises(ValueError, match="host"):
        IBCredentials(host="", port=4002, client_id=1, account_id="DU1")


def test_direct_construction_validates_port_low() -> None:
    with pytest.raises(ValueError, match="port"):
        IBCredentials(host="127.0.0.1", port=0, client_id=1, account_id="DU1")


def test_direct_construction_validates_port_high() -> None:
    with pytest.raises(ValueError, match="port"):
        IBCredentials(host="127.0.0.1", port=65536, client_id=1, account_id="DU1")


def test_direct_construction_validates_client_id() -> None:
    with pytest.raises(ValueError, match="client_id"):
        IBCredentials(host="127.0.0.1", port=4002, client_id=-1, account_id="DU1")


def test_direct_construction_validates_account_id() -> None:
    with pytest.raises(ValueError, match="account_id"):
        IBCredentials(host="127.0.0.1", port=4002, client_id=1, account_id="")


def test_credentials_dataclass_is_frozen() -> None:
    creds = IBCredentials(host="127.0.0.1", port=4002, client_id=1, account_id="DU1")
    with pytest.raises(AttributeError):
        creds.host = "x"  # type: ignore[misc]


def test_client_id_zero_is_allowed() -> None:
    """clientId=0 is valid in TWS API (master client default in some setups)."""
    creds = IBCredentials(host="127.0.0.1", port=4002, client_id=0, account_id="DU1")
    assert creds.client_id == 0


def test_port_boundaries_are_inclusive() -> None:
    """TCP ports 1 and 65535 are both valid."""
    low = IBCredentials(host="127.0.0.1", port=1, client_id=1, account_id="DU1")
    high = IBCredentials(host="127.0.0.1", port=65535, client_id=1, account_id="DU1")
    assert low.port == 1
    assert high.port == 65535
