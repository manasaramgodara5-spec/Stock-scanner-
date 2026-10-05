import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="NSE Stock Scanner",
    page_icon="📈",
    layout="wide"
)

st.title("📈 NSE Price Action & Candlestick Stock Scanner")
st.caption("Python + Streamlit + yfinance")


# ============================================================
# NSE STOCK UNIVERSE
# ============================================================

NSE_STOCKS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "ITC", "LT", "BHARTIARTL", "AXISBANK",
    "KOTAKBANK", "HINDUNILVR", "BAJFINANCE", "MARUTI",
    "SUNPHARMA", "TITAN", "ASIANPAINT", "ULTRACEMCO",
    "HCLTECH", "WIPRO", "NTPC", "POWERGRID", "M&M",
    "TATAMOTORS", "TATASTEEL", "ADANIENT", "ADANIPORTS",
    "COALINDIA", "ONGC", "JSWSTEEL", "TECHM",
    "NESTLEIND", "GRASIM", "HINDALCO", "CIPLA",
    "DRREDDY", "DIVISLAB", "EICHERMOT", "BAJAJFINSV",
    "BAJAJ-AUTO", "HEROMOTOCO", "APOLLOHOSP",
    "BRITANNIA", "BPCL", "IOC", "GAIL", "TATACONSUM",
    "INDUSINDBK", "SHRIRAMFIN", "BEL", "HAL",
    "TRENT", "ZOMATO", "JIOFIN", "IRFC", "RVNL",
    "DLF", "PIDILITIND", "SIEMENS", "ABB", "HAVELLS",
    "DABUR", "GODREJCP", "MARICO", "COLPAL",
    "AMBUJACEM", "ACC", "VEDL", "SAIL", "NMDC",
    "BANKBARODA", "PNB", "CANBK", "UNIONBANK",
    "IDFCFIRSTB", "FEDERALBNK", "INDIANB",
    "LICI", "PFC", "RECLTD", "NHPC", "SJVN",
    "IOC", "HINDPETRO", "MOTHERSON", "BOSCHLTD",
    "TVSMOTOR", "ASHOKLEY", "BHEL", "IRCTC",
    "CONCOR", "DIXON", "POLYCAB", "VOLTAS",
    "CUMMINSIND", "TORNTPHARM", "AUROPHARMA",
    "LUPIN", "ALKEM", "MAXHEALTH", "FORTIS",
    "INDHOTEL", "INDIGO", "ADANIGREEN", "ADANIPOWER",
    "TATAPOWER", "TATAELXSI", "PERSISTENT",
    "COFORGE", "MPHASIS", "LTIM", "OFSS",
    "CANFINHOME", "LICHSGFIN", "MFSL", "ICICIPRULI",
    "ICICIGI", "SBILIFE", "HDFCLIFE", "MUTHOOTFIN",
    "MANAPPURAM", "CHOLAFIN", "IDBI", "YESBANK"
]


# Remove duplicates
NSE_STOCKS = list(dict.fromkeys(NSE_STOCKS))


# ============================================================
# TIMEFRAME SETTINGS
# ============================================================

TIMEFRAME_MAP = {
    "5-minute": {
        "interval": "5m",
        "period": "5d"
    },
    "1-hour": {
        "interval": "1h",
        "period": "1mo"
    },
    "Daily": {
        "interval": "1d",
        "period": "1y"
    }
}


# ============================================================
# DATA DOWNLOAD
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_data(symbol, interval, period):

    ticker = f"{symbol}.NS"

    try:

        df = yf.download(
            ticker,
            interval=interval,
            period=period,
            auto_adjust=False,
            progress=False,
            threads=False
        )

        if df is None or df.empty:
            return pd.DataFrame()

        # Fix MultiIndex returned by yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for column in required_columns:
            if column not in df.columns:
                return pd.DataFrame()

        df = df[required_columns].copy()

        # Convert columns to numeric
        for column in required_columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df.dropna(inplace=True)

        return df

    except Exception:
        return pd.DataFrame()


# ============================================================
# INDICATORS
# ============================================================

