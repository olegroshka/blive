"""Pull the IB *paper* account's Flex Activity Statement → daily NAV, and (when the
query includes them) open positions + trades, into the shared feeds under
``lab/reporting/nav/``.

blive owns the paper account's history — this never touches ForgeFolio. It uses
IB's **Flex Web Service** (the same read-only reporting API ForgeFolio uses for
the live account, just pointed at the paper account and owned here).

Feeds written (all keyed ``book = PAPER:<accountId>``):
  * ``paper_nav.csv``       — EquitySummaryByReportDateInBase (daily NAV)   [always]
  * ``positions_paper.csv`` — OpenPosition (per date × symbol holdings)     [if section present]
  * ``trades_paper.csv``    — Trade (per fill: qty, price, commission)      [if section present]

positions/trades power the per-leg reconciliation breakdown
(``lab/reporting/breakdown_theoretical_vs_paper.py``): coverage gap, integer-share
rounding, execution slippage, and commissions — plus the per-strategy paper split.

SETUP (one-time, in the PAPER account's IB Account Management):
  1. Reporting -> Flex Queries -> create an **Activity Statement** Flex query that
     INCLUDES these sections:
       - "Net Asset Value" / "Change in NAV" (Equity Summary)  [required, for NAV]
       - "Open Positions"                                       [for per-leg breakdown]
       - "Trades"                                               [for slippage/commissions]
     period = e.g. "Last 90 Calendar Days" (or Custom). Note its Query ID.
  2. Reporting -> Flex Web Service -> generate a **token**.
  3. Put them in ``~/.blive/secrets/ib_flex.env``:
         IB_FLEX_TOKEN=xxxxxxxx
         IB_FLEX_QUERY_ID=123456

    uv run python scripts/pull_paper_flex.py

It's a two-step web service (send request -> poll -> download XML), then parses
the sections above and upserts each feed idempotently.
"""

from __future__ import annotations

import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

_BASE = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService"
_NAV_DIR = Path(__file__).resolve().parents[2] / "lab" / "reporting" / "nav"
_FEED = _NAV_DIR / "paper_nav.csv"
_FEED_POS = _NAV_DIR / "positions_paper.csv"
_FEED_TRD = _NAV_DIR / "trades_paper.csv"
_SECRETS = Path.home() / ".blive" / "secrets" / "ib_flex.env"
_UA = {"User-Agent": "blive-flex/1.0"}  # IB rejects the default urllib UA


def _load_creds() -> tuple[str, str]:
    from dotenv import dotenv_values
    vals = dotenv_values(_SECRETS) if _SECRETS.is_file() else {}
    token, query = vals.get("IB_FLEX_TOKEN"), vals.get("IB_FLEX_QUERY_ID")
    if not token or not query:
        raise SystemExit(
            f"Missing IB_FLEX_TOKEN / IB_FLEX_QUERY_ID in {_SECRETS}. "
            "See the module docstring for the one-time Flex setup.")
    return token, query


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")


def _send_request(token: str, query: str) -> tuple[str, str]:
    root = ET.fromstring(_get(f"{_BASE}/SendRequest?t={token}&q={query}&v=3"))
    if (root.findtext("Status") or "").strip() != "Success":
        raise SystemExit(f"Flex SendRequest failed: {root.findtext('ErrorMessage') or ET.tostring(root)[:400]}")
    return root.findtext("ReferenceCode"), (root.findtext("Url") or f"{_BASE}/GetStatement")


def _get_statement(token: str, ref: str, base_url: str) -> str:
    for _ in range(12):
        xml = _get(f"{base_url}?t={token}&q={ref}&v=3")
        head = xml[:200]
        if "FlexQueryResponse" in head:            # statement is ready
            return xml
        if "in progress" in xml or "<Status>Warn" in xml:
            time.sleep(5)
            continue
        raise SystemExit(f"Flex GetStatement error: {xml[:400]}")
    raise SystemExit("Flex statement not ready after retries")


def _ymd(d: str) -> str | None:
    """Flex dates are YYYYMMDD; return YYYY-MM-DD or None if malformed."""
    d = (d or "").strip()
    return f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 and d.isdigit() else None


