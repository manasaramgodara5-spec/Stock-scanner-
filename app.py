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

# फिलहाल stable NSE stock universe.
# बाद में इसे पूरी NSE list से expand किया जा सकता है.

ALL_NSE_STOCKS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "ITC", "LT", "BHARTIARTL", "AXISBANK",
    "KOTAKBANK", "HINDUNILVR", "BAJFINANCE", "MARUTI",
    "M&M", "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO",
    "HCLTECH", "NTPC", "POWERGRID", "TATASTEEL", "JSWSTEEL",
    "ADANIENT", "ADANIPORTS", "ONGC", "COALINDIA", "TATAMOTORS",
    "TATACONSUM", "TECHM", "INDUSINDBK", "HINDALCO",
    "GRASIM", "CIPLA", "DRREDDY", "DIVISLAB", "EICHERMOT",
    "HEROMOTOCO", "BAJAJ-AUTO", "APOLLOHOSP", "BPCL",
    "IOC", "BRITANNIA", "NESTLEIND", "ASIANPAINT",
    "PIDILITIND", "DABUR", "BEL", "HAL", "TRENT",
    "ZOMATO", "JIOFIN", "IRFC", "RVNL", "RECLTD",
    "PFC", "CANBK", "BANKBARODA", "PNB", "IDFCFIRSTB",
    "LICI", "SIEMENS", "ABB", "DLF", "INDHOTEL",
    "VBL", "INDIGO", "DMART", "BAJAJFINSV", "SHRIRAMFIN",
    "ICICIPRULI", "SBILIFE", "HDFCLIFE", "MOTHERSON",
    "TVSMOTOR", "ASHOKLEY", "BOSCHLTD", "VEDL",
    "SAIL", "NMDC", "JINDALSTEL", "HAVELLS",
    "VOLTAS", "CROMPTON", "POLYCAB", "DIXON",
    "PERSISTENT", "COFORGE", "LTIM", "MPHASIS",
    "BANDHANBNK", "FEDERALBNK", "IDBI", "YESBANK",
    "RBLBANK", "MANAPPURAM", "MUTHOOTFIN"
]


# ============================================================
# SETTINGS
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


PATTERN_NAMES = [
    "Hammer",
    "Bullish Engulfing",
    "Bearish Engulfing",
    "Piercing Line",
    "Dark Cloud Cover",
    "Shooting Star",
    "Morning Star",
    "Evening Star",
    "Inverted Hammer"
]


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

        # yfinance MultiIndex fix
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for col in required:
            if col not in df.columns:
                return pd.DataFrame()

        df = df[required].copy()
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
    df["BB_MID"] = df["Close"].rolling(20).mean()
    df["BB_STD"] = df["Close"].rolling(20).std()

    df["BB_UPPER"] = (
        df["BB_MID"] + 2 * df["BB_STD"]
    )

    df["BB_LOWER"] = (
        df["BB_MID"] - 2 * df["BB_STD"]
    )

    df["BB_WIDTH"] = (
        (df["BB_UPPER"] - df["BB_LOWER"])
        / df["BB_MID"]
    )

    # True Range
    previous_close = df["Close"].shift(1)

    tr1 = df["High"] - df["Low"]
    tr2 = abs(df["High"] - previous_close)
    tr3 = abs(df["Low"] - previous_close)

    df["TR"] = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    df["ATR"] = df["TR"].rolling(14).mean()

    return df


# ============================================================
# CANDLE VALUES
# ============================================================

def candle_values(row):

    open_price = float(row["Open"])
    high = float(row["High"])
    low = float(row["Low"])
    close = float(row["Close"])

    body = abs(close - open_price)

    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low

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
        lower_wick >= effective_body * 3
        and upper_wick <= effective_body * 0.5
        and close >= open_price
    )


# ============================================================
# INVERTED HAMMER
# ============================================================

