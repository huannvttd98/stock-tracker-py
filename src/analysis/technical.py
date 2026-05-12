"""
Technical Analysis: RSI, MA Crossover, Bollinger Bands.
All functions work with a list of close prices (oldest first).
"""
import math

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# === RSI ===
def calc_rsi(closes: list, period: int = 14):
    """Calculate RSI. Returns 0-100 or None if not enough data."""
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    # Use last `period` changes
    recent_gains = gains[-period:]
    recent_losses = losses[-period:]

    avg_gain = sum(recent_gains) / period
    avg_loss = sum(recent_losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 1)


def interpret_rsi(rsi: object) -> str:
    if rsi is None:
        return ""
    if rsi >= 70:
        return "QUA MUA"
    if rsi <= 30:
        return "QUA BAN"
    if rsi >= 60:
        return "Manh"
    if rsi <= 40:
        return "Yeu"
    return "Trung tinh"


# === Moving Average Crossover ===
def calc_sma(closes: list, period: int):
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def detect_ma_crossover(closes: list, fast: int = 5, slow: int = 20) :
    """
    Detect MA crossover between fast and slow SMA.
    Returns: 'GOLDEN_CROSS', 'DEATH_CROSS', or None.
    Needs at least slow+1 data points.
    """
    if len(closes) < slow + 1:
        return None

    # Current
    fast_now = calc_sma(closes, fast)
    slow_now = calc_sma(closes, slow)

    # Previous (exclude last price)
    prev = closes[:-1]
    fast_prev = calc_sma(prev, fast)
    slow_prev = calc_sma(prev, slow)

    if None in (fast_now, slow_now, fast_prev, slow_prev):
        return None

    # Golden Cross: fast crosses above slow
    if fast_prev <= slow_prev and fast_now > slow_now:
        return "GOLDEN_CROSS"

    # Death Cross: fast crosses below slow
    if fast_prev >= slow_prev and fast_now < slow_now:
        return "DEATH_CROSS"

    return None


def get_ma_position(closes: list, fast: int = 5, slow: int = 20) :
    """Return current MA position: 'ABOVE' (bullish) or 'BELOW' (bearish)."""
    fast_now = calc_sma(closes, fast)
    slow_now = calc_sma(closes, slow)
    if fast_now is None or slow_now is None:
        return None
    return "ABOVE" if fast_now > slow_now else "BELOW"


# === Bollinger Bands ===
def calc_bollinger(closes: list, period: int = 20, num_std: float = 2.0) :
    """
    Calculate Bollinger Bands.
    Returns: {upper, middle, lower, bandwidth, position} or None.
    position: 0.0 = at lower band, 1.0 = at upper band.
    """
    if len(closes) < period:
        return None

    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = math.sqrt(variance)

    upper = middle + num_std * std
    lower = middle - num_std * std

    current = closes[-1]
    bandwidth = (upper - lower) / middle * 100 if middle else 0

    # Position relative to bands (0 = lower, 1 = upper)
    band_range = upper - lower
    position = (current - lower) / band_range if band_range else 0.5

    return {
        "upper": round(upper, 0),
        "middle": round(middle, 0),
        "lower": round(lower, 0),
        "bandwidth": round(bandwidth, 2),
        "position": round(position, 2),
    }


def interpret_bollinger(bb) -> str:
    if bb is None:
        return ""
    pos = bb["position"]
    if pos >= 1.0:
        return "TREN BANG TREN (breakout)"
    if pos <= 0.0:
        return "DUOI BANG DUOI (breakout)"
    if pos >= 0.8:
        return "Gan bang tren"
    if pos <= 0.2:
        return "Gan bang duoi"
    return "Trong bang"