def _parse_nav(root: ET.Element) -> list[dict]:
    rows = []
    for e in root.iter("EquitySummaryByReportDateInBase"):
        d = _ymd(e.get("reportDate"))
        if not d:
            continue
        rows.append({
            "date": d,
            "book": f"PAPER:{e.get('accountId') or ''}",
            "nav": float(e.get("total") or 0),
            "gross_exposure": float(e.get("stock") or 0),
            "ccy": e.get("currency") or "",
            "source": "blive-flex",
        })
    if not rows:
        sections = sorted({el.tag for el in root.iter()})
        raise SystemExit("No EquitySummaryByReportDateInBase in the statement — the Flex query must "
                         "include the 'Net Asset Value / Equity Summary' section.\n"
                         f"Sections present: {', '.join(sections)[:500]}")
    return rows


def _parse_positions(root: ET.Element) -> list[dict]:
    rows = []
    for e in root.iter("OpenPosition"):
        d = _ymd(e.get("reportDate"))
        if not d:
            continue
        rows.append({
            "date": d,
            "book": f"PAPER:{e.get('accountId') or ''}",
            "symbol": e.get("symbol") or "",
            "quantity": float(e.get("position") or 0),
            "mark_price": float(e.get("markPrice") or 0),
            "value": float(e.get("positionValue") or 0),
            "ccy": e.get("currency") or "",
            "source": "blive-flex",
        })
    return rows


def _parse_trades(root: ET.Element) -> list[dict]:
    rows = []
    for e in root.iter("Trade"):
        d = _ymd(e.get("tradeDate") or e.get("reportDate"))
        if not d:
            continue
        rows.append({
            "date": d,
            "book": f"PAPER:{e.get('accountId') or ''}",
            "symbol": e.get("symbol") or "",
            "quantity": float(e.get("quantity") or 0),
            "price": float(e.get("tradePrice") or 0),
            "commission": float(e.get("ibCommission") or 0),
            "side": e.get("buySell") or "",
            "proceeds": float(e.get("proceeds") or 0),
            "trade_id": e.get("tradeID") or e.get("ibExecID") or "",
            "ccy": e.get("currency") or "",
            "source": "blive-flex",
        })
    return rows


def _upsert(feed: Path, rows: list[dict], keys: list[str]) -> None:
    """Idempotent upsert: replace any existing rows matching `keys`, then append."""
    if not rows:
        return
    feed.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(feed) if feed.is_file() else pd.DataFrame()
    new = pd.DataFrame(rows)
    if not df.empty and all(k in df.columns for k in keys):
        kset = {tuple(str(v) for v in t) for t in new[keys].itertuples(index=False)}
        mask = df[keys].astype(str).apply(lambda r: tuple(r) in kset, axis=1)
        df = df[~mask]
    df = pd.concat([df, new], ignore_index=True)
    sort_cols = [c for c in ("book", "date", "symbol") if c in df.columns]
    df = df.sort_values(sort_cols).reset_index(drop=True) if sort_cols else df
    df.to_csv(feed, index=False)


def main() -> int:
    token, query = _load_creds()
    ref, url = _send_request(token, query)
    print(f"Flex request sent (ref {ref}); waiting for statement ...")
    root = ET.fromstring(_get_statement(token, ref, url))

    nav = _parse_nav(root)
    _upsert(_FEED, nav, ["book", "date"])
    print(f"NAV       : {len(nav):>4} day(s)  -> {_FEED.name}   "
          f"({nav[0]['date']} .. {nav[-1]['date']}, {nav[-1]['book']} {nav[-1]['ccy']})")

    pos = _parse_positions(root)
    if pos:
        _upsert(_FEED_POS, pos, ["book", "date", "symbol"])
        print(f"positions : {len(pos):>4} row(s)  -> {_FEED_POS.name}")
    else:
        print("positions :  none  (add the 'Open Positions' section to the Flex query "
              "for the per-leg breakdown)")

    trd = _parse_trades(root)
    if trd:
        key = ["trade_id"] if all(r["trade_id"] for r in trd) else ["book", "date", "symbol", "quantity", "price"]
        _upsert(_FEED_TRD, trd, key)
        print(f"trades    : {len(trd):>4} fill(s) -> {_FEED_TRD.name}")
    else:
        print("trades    :  none  (add the 'Trades' section to the Flex query "
              "for slippage/commissions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