def is_inverted_hammer(row):

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
        upper_wick >= effective_body * 2
        and lower_wick <= effective_body * 0.5
    )


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
        upper_wick >= effective_body * 2
        and lower_wick <= effective_body * 0.5
    )


# ============================================================
# BULLISH ENGULFING
# ============================================================

def is_bullish_engulfing(df, index):

    if index < 1:
        return False

    prev = df.iloc[index - 1]
    curr = df.iloc[index]

    prev_open = float(prev["Open"])
    prev_close = float(prev["Close"])

    curr_open = float(curr["Open"])
    curr_close = float(curr["Close"])

    previous_bearish = (
        prev_close < prev_open
    )

    current_bullish = (
        curr_close > curr_open
    )

    engulfing = (
        curr_open <= prev_close
        and curr_close >= prev_open
    )

    return (
        previous_bearish
        and current_bullish
        and engulfing
    )


# ============================================================
# BEARISH ENGULFING
# ============================================================

def is_bearish_engulfing(df, index):

    if index < 1:
        return False

    prev = df.iloc[index - 1]
    curr = df.iloc[index]

    prev_open = float(prev["Open"])
    prev_close = float(prev["Close"])

    curr_open = float(curr["Open"])
    curr_close = float(curr["Close"])

    previous_bullish = (
        prev_close > prev_open
    )

    current_bearish = (
        curr_close < curr_open
    )

    engulfing = (
        curr_open >= prev_close
        and curr_close <= prev_open
    )

    return (
        previous_bullish
        and current_bearish
        and engulfing
    )


# ============================================================
# PIERCING LINE
# ============================================================

def is_piercing_line(df, index):

    if index < 1:
        return False

    prev = df.iloc[index - 1]
    curr = df.iloc[index]

    prev_open = float(prev["Open"])
    prev_close = float(prev["Close"])

    curr_open = float(curr["Open"])
    curr_close = float(curr["Close"])

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

    prev = df.iloc[index - 1]
    curr = df.iloc[index]

    prev_open = float(prev["Open"])
    prev_close = float(prev["Close"])

    curr_open = float(curr["Open"])
    curr_close = float(curr["Close"])

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

    if first_body <= 0:
        return False

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

    if first_body <= 0:
        return False

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
# PATTERN CHECKER
# ============================================================

def check_pattern(df, pattern_name):

    if df.empty:
        return False

    index = len(df) - 1
    current = df.iloc[index]

    if pattern_name == "Hammer":
        return is_hammer(current)

    if pattern_name == "Inverted Hammer":
        return is_inverted_hammer(current)

    if pattern_name == "Shooting Star":
        return is_shooting_star(current)

    if pattern_name == "Bullish Engulfing":
        return is_bullish_engulfing(df, index)

    if pattern_name == "Bearish Engulfing":
        return is_bearish_engulfing(df, index)

    if pattern_name == "Piercing Line":
        return is_piercing_line(df, index)

    if pattern_name == "Dark Cloud Cover":
        return is_dark_cloud_cover(df, index)

    if pattern_name == "Morning Star":
        return is_morning_star(df, index)

    if pattern_name == "Evening Star":
        return is_evening_star(df, index)

    return False


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

        result = check_pattern(
            df,
            pattern_name
        )

        results.append(result)

    # AND logic
    return all(results)


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

    first_pos = np.argmin(
        first_half
    )

    second_pos = (
        20 + np.argmin(second_half)
    )

    if second_pos <= first_pos:
        return False

    between = lows[
        first_pos:second_pos + 1
    ]

    if len(between) < 5:
        return False

    neckline = np.max(between)

    bounce = (
        neckline - min(first_low, second_low)
    ) / min(first_low, second_low)

    valid_bounce = bounce >= 0.02

    current_close = float(
        df["Close"].iloc[-1]
    )

    near_second_bottom = (
        abs(current_close - second_low)
        / second_low
        <= 0.04
    )

    return (
        similar_lows
        and valid_bounce
        and near_second_bottom
    )