# === MACD ===
def calc_ema(closes: list, period: int) -> list:
    """Calculate Exponential Moving Average. Returns list same length as closes."""
    if len(closes) < period:
        return []
    multiplier = 2 / (period + 1)
    ema = [sum(closes[:period]) / period]
    for price in closes[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema


def calc_macd(closes: list, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Calculate MACD(12,26,9).
    Returns: {macd, signal, histogram, crossover} or None.
    crossover: 'BULLISH' (MACD crosses above signal), 'BEARISH', or None.
    """
    if len(closes) < slow + signal:
        return None

    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)

    # Align: ema_fast starts at index fast-1, ema_slow starts at index slow-1
    offset = slow - fast
    macd_line = [f - s for f, s in zip(ema_fast[offset:], ema_slow)]

    if len(macd_line) < signal:
        return None

    signal_line = calc_ema(macd_line, signal)
    # Align macd_line with signal_line
    macd_now = macd_line[-1]
    signal_now = signal_line[-1]
    histogram = macd_now - signal_now

    # Crossover detection
    crossover = None
    if len(macd_line) >= 2 and len(signal_line) >= 2:
        macd_prev = macd_line[-2]
        signal_prev = signal_line[-2]
        if macd_prev <= signal_prev and macd_now > signal_now:
            crossover = "BULLISH"
        elif macd_prev >= signal_prev and macd_now < signal_now:
            crossover = "BEARISH"

    return {
        "macd": round(macd_now, 2),
        "signal": round(signal_now, 2),
        "histogram": round(histogram, 2),
        "crossover": crossover,
    }


def interpret_macd(macd_data) -> str:
    if macd_data is None:
        return ""
    if macd_data["crossover"] == "BULLISH":
        return "MACD cat len Signal (MUA)"
    if macd_data["crossover"] == "BEARISH":
        return "MACD cat xuong Signal (BAN)"
    if macd_data["histogram"] > 0:
        return "MACD ↑ Signal (xu huong tang)"
    if macd_data["histogram"] < 0:
        return "MACD ↓ Signal (xu huong giam)"
    return "Trung tinh"


# === Full Analysis ===
def analyze_symbol(closes: list) :
    """Run all indicators on a symbol. Returns analysis dict or None."""
    if len(closes) < 21:
        return None

    rsi = calc_rsi(closes)
    crossover = detect_ma_crossover(closes)
    ma_pos = get_ma_position(closes)
    bb = calc_bollinger(closes)
    macd = calc_macd(closes)

    # Score: positive = bullish, negative = bearish
    score = 0
    signals = []

    # RSI
    if rsi is not None:
        if rsi <= 30:
            score += 2
            signals.append(f"RSI {rsi} (qua ban)")
        elif rsi >= 70:
            score -= 2
            signals.append(f"RSI {rsi} (qua mua)")
        elif rsi <= 40:
            score += 1
            signals.append(f"RSI {rsi}")
        elif rsi >= 60:
            score -= 1
            signals.append(f"RSI {rsi}")

    # MA Crossover
    if crossover == "GOLDEN_CROSS":
        score += 3
        signals.append("Golden Cross (MA5↑MA20)")
    elif crossover == "DEATH_CROSS":
        score -= 3
        signals.append("Death Cross (MA5↓MA20)")
    elif ma_pos == "ABOVE":
        score += 1
        signals.append("MA5 ↑ MA20")
    elif ma_pos == "BELOW":
        score -= 1
        signals.append("MA5 ↓ MA20")

    # Bollinger Bands
    if bb:
        if bb["position"] <= 0.0:
            score += 2
            signals.append("Pha bang duoi BB")
        elif bb["position"] >= 1.0:
            score -= 2
            signals.append("Pha bang tren BB")
        elif bb["position"] <= 0.2:
            score += 1
            signals.append("Gan day BB")
        elif bb["position"] >= 0.8:
            score -= 1
            signals.append("Gan dinh BB")

    # MACD
    if macd:
        if macd["crossover"] == "BULLISH":
            score += 2
            signals.append("MACD Bullish Cross")
        elif macd["crossover"] == "BEARISH":
            score -= 2
            signals.append("MACD Bearish Cross")
        elif macd["histogram"] > 0:
            score += 1
            signals.append("MACD ↑ Signal")
        elif macd["histogram"] < 0:
            score -= 1
            signals.append("MACD ↓ Signal")

    return {
        "rsi": rsi,
        "crossover": crossover,
        "ma_position": ma_pos,
        "bollinger": bb,
        "macd": macd,
        "score": score,
        "signals": signals,
    }


# === Support / Resistance ===
def calc_support_resistance(closes: list, period: int = 20):
    """
    Find nearest support and resistance levels from recent highs/lows.
    Returns {support, resistance} or None.
    """
    if len(closes) < period:
        return None

    window = closes[-period:]
    current = closes[-1]

    # Find local minima (support) and maxima (resistance)
    supports = []
    resistances = []

    for i in range(1, len(window) - 1):
        if window[i] <= window[i - 1] and window[i] <= window[i + 1]:
            supports.append(window[i])
        if window[i] >= window[i - 1] and window[i] >= window[i + 1]:
            resistances.append(window[i])

    # Nearest support below current price
    support = None
    below = [s for s in supports if s < current]
    if below:
        support = max(below)

    # Nearest resistance above current price
    resistance = None
    above = [r for r in resistances if r > current]
    if above:
        resistance = min(above)

    # Fallback: use period min/max
    if support is None:
        support = min(window)
    if resistance is None:
        resistance = max(window)

    return {
        "support": round(support, 0),
        "resistance": round(resistance, 0),
    }


def calc_ma_multi(closes: list):
    """Calculate MA5, MA10, MA20, MA50. Returns dict or None."""
    result = {}
    for period in [5, 10, 20, 50]:
        val = calc_sma(closes, period)
        if val is not None:
            result[f"ma{period}"] = round(val, 0)
    return result if result else None


def classify_trend(closes: list):
    """
    Classify trend based on MA alignment.
    Returns: 'TANG MANH', 'TANG', 'DI NGANG', 'GIAM', 'GIAM MANH'
    """
    if len(closes) < 50:
        if len(closes) < 20:
            return None
        ma5 = calc_sma(closes, 5)
        ma20 = calc_sma(closes, 20)
        if ma5 > ma20:
            return "TANG"
        elif ma5 < ma20:
            return "GIAM"
        return "DI NGANG"

    ma5 = calc_sma(closes, 5)
    ma20 = calc_sma(closes, 20)
    ma50 = calc_sma(closes, 50)

    if ma5 > ma20 > ma50:
        return "TANG MANH"
    elif ma5 > ma20:
        return "TANG"
    elif ma5 < ma20 < ma50:
        return "GIAM MANH"
    elif ma5 < ma20:
        return "GIAM"
    return "DI NGANG"
