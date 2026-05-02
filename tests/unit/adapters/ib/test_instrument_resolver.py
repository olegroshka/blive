"""Tests for :mod:`blive.adapters.ib.instrument_resolver`.

Covers the IB instrument resolver per [ADR-032](../../../../../docs/decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract)
+ [DD-7](../../../../../docs/dd/instrument_dictionary.md):

- ``to_contract`` field mapping (DD-7 §1, §2, §3) + tradability /
  asset_class / venue rejection paths.
- ``resolve`` lazy + cached + rate-limit-acquire happy path.
- Zero / multiple / zero-conId candidate paths → typed exceptions.
- ``clear_cache`` per-instrument and full-flush.

Mocks ``ib_async.IB`` via :class:`unittest.mock.MagicMock` injected
through :class:`IBClient`'s ``ib=`` constructor kwarg — same pattern as
``test_client.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import ib_async
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ib.client import IBClient
from blive.adapters.ib.credentials import IBCredentials
from blive.adapters.ib.instrument_resolver import (
    IBInstrumentResolver,
    InstrumentAmbiguous,
    InstrumentNotResolvable,
)
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)
from blive.domain.types import AssetClass, Instrument

# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def clock() -> SimClock:
    return SimClock(start=datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def rate_limiter(clock: SimClock) -> TokenBucketRateLimiter:
    return TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "global": RateLimitBucket(capacity=100, refill_per_second=Decimal("20")),
                "historical": RateLimitBucket(capacity=50, refill_per_second=Decimal("1")),
            }
        ),
    )


@pytest.fixture
def credentials() -> IBCredentials:
    return IBCredentials(
        host="127.0.0.1",
        port=4002,
        client_id=1,
        account_id="DUTEST",
    )


def _make_mock_ib(*, qualify_returns: list[ib_async.Contract] | None = None) -> MagicMock:
    """Build a connected mock with ``qualifyContractsAsync`` pre-wired."""
    m = MagicMock(spec=ib_async.IB)
    m.isConnected.return_value = True  # resolver assumes a live connection.
    m.qualifyContractsAsync = AsyncMock(return_value=qualify_returns or [])
    return m


def _make_resolver(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    mock_ib: MagicMock,
) -> IBInstrumentResolver:
    client = IBClient(
        credentials=credentials,
        rate_limiter=rate_limiter,
        clock=clock,
        ib=mock_ib,
    )
    return IBInstrumentResolver(client)


@pytest.fixture
def cac_pa() -> Instrument:
    """Phase 1 ETF on Euronext Paris per ADR-021."""
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )


# --- to_contract: happy paths -----------------------------------------------


def test_to_contract_etf_spot_maps_to_stk_sbf(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """ETF tradability=spot on XPAR → STK on SBF (DD-7 §2 + §3, Phase 1).

    The Yahoo-style ``.PA`` suffix is stripped per ADR-041 + DD-7 §3.1
    — IB uses bare exchange tickers (``CAC`` not ``CAC.PA``).
    """
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    contract = resolver.to_contract(cac_pa)
    assert contract.symbol == "CAC"  # ".PA" stripped (Yahoo→IB)
    assert contract.secType == "STK"
    assert contract.exchange == "SBF"
    assert contract.currency == "EUR"
    assert contract.multiplier == ""  # multiplier=1 → empty string


def test_to_contract_equity_maps_to_stk(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """EQUITY → STK (same as ETF, IB doesn't distinguish at secType).

    AAPL on XNAS routes via SMART per ADR-046 (US-equity venues + spot +
    EQUITY/ETF asset class → SMART with primaryExchange hint). The
    Contract.exchange is "SMART"; the IB-named exchange "NASDAQ" carries
    on the primaryExchange field.
    """
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="AAPL",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.EQUITY,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.secType == "STK"
    assert contract.exchange == "SMART"
    assert contract.primaryExchange == "NASDAQ"


def test_to_contract_us_etf_xnas_routes_via_smart_nasdaq(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """ETF on XNAS routes via SMART/NASDAQ per ADR-046. Phase 1 path:
    TQQQ (3× QQQ) on NASDAQ via SMART avoids IB Paper's direct-routing
    precaution at error 10311 without operator-side bypass."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="TQQQ",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.secType == "STK"
    assert contract.exchange == "SMART"
    assert contract.primaryExchange == "NASDAQ"


def test_to_contract_us_etf_xnys_routes_via_smart_nyse(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """ETF on XNYS routes via SMART/NYSE per ADR-046."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="TMF",
        venue="XNYS",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.exchange == "SMART"
    assert contract.primaryExchange == "NYSE"


def test_to_contract_us_etf_arcx_routes_via_smart_arca(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """ETF on ARCX routes via SMART/ARCA per ADR-046."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="SPY",
        venue="ARCX",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.exchange == "SMART"
    assert contract.primaryExchange == "ARCA"


def test_to_contract_us_etf_bats_routes_via_smart_bats(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """ETF on BATS routes via SMART/BATS per ADR-046."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="VOO",
        venue="BATS",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.exchange == "SMART"
    assert contract.primaryExchange == "BATS"


def test_to_contract_non_us_venue_retains_direct_routing(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """Non-US venues (XPAR / XLON / XETR) retain direct routing per ADR-046:
    SMART support varies by venue and is revisited per venue when those
    return to scope. CAC.PA on XPAR stays direct-routed to SBF;
    primaryExchange is empty (IB convention for non-SMART contracts)."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    contract = resolver.to_contract(cac_pa)
    assert contract.exchange == "SBF"
    assert contract.primaryExchange == ""


def test_to_contract_us_index_does_not_use_smart(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """INDEX on a US venue is *not* routed via SMART — the SMART convention
    per ADR-046 applies only to spot EQUITY / ETF asset classes. INDEX is
    used for parity-residual decomposition reads, not orders."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="SPX",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.INDEX,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.secType == "IND"
    assert contract.exchange == "NASDAQ"
    assert contract.primaryExchange == ""


def test_to_contract_index_maps_to_ind(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """INDEX → IND (used for parity-residual decomposition reads, not orders)."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="CAC40",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.INDEX,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.secType == "IND"


def test_to_contract_multiplier_other_than_one_serialises_to_string(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """OPT / FUT instruments carry an actual multiplier (100 for US options,
    50 for ES futures). The resolver casts to a string for ib_async."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="ES",
        venue="XNAS",  # placeholder; CME mapping not in DD-7 §3 yet
        currency="USD",
        asset_class=AssetClass.FUTURE,
        multiplier=Decimal("50"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.multiplier == "50"


# --- to_contract: Yahoo-suffix translation (ADR-041 / DD-7 §3.1) -----------


def test_to_contract_strips_dot_l_suffix_on_xlon(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """``BARC.L`` on XLON → IB symbol ``BARC`` on LSE."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="BARC.L",
        venue="XLON",
        currency="GBP",
        asset_class=AssetClass.EQUITY,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.symbol == "BARC"
    assert contract.exchange == "LSE"


def test_to_contract_strips_dot_de_suffix_on_xetr(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """``SAP.DE`` on XETR → IB symbol ``SAP`` on IBIS."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="SAP.DE",
        venue="XETR",
        currency="EUR",
        asset_class=AssetClass.EQUITY,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.symbol == "SAP"
    assert contract.exchange == "IBIS"


def test_to_contract_passes_through_unsuffixed_symbol_unchanged(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """``AAPL`` on XNAS has no Yahoo suffix → unchanged."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="AAPL",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.EQUITY,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.symbol == "AAPL"


def test_to_contract_does_not_strip_mismatched_suffix(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """A symbol ending in ``.PA`` on a non-XPAR venue is NOT stripped — the
    Yahoo convention couples suffix to listing exchange. ``ABC.PA`` on
    XNAS isn't a Yahoo-style ticker for that venue; pass through."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="ABC.PA",
        venue="XNAS",  # mismatched: .PA suffix is XPAR-only convention
        currency="USD",
        asset_class=AssetClass.EQUITY,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.symbol == "ABC.PA"  # not stripped


def test_to_contract_passes_through_when_venue_has_no_yahoo_suffix(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """XNAS / XNYS have no Yahoo-suffix entry → no stripping attempted."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="QQQ",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )
    contract = resolver.to_contract(instrument)
    assert contract.symbol == "QQQ"


# --- to_contract: rejection paths -------------------------------------------


def test_to_contract_cfd_tradability_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """ADR-037 CFD tradability is the IG path; IB retail is spot-only."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="CAC40",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.INDEX,
        multiplier=Decimal("1"),
        tradability="cfd",
    )
    with pytest.raises(InstrumentNotResolvable, match="tradability"):
        resolver.to_contract(instrument)


def test_to_contract_spread_bet_tradability_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="UK100",
        venue="XLON",
        currency="GBP",
        asset_class=AssetClass.INDEX,
        multiplier=Decimal("1"),
        tradability="spread_bet",
    )
    with pytest.raises(InstrumentNotResolvable, match="tradability"):
        resolver.to_contract(instrument)


def test_to_contract_unknown_venue_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """An unknown MIC has no entry in DD-7 §3; resolver refuses."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    instrument = Instrument(
        symbol="X",
        venue="XXXX",  # not in _MIC_TO_IB_EXCHANGE
        currency="USD",
        asset_class=AssetClass.EQUITY,
        multiplier=Decimal("1"),
    )
    with pytest.raises(InstrumentNotResolvable, match="venue"):
        resolver.to_contract(instrument)


# --- resolve: happy path ----------------------------------------------------


async def test_resolve_returns_conid_from_qualify(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    qualified = ib_async.Contract(
        symbol="CAC.PA",
        secType="STK",
        exchange="SBF",
        currency="EUR",
        conId=42_424_242,
    )
    mock_ib = _make_mock_ib(qualify_returns=[qualified])
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)

    conid = await resolver.resolve(cac_pa)

    assert conid == 42_424_242
    mock_ib.qualifyContractsAsync.assert_awaited_once()


async def test_resolve_passes_constructed_contract_to_qualify(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """qualifyContractsAsync receives the Contract built by to_contract.

    Symbol is the Yahoo-stripped IB form (``CAC``), not the Yahoo form
    (``CAC.PA``). Per ADR-041 + DD-7 §3.1.
    """
    qualified = ib_async.Contract(conId=1)
    mock_ib = _make_mock_ib(qualify_returns=[qualified])
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)

    await resolver.resolve(cac_pa)

    sent = mock_ib.qualifyContractsAsync.await_args.args[0]
    assert sent.symbol == "CAC"
    assert sent.secType == "STK"
    assert sent.exchange == "SBF"
    assert sent.currency == "EUR"


async def test_resolve_caches_subsequent_calls(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """Second resolve of the same Instrument is a cache hit; no second wire trip."""
    qualified = ib_async.Contract(conId=99)
    mock_ib = _make_mock_ib(qualify_returns=[qualified])
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)

    first = await resolver.resolve(cac_pa)
    second = await resolver.resolve(cac_pa)

    assert first == second == 99
    assert mock_ib.qualifyContractsAsync.await_count == 1


async def test_resolve_consumes_global_token_only_on_wire_call(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """First resolve consumes one global token; cache hit consumes none."""
    qualified = ib_async.Contract(conId=1)
    mock_ib = _make_mock_ib(qualify_returns=[qualified])
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)

    before = rate_limiter.metrics()["global"].available
    await resolver.resolve(cac_pa)
    after_first = rate_limiter.metrics()["global"].available
    await resolver.resolve(cac_pa)  # cache hit
    after_second = rate_limiter.metrics()["global"].available

    assert after_first == before - Decimal(1)
    # No further token consumed on cache hit (the limiter may have refilled
    # in the intervening SimClock advance, but it must be ≥ after_first).
    assert after_second >= after_first


# --- resolve: rejection paths -----------------------------------------------


async def test_resolve_zero_candidates_raises_not_resolvable(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    mock_ib = _make_mock_ib(qualify_returns=[])
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)
    with pytest.raises(InstrumentNotResolvable, match="zero candidates"):
        await resolver.resolve(cac_pa)


async def test_resolve_zero_conid_raises_not_resolvable(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """conId=0 is ib_async's "unqualified" sentinel — treat as not resolvable."""
    qualified = ib_async.Contract(symbol="CAC.PA", secType="STK", conId=0)
    mock_ib = _make_mock_ib(qualify_returns=[qualified])
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)
    with pytest.raises(InstrumentNotResolvable, match="conId=0"):
        await resolver.resolve(cac_pa)


async def test_resolve_multiple_candidates_raises_ambiguous(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    candidates = [
        ib_async.Contract(symbol="CAC.PA", conId=1, primaryExchange="SBF", currency="EUR"),
        ib_async.Contract(symbol="CAC.PA", conId=2, primaryExchange="SBF", currency="USD"),
    ]
    mock_ib = _make_mock_ib(qualify_returns=candidates)
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)
    with pytest.raises(InstrumentAmbiguous) as excinfo:
        await resolver.resolve(cac_pa)
    assert excinfo.value.instrument == cac_pa
    assert len(excinfo.value.candidates) == 2
    assert excinfo.value.candidates[0].conId == 1
    assert excinfo.value.candidates[1].conId == 2


async def test_resolve_does_not_cache_failed_resolutions(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """A failed resolve is NOT cached — retry-after-fix should re-call qualify."""
    mock_ib = _make_mock_ib(qualify_returns=[])
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)

    with pytest.raises(InstrumentNotResolvable):
        await resolver.resolve(cac_pa)
    # Wire the mock to succeed on retry.
    qualified = ib_async.Contract(conId=7)
    mock_ib.qualifyContractsAsync = AsyncMock(return_value=[qualified])

    conid = await resolver.resolve(cac_pa)
    assert conid == 7


# --- clear_cache ------------------------------------------------------------


async def test_clear_cache_specific_instrument(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    qualified = ib_async.Contract(conId=11)
    mock_ib = _make_mock_ib(qualify_returns=[qualified])
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)

    await resolver.resolve(cac_pa)
    resolver.clear_cache(cac_pa)
    await resolver.resolve(cac_pa)

    # Cache invalidated → second resolve made a second wire call.
    assert mock_ib.qualifyContractsAsync.await_count == 2


async def test_clear_cache_none_flushes_all(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    aapl = Instrument(
        symbol="AAPL",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.EQUITY,
        multiplier=Decimal("1"),
    )
    mock_ib = _make_mock_ib(qualify_returns=[ib_async.Contract(conId=1)])
    resolver = _make_resolver(credentials, rate_limiter, clock, mock_ib)

    await resolver.resolve(cac_pa)
    await resolver.resolve(aapl)
    assert mock_ib.qualifyContractsAsync.await_count == 2

    resolver.clear_cache(None)

    await resolver.resolve(cac_pa)
    await resolver.resolve(aapl)
    assert mock_ib.qualifyContractsAsync.await_count == 4


def test_clear_cache_unknown_instrument_is_noop(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """clear_cache on an entry that isn't there must not raise."""
    resolver = _make_resolver(credentials, rate_limiter, clock, _make_mock_ib())
    resolver.clear_cache(cac_pa)  # cache is empty — no-op, no raise