def add_indicators(df):

    df = df.copy()

    df["EMA20"] = (
        df["Close"]
        .ewm(span=20, adjust=False)
        .mean()
    )

    df["EMA50"] = (
        df["Close"]
        .ewm(span=50, adjust=False)
        .mean()
    )

    # Bollinger Bands
    df["BB_MID"] = (
        df["Close"]
        .rolling(20)
        .mean()
    )

    df["BB_STD"] = (
        df["Close"]
        .rolling(20)
        .std()
    )

    df["BB_UPPER"] = (
        df["BB_MID"]
        + 2 * df["BB_STD"]
    )

    df["BB_LOWER"] = (
        df["BB_MID"]
        - 2 * df["BB_STD"]
    )

    df["BB_WIDTH"] = (
        (df["BB_UPPER"] - df["BB_LOWER"])
        / df["BB_MID"]
    )

    # ATR
    previous_close = df["Close"].shift(1)

    tr1 = df["High"] - df["Low"]

    tr2 = (
        df["High"] - previous_close
    ).abs()

    tr3 = (
        df["Low"] - previous_close
    ).abs()

    df["TR"] = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    df["ATR"] = (
        df["TR"]
        .rolling(14)
        .mean()
    )

    return df


# ============================================================
# CANDLE CALCULATION
# ============================================================

def candle_values(row):

    open_price = float(row["Open"])
    high = float(row["High"])
    low = float(row["Low"])
    close = float(row["Close"])

    body = abs(close - open_price)

    upper_wick = (
        high - max(open_price, close)
    )

    lower_wick = (
        min(open_price, close) - low
    )

    candle_range = high - low

    return (
        open_price,
        high,
        low,
        close,
        body,
        upper_wick,
        lower_wick,
        candle_range
    )


# ============================================================
# HAMMER
# ============================================================

def is_hammer(row):

    (
        open_price,
        high,
        low,
        close,
        body,
        upper_wick,
        lower_wick,
        candle_range
    ) = candle_values(row)

    if candle_range <= 0:
        return False

    effective_body = max(
        body,
        candle_range * 0.01
    )

    return (
        lower_wick >= 3 * effective_body
        and upper_wick <= 0.5 * effective_body
    )


# ============================================================
# HANGING MAN
# ============================================================

def is_hanging_man(df, index):

    if index < 1:
        return False

    row = df.iloc[index]

    if not is_hammer(row):
        return False

    previous_close = float(
        df["Close"].iloc[index - 1]
    )

    current_close = float(
        row["Close"]
    )

    # Previous movement should be upward
    return current_close > previous_close


# ============================================================
# SHOOTING STAR
# ============================================================

def is_shooting_star(row):

    (
        open_price,
        high,
        low,
        close,
        body,
        upper_wick,
        lower_wick,
        candle_range
    ) = candle_values(row)

    if candle_range <= 0:
        return False

    effective_body = max(
        body,
        candle_range * 0.01
    )

    return (
        upper_wick >= 2 * effective_body
        and lower_wick <= 0.5 * effective_body
    )


# ============================================================
# INVERTED HAMMER
# ============================================================

def is_inverted_hammer(df, index):

    if index < 1:
        return False

    row = df.iloc[index]

    (
        open_price,
        high,
        low,
        close,
        body,
        upper_wick,
        lower_wick,
        candle_range
    ) = candle_values(row)

    if candle_range <= 0:
        return False

    effective_body = max(
        body,
        candle_range * 0.01
    )

    return (
        upper_wick >= 2 * effective_body
        and lower_wick <= 0.5 * effective_body
    )


# ============================================================
# BULLISH ENGULFING
# ============================================================

def is_bullish_engulfing(df, index):

    if index < 1:
        return False

    previous = df.iloc[index - 1]
    current = df.iloc[index]

    prev_open = float(previous["Open"])
    prev_close = float(previous["Close"])

    curr_open = float(current["Open"])
    curr_close = float(current["Close"])

    previous_bearish = (
        prev_close < prev_open
    )

    current_bullish = (
        curr_close > curr_open
    )

    return (
        previous_bearish
        and current_bullish
        and curr_open <= prev_close
        and curr_close >= prev_open
    )


# ============================================================
# BEARISH ENGULFING
# ============================================================

def is_bearish_engulfing(df, index):

    if index < 1:
        return False

    previous = df.iloc[index - 1]
    current = df.iloc[index]

    prev_open = float(previous["Open"])
    prev_close = float(previous["Close"])

    curr_open = float(current["Open"])
    curr_close = float(current["Close"])

    previous_bullish = (
        prev_close > prev_open
    )

    current_bearish = (
        curr_close < curr_open
    )

    return (
        previous_bullish
        and current_bearish
        and curr_open >= prev_close
        and curr_close <= prev_open
    )


# ============================================================
# PIERCING LINE
# ============================================================

