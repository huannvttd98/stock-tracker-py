"""
Fetch fundamental data from VNDirect API.
Calculates P/E, P/B, EPS, BVPS, ROE from financial statements.

NOTE: VNDirect API ignores itemCode in q param. Must fetch batch
and filter client-side.
"""
import requests
from typing import Optional

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

VNDIRECT_API = "https://api-finfo.vndirect.com.vn/v4"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 12

# Item codes for financial statements
# Bank model: 23003=LNST, 413100=equity, 412100=total assets
# Non-bank model: 23003=LNST, 12700=total assets, 13000=total liabilities
ITEMS_NEEDED = {"23003", "413100", "412100", "12700", "13000"}


def _fetch_financial_batch(code: str) -> dict:
    """
    Fetch financial statements batch and filter client-side.
    Returns dict: {itemCode_reportType: {value, date}} with latest value per key.
    """
    try:
        resp = requests.get(
            f"{VNDIRECT_API}/financial_statements",
            params={"q": f"code:{code}", "size": 5000, "sort": "fiscalDate", "order": "desc"},
            headers=HEADERS, timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return {}

        records = resp.json().get("data", [])
        results = {}
        for item in records:
            ic = str(int(item.get("itemCode", 0)))
            if ic not in ITEMS_NEEDED:
                continue
            rt = item.get("reportType", "")
            fd = item.get("fiscalDate", "")
            val = item.get("numericValue")
            if val is None:
                continue

            key = f"{ic}_{rt}"
            if key not in results or fd > results[key]["date"]:
                results[key] = {"value": val, "date": fd, "type": rt}

        return results
    except Exception as e:
        logger.debug(f"VNDirect batch fetch error: {e}")
        return {}


def _pick_value(batch: dict, item_code: str, prefer_types=("ANNUAL", "ANNUAL2", "QUARTER", "QUARTER2")) -> Optional[float]:
    """Pick best value for an item code from batch, preferring report types in order."""
    for rt in prefer_types:
        key = f"{item_code}_{rt}"
        if key in batch and batch[key]["value"]:
            return batch[key]["value"]
    return None


def _get_total_shares(code: str) -> Optional[float]:
    """Get outstanding shares from VNDirect ratios."""
    try:
        resp = requests.get(
            f"{VNDIRECT_API}/ratios/latest",
            params={"filter": f"code:{code},ratioCode:TOTAL_SHARES", "order": "reportDate"},
            headers=HEADERS, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            if data and data[0].get("value"):
                return data[0]["value"]

        # Fallback: try OUTSTANDING_SHARES
        resp2 = requests.get(
            f"{VNDIRECT_API}/ratios",
            params={"q": f"code:{code}", "size": 100, "sort": "reportDate", "order": "desc"},
            headers=HEADERS, timeout=TIMEOUT,
        )
        if resp2.status_code == 200:
            for item in resp2.json().get("data", []):
                if item.get("ratioCode") == "OUTSTANDING_SHARES" and item.get("value"):
                    return item["value"]
        return None
    except Exception as e:
        logger.debug(f"VNDirect shares error: {e}")
        return None


def _get_company_info(code: str) -> dict:
    """Get company profile from VNDirect."""
    try:
        resp = requests.get(
            f"{VNDIRECT_API}/company_profiles",
            params={"q": f"code:{code}", "size": 1},
            headers=HEADERS, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            if data:
                return {
                    "name": data[0].get("vnName", ""),
                    "short_name": data[0].get("shortName", ""),
                    "floor": data[0].get("floor", ""),
                    "index": data[0].get("indexCode", ""),
                }
    except Exception as e:
        logger.debug(f"VNDirect company error: {e}")
    return {}


def get_fundamental(code: str, current_price: float) -> dict:
    """
    Get fundamental data for a stock.
    Returns dict with pe, pb, eps, bvps, roe, company info.
    Values may be None if data unavailable.
    """
    result = {
        "pe": None, "pb": None, "eps": None, "bvps": None,
        "roe": None, "company": {},
    }

    result["company"] = _get_company_info(code)

    total_shares = _get_total_shares(code)
    if not total_shares or total_shares <= 0:
        logger.debug(f"No share count for {code}")
        return result

    batch = _fetch_financial_batch(code)
    if not batch:
        logger.debug(f"No financial data for {code}")
        return result

    # Net profit after tax (LNST)
    net_profit = _pick_value(batch, "23003")

    # Equity: bank model has 413100 directly
    # Non-bank: calculate as total_assets - total_liabilities
    total_equity = _pick_value(batch, "413100")
    if not total_equity:
        ta = _pick_value(batch, "12700")
        tl = _pick_value(batch, "13000")
        if ta and tl:
            total_equity = ta - tl

    # Total assets: bank=412100, non-bank=12700
    total_assets = _pick_value(batch, "412100")
    if not total_assets:
        total_assets = _pick_value(batch, "12700")

    # Calculate ratios
    if net_profit and total_shares > 0:
        eps = net_profit / total_shares
        result["eps"] = round(eps, 0)
        if eps > 0 and current_price > 0:
            result["pe"] = round(current_price / eps, 2)

    if total_equity and total_shares > 0:
        bvps = total_equity / total_shares
        result["bvps"] = round(bvps, 0)
        if bvps > 0 and current_price > 0:
            result["pb"] = round(current_price / bvps, 2)

    if net_profit and total_equity and total_equity > 0:
        result["roe"] = round(net_profit / total_equity * 100, 2)

    return result