# ============================================================
# CONSOLIDATION
# ============================================================

def detect_consolidation(df):

    if len(df) < 30:
        return False

    recent = df.tail(20)

    high = float(
        recent["High"].max()
    )

    low = float(
        recent["Low"].min()
    )

    current_price = float(
        recent["Close"].iloc[-1]
    )

    if current_price <= 0:
        return False

    range_percent = (
        high - low
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
# CUP & HANDLE
# ============================================================

def detect_cup_handle(df):

    if len(df) < 80:
        return False

    recent = df.tail(80)

    prices = recent["Close"].values

    left = np.mean(prices[:15])

    middle = np.min(
        prices[25:55]
    )

    right = np.mean(
        prices[60:70]
    )

    current = prices[-1]

    if middle <= 0 or left <= 0:
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

    handle = (
        (
            np.max(prices[-10:])
            - np.min(prices[-10:])
        )
        / current
        <= 0.06
    )

    return cup and handle


# ============================================================
# STRATEGY CHECKER
# ============================================================

def check_strategy(
    df,
    strategy_name
):

    if strategy_name == "Double Bottom":
        return detect_double_bottom(df)

    if strategy_name == "Cup & Handle":
        return detect_cup_handle(df)

    if strategy_name == "Consolidation":
        return detect_consolidation(df)

    return False


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Scanner Settings")

selected_timeframe = st.sidebar.selectbox(
    "Timeframe",
    list(TIMEFRAME_MAP.keys())
)

scan_type = st.sidebar.radio(
    "Scan Type",
    [
        "Candlestick Pattern",
        "Strategy"
    ]
)


if scan_type == "Candlestick Pattern":

    scan_mode = st.sidebar.radio(
        "Pattern Mode",
        [
            "Single Pattern",
            "Multiple Patterns (AND)"
        ]
    )

    if scan_mode == "Single Pattern":

        selected_pattern = st.sidebar.selectbox(
            "Select Candlestick Pattern",
            PATTERN_NAMES
        )

        selected_patterns = [
            selected_pattern
        ]

    else:

        selected_patterns = st.sidebar.multiselect(
            "Select Candlestick Patterns",
            PATTERN_NAMES
        )

else:

    strategy_names = [
        "Double Bottom",
        "Cup & Handle",
        "Consolidation"
    ]

    selected_strategy = st.sidebar.selectbox(
        "Select Strategy",
        strategy_names
    )

    selected_patterns = []


# ============================================================
# STOCK LIMIT
# ============================================================

stock_limit = st.sidebar.slider(
    "Number of stocks to scan",
    min_value=10,
    max_value=len(ALL_NSE_STOCKS),
    value=min(50, len(ALL_NSE_STOCKS)),
    step=10
)


# ============================================================
# SCAN BUTTON
# ============================================================

scan_button = st.sidebar.button(
    "🔍 Start Scan",
    use_container_width=True
)


# ============================================================
# SCANNER
# ============================================================

if scan_button:

    if (
        scan_type == "Candlestick Pattern"
        and not selected_patterns
    ):
        st.warning(
            "कम से कम एक pattern चुनें."
        )
        st.stop()

    settings = TIMEFRAME_MAP[
        selected_timeframe
    ]

    interval = settings["interval"]
    period = settings["period"]

    stocks_to_scan = (
        ALL_NSE_STOCKS[:stock_limit]
    )

    results = []

    progress = st.progress(0)

    status = st.empty()

    total = len(stocks_to_scan)

    # --------------------------------------------------------
    # Parallel scanning
    # --------------------------------------------------------

    def scan_one_stock(symbol):

        df = get_stock_data(
            symbol,
            interval,
            period
        )

        if df.empty:
            return None

        df = add_indicators(df)

        if scan_type == "Candlestick Pattern":

            matched = check_selected_patterns(
                df,
                selected_patterns
            )

            pattern_tex