def is_piercing_line(df, index):

    if index < 1:
        return False

    previous = df.iloc[index - 1]
    current = df.iloc[index]

    prev_open = float(previous["Open"])
    prev_close = float(previous["Close"])

    curr_open = float(current["Open"])
    curr_close = float(current["Close"])

    if prev_close >= prev_open:
        return False

    if curr_close <= curr_open:
        return False

    midpoint = (
        prev_open + prev_close
    ) / 2

    return (
        curr_open < prev_close
        and curr_close > midpoint
        and curr_close < prev_open
    )


# ============================================================
# DARK CLOUD COVER
# ============================================================

def is_dark_cloud_cover(df, index):

    if index < 1:
        return False

    previous = df.iloc[index - 1]
    current = df.iloc[index]

    prev_open = float(previous["Open"])
    prev_close = float(previous["Close"])

    curr_open = float(current["Open"])
    curr_close = float(current["Close"])

    if prev_close <= prev_open:
        return False

    if curr_close >= curr_open:
        return False

    midpoint = (
        prev_open + prev_close
    ) / 2

    return (
        curr_open > prev_close
        and curr_close < midpoint
        and curr_close > prev_open
    )


# ============================================================
# MORNING STAR
# ============================================================

def is_morning_star(df, index):

    if index < 2:
        return False

    first = df.iloc[index - 2]
    second = df.iloc[index - 1]
    third = df.iloc[index]

    first_open = float(first["Open"])
    first_close = float(first["Close"])

    second_open = float(second["Open"])
    second_close = float(second["Close"])

    third_open = float(third["Open"])
    third_close = float(third["Close"])

    first_body = abs(
        first_close - first_open
    )

    second_body = abs(
        second_close - second_open
    )

    first_bearish = (
        first_close < first_open
    )

    third_bullish = (
        third_close > third_open
    )

    first_midpoint = (
        first_open + first_close
    ) / 2

    small_middle = (
        second_body <= first_body * 0.5
    )

    return (
        first_bearish
        and small_middle
        and third_bullish
        and third_close > first_midpoint
    )


# ============================================================
# EVENING STAR
# ============================================================

def is_evening_star(df, index):

    if index < 2:
        return False

    first = df.iloc[index - 2]
    second = df.iloc[index - 1]
    third = df.iloc[index]

    first_open = float(first["Open"])
    first_close = float(first["Close"])

    second_open = float(second["Open"])
    second_close = float(second["Close"])

    third_open = float(third["Open"])
    third_close = float(third["Close"])

    first_body = abs(
        first_close - first_open
    )

    second_body = abs(
        second_close - second_open
    )

    first_bullish = (
        first_close > first_open
    )

    third_bearish = (
        third_close < third_open
    )

    first_midpoint = (
        first_open + first_close
    ) / 2

    small_middle = (
        second_body <= first_body * 0.5
    )

    return (
        first_bullish
        and small_middle
        and third_bearish
        and third_close < first_midpoint
    )


# ============================================================
# PATTERN FUNCTIONS
# ============================================================

PATTERN_FUNCTIONS = {
    "Hammer": lambda df: is_hammer(df.iloc[-1]),

    "Hanging Man": lambda df:
        is_hanging_man(df, len(df) - 1),

    "Shooting Star": lambda df:
        is_shooting_star(df.iloc[-1]),

    "Inverted Hammer": lambda df:
        is_inverted_hammer(df, len(df) - 1),

    "Bullish Engulfing": lambda df:
        is_bullish_engulfing(df, len(df) - 1),

    "Bearish Engulfing": lambda df:
        is_bearish_engulfing(df, len(df) - 1),

    "Piercing Line": lambda df:
        is_piercing_line(df, len(df) - 1),

    "Dark Cloud Cover": lambda df:
        is_dark_cloud_cover(df, len(df) - 1),

    "Morning Star": lambda df:
        is_morning_star(df, len(df) - 1),

    "Evening Star": lambda df:
        is_evening_star(df, len(df) - 1),
}


# ============================================================
# MULTIPLE PATTERN CHECK
# ============================================================

def check_selected_patterns(
    df,
    selected_patterns
):

    if not selected_patterns:
        return False

    results = []

    for pattern_name in selected_patterns:

        pattern_function = (
            PATTERN_FUNCTIONS.get(pattern_name)
        )

        if pattern_function is None:
            return False

        result = pattern_function(df)

        results.append(result)

    # AND logic
    return all(results)


# ============================================================
# BULLISH CANDLE
# ============================================================

def bullish_candle(df):

    index = len(df) - 1

    return (
        is_hammer(df.iloc[index])
        or is_bullish_engulfing(df, index)
        or is_piercing_line(df, index)
        or is_morning_star(df, index)
        or is_inverted_hammer(df, index)
    )


