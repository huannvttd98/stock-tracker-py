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


# === Full Analysis ===
def analyze_symbol(closes: list) :
    """Run all indicators on a symbol. Returns analysis dict or None."""
    if len(closes) < 21:
        return None

    rsi = calc_rsi(closes)
    crossover = detect_ma_crossover(closes)
    ma_pos = get_ma_position(closes)
    bb = calc_bollinger(closes)

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
        signals.append("Golden Cross (MA5>MA20)")
    elif crossover == "DEATH_CROSS":
        score -= 3
        signals.append("Death Cross (MA5<MA20)")
    elif ma_pos == "ABOVE":
        score += 1
        signals.append("MA5 > MA20")
    elif ma_pos == "BELOW":
        score -= 1
        signals.append("MA5 < MA20")

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

    return {
        "rsi": rsi,
        "crossover": crossover,
        "ma_position": ma_pos,
        "bollinger": bb,
        "score": score,
        "signals": signals,
    }
