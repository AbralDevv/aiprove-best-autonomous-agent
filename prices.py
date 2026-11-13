"""Live market data for the prediction handlers. Nothing here is hardcoded:
every forecast is computed from data fetched at run time.

Sources (all public, no API key):
  - CoinGecko public API: BTC/ETH spot price, 24h change, 7d daily closes.
  - Yahoo Finance chart API: SPY / GLD / NVDA daily closes (5d window).
  - ponsfamily.com app API: freshly launched tokens (top-5 bounty).

Each fetch retries briefly; a failed source raises DataError and the
affected bounty is skipped with the reason logged (never guessed).
"""
import json
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}


class DataError(RuntimeError):
    pass


def _get_json(url, retries=2):
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=dict(UA))
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:  # noqa: BLE001 - network flakiness: retry, then raise
            last = e
            time.sleep(1 * attempt)
    raise DataError(f"GET {url} failed after {retries} attempts: {last}")


# ------------------------------------------------------------------- crypto
def get_crypto(coin_id):
    """Return dict(price, change_24h_pct, closes_7d) for a CoinGecko id
    ('bitcoin' / 'ethereum'). closes_7d is a list of (ts_ms, price)."""
    try:
        px = _get_json(
            "https://api.coingecko.com/api/v3/simple/price"
            f"?ids={coin_id}&vs_currencies=usd&include_24hr_change=true")
        chart = _get_json(
            "https://api.coingecko.com/api/v3/coins"
            f"/{coin_id}/market_chart?vs_currency=usd&days=7&interval=daily")
    except DataError as e:
        raise DataError(f"CoinGecko {coin_id}: {e}")
    entry = px.get(coin_id)
    if not entry or "usd" not in entry:
        raise DataError(f"CoinGecko {coin_id}: no price in response {str(px)[:200]}")
    closes = [(p[0], p[1]) for p in chart.get("prices", []) if len(p) == 2]
    return {"price": entry["usd"],
            "change_24h_pct": entry.get("usd_24h_change"),
            "closes_7d": closes}


def pct_change(first, last):
    return (last - first) / first * 100.0 if first else 0.0


# ------------------------------------------------------------------- stocks
def get_stock(ticker):
    """Return dict(last, closes) for a Yahoo ticker from the 5d daily chart.
    closes is a list of daily closes, oldest first, Nones dropped."""
    try:
        d = _get_json(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            "?range=5d&interval=1d")
    except DataError as e:
        raise DataError(f"Yahoo {ticker}: {e}")
    try:
        result = d["chart"]["result"][0]
        closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
        last = result["meta"].get("regularMarketPrice") or closes[-1]
    except (KeyError, IndexError, TypeError) as e:
        raise DataError(f"Yahoo {ticker}: unexpected chart shape: {e}")
    if len(closes) < 2:
        raise DataError(f"Yahoo {ticker}: only {len(closes)} closes, need >= 2")
    return {"last": last, "closes": closes}


# --------------------------------------------------------------------- pons
PONS_API = "https://ponsfamily.com/api/launches"


def get_pons_top5(max_pages=20, n=5):
    """Top `n` tokens launched on pons in the last 24h, by market cap (USD).

    Pages sort=newest (40/page, cursor pagination) until launches older than
    24h appear, then ranks the 24h set by marketCapUsd. Returns a list of
    dicts (symbol, address, marketCapUsd, age_hours). Callers that dedupe
    by symbol ask for more than 5 and trim down."""
    cutoff = time.time() - 24 * 3600
    recent = []
    cursor = None
    for _ in range(max_pages):
        url = PONS_API + "?sort=newest" + (f"&cursor={cursor}" if cursor else "")
        try:
            d = _get_json(url)
        except DataError as e:
            raise DataError(f"pons launches: {e}")
        items = d.get("items", [])
        if not items:
            break
        for it in items:
            if it.get("createdAt", 0) >= cutoff:
                recent.append(it)
        oldest = min(it.get("createdAt", 0) for it in items)
        cursor = d.get("nextCursor")
        if oldest < cutoff or not cursor:
            break
    if len(recent) < 5:
        raise DataError(f"pons: only {len(recent)} launches in the last 24h, need 5")
    recent.sort(key=lambda it: it.get("marketCapUsd") or 0, reverse=True)
    now = time.time()
    return [{"symbol": it["symbol"], "address": it["address"],
             "marketCapUsd": it.get("marketCapUsd"),
             "age_hours": round((now - it["createdAt"]) / 3600, 1)}
            for it in recent[:n]]