# ============================================================
# DOUBLE BOTTOM
# ============================================================

def detect_double_bottom(df):

    if len(df) < 40:
        return False

    lows = df["Low"].values[-40:]

    first_half = lows[:20]
    second_half = lows[20:]

    first_low = np.min(first_half)
    second_low = np.min(second_half)

    if first_low <= 0:
        return False

    difference = (
        abs(first_low - second_low)
        / first_low
    )

    similar_lows = (
        difference <= 0.03
    )

    first_position = np.argmin(
        first_half
    )

    second_position = (
        20 + np.argmin(second_half)
    )

    if second_position <= first_position:
        return False

    between = lows[
        first_position:
        second_position + 1
    ]

    if len(between) < 5:
        return False

    neckline = np.max(between)

    bounce = (
        neckline - min(
            first_low,
            second_low
        )
    ) / min(
        first_low,
        second_low
    )

    valid_bounce = (
        bounce >= 0.02
    )

    current_close = float(
        df["Close"].iloc[-1]
    )

    near_second_bottom = (
        abs(
            current_close - second_low
        ) / second_low <= 0.04
    )

    return (
        similar_lows
        and valid_bounce
        and near_second_bottom
    )


def strategy_double_bottom(df):

    return (
        detect_double_bottom(df)
        and bullish_candle(df)
    )


# ============================================================
# CONSOLIDATION
# ============================================================

def detect_consolidation(df):

    if len(df) < 30:
        return False

    recent = df.tail(20)

    highest = recent["High"].max()
    lowest = recent["Low"].min()

    current_price = float(
        recent["Close"].iloc[-1]
    )

    if current_price <= 0:
        return False

    range_percent = (
        highest - lowest
    ) / current_price

    narrow_range = (
        range_percent <= 0.08
    )

    bb_width = float(
        df["BB_WIDTH"].iloc[-1]
    )

    squeeze = (
        not np.isnan(bb_width)
        and bb_width <= 0.12
    )

    return (
        narrow_range
        or squeeze
    )


# ============================================================
# RANGE BREAKOUT
# ============================================================

def strategy_range_breakout(df):

    if len(df) < 30:
        return False

    if not detect_consolidation(df):
        return False

    previous_range = df.iloc[-21:-1]

    resistance = (
        previous_range["High"].max()
    )

    current = df.iloc[-1]

    breakout = (
        float(current["Close"])
        > resistance
    )

    return breakout


# ============================================================
# TRIPLE BOTTOM
# ============================================================

def detect_triple_bottom(df):

    if len(df) < 60:
        return False

    lows = df["Low"].values[-60:]

    low1 = np.min(lows[:20])
    low2 = np.min(lows[20:40])
    low3 = np.min(lows[40:60])

    average_low = (
        low1 + low2 + low3
    ) / 3

    if average_low <= 0:
        return False

    tolerance = 0.04

    similar1 = (
        abs(low1 - average_low)
        / average_low
        <= tolerance
    )

    similar2 = (
        abs(low2 - average_low)
        / average_low
        <= tolerance
    )

    similar3 = (
        abs(low3 - average_low)
        / average_low
        <= tolerance
    )

    return (
        similar1
        and similar2
        and similar3
    )


# ============================================================
# CUP & HANDLE
# ============================================================

def detect_cup_handle(df):

    if len(df) < 80:
        return False

    recent = df.tail(80)

    prices = recent["Close"].values

    left = np.mean(
        prices[:15]
    )

    middle = np.min(
        prices[25:55]
    )

    right = np.mean(
        prices[60:70]
    )

    current = prices[-1]

    if left <= 0 or middle <= 0:
        return False

    left_drop = (
        left - middle
    ) / left

    right_recovery = (
        right - middle
    ) / middle

    cup = (
        left_drop >= 0.05
        and right_recovery >= 0.03
    )

    handle_range = (
        np.max(prices[-10:])
        - np.min(prices[-10:])
    )

    handle = (
        handle_range / current
        <= 0.06
    )

    return cup and handle


def strategy_cup_triple(df):

    return (
        detect_triple_bottom(df)
        or detect_cup_handle(df)
    )


# ============================================================
# CANDLE + EMA STRATEGY
# ============================================================

def strategy_candle_ema(df):

    if len(df) < 55:
        return False

    current = df.iloc[-1]

    if not bullish_candle(df):
        return False

    price = float(
        current["Close"]
    )

    em
