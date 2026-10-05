from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta


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
# NSE STOCK LIST
# ============================================================

# You can replace/expand this list with your own NSE universe.
def check_selected_patterns(df, selected_patterns):
    """
    सभी selected patterns को check करता है।
    सभी TRUE होने पर ही TRUE return करेगा.
    """

    if not selected_patterns:
        return False

    results = []

    for pattern_name in selected_patterns:

       pattern_function = PATTERN_FUNCTIONS[pattern_name]

       result = pattern_function(df)

       results.append(result)

    # AND logic
    return all(results)
    @st.cache_data(ttl=24 * 60 * 60, show_spinner=False)

def get_nse_stocks_by_market_cap():
    """
    Fetch NSE stocks from Yahoo Finance and return only
    stocks havinMarketet Cap > ₹100 Crore.

    Cache duration: 24 hours
    """

    # NSE equity symbols
    nse_url = (
        "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"
    )

    # For a complete NSE universe, maintain/use your NSE symbols list.
    # Example base universe:
    symbols = [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
        "SBIN", "ITC", "LT","BHARTIARTLTL", "AXISBANK"
    ]

    # Convert NSE symbols to Yahoo Finance format
    tickers = [symbol + ".NS" for symbol in symbols]

    def get_market_cap(ticker):
        try:
            stock = yf.Ticker(ticker)

            # fast_info is preferable when marketCap is available
            market_cap = stock.fast_info.get("market_cap", None)

            if market_cap is None:
                # Fallback to info
                market_cap = stock.info.get("marketCap", None)

            if market_cap and market_cap > MIN_MARKET_CAP:
                return ticker.replace(".NS", "")

        except Exception:
            pass

        return None

    valid_stocks = []

    # Query several stocks concurrently instead of one-by-one
    with ThreadPoolExecutor(max_workers=8) as executor:

        futures = [
            executor.submit(get_market_cap, ticker)
            for ticker in tickers
        ]

        for future in as_completed(futures):
            result = future.result()

            if result:
                valid_stocks.append(result)

    return sorted(valid_stocks) NSE_STOCKS = [
    "RELIANCE",
    "TCS",
    "INFY",
    ...
    ]# Original NSE universe
ALL_NSE_STOCKS = [
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "ITC",
    "LT",
    "BHARTIARTL",
    "AXISBANK",
    # ... your complete NSE symbol list
]

# Dynamically filter by Market Cap > ₹100 Crore
NSE_STOCKS = filter_stocks_by_market_cap(ALL_NSE_STOCKS)
def is_hammer(df):
    if len(df) < 1:
        return False

    c = df.iloc[-1]

    body = abs(c["Close"] - c["Open"])
    lower_shadow = min(c["Open"], c["Close"]) - c["Low"]
    upper_shadow = c["High"] - max(c["Open"], c["Close"])

    # Zero body से division/logic problem रोकने के लिए
    if body <= 0:
        return False

    return (
        lower_shadow >= 3 * body
        and upper_shadow <= body * 0.5
    )


def is_bullish_engulfing(df):
    if len(df) < 2:
        return False

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    prev_bearish = prev["Close"] < prev["Open"]
    curr_bullish = curr["Close"] > curr["Open"]

    return (
        prev_bearish
        and curr_bullish
        and curr["Open"] <= prev["Close"]
        and curr["Close"] >= prev["Open"]
    )


def is_bearish_engulfing(df):
    if len(df) < 2:
        return False

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    prev_bullish = prev["Close"] > prev["Open"]
    curr_bearish = curr["Close"] < curr["Open"]

    return (
        prev_bullish
        and curr_bearish
        and curr["Open"] >= prev["Close"]
        and curr["Close"] <= prev["Open"]
    )


def is_piercing_line(df):
    if len(df) < 2:
        return False

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    prev_bearish = prev["Close"] < prev["Open"]
    curr_bullish = curr["Close"] > curr["Open"]

    previous_midpoint = (prev["Open"] + prev["Close"]) / 2

    return (
        prev_bearish
        and curr_bullish
        and curr["Open"] < prev["Close"]
        and curr["Close"] > previous_midpoint
        and curr["Close"] < prev["Open"]
    )PATTERN_FUNCTIONS = {
    "Hammer": is_hammer,
    "Bullish Engulfing": is_bullish_engulfing,
    "Bearish Engulfing": is_bearish_engulfing,
    "Piercing Line": is_piercing_line,
    }def is_shooting_star(df):
    ...st.subheader("Candlestick Pattern Scanner")
results = []

for symbol in NSE_STOCKS:

    try:

        df = yf.download(
            f"{symbol}.NS",
            period="3mo",
            interval=selected_interval,
            progress=False,
            auto_adjust=False
        )

        if df.empty:
            continue

        # MultiIndex होने पर ठीक करना
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Single Pattern
        if scan_mode == "Single Pattern":

            matched = check_selected_patterns(
                df,
                [selected_pattern]
            )

        # Multiple Patterns
        else:

            if not selected_patterns:
                st.warning("कम से कम एक pattern चुनें.")
                st.stop()

            matched = check_selected_patterns(
                df,
                selected_patterns
            )

        if matched:

            results.append({
                "Symbol": symbol,
                "Pattern": (
                    selected_pattern
                    if scan_mode == "Single Pattern"
                    else ", ".join(selected_patterns)
                ),
                "Close": float(df["Close"].iloc[-1])
            })

    except Exception as e:
        continue
if results:

    result_df = pd.DataFrame(results)

    st.success(
        f"{len(result_df)} stocks matched the selected conditions."
    )

    st.dataframe(
        result_df,
        use_container_width=True
    )

else:

    st.info("कोई stock सभी selected conditions को पूरा नहीं करता.") scan_mode = st.radio(
    "Scan Mode",
    ["Single Pattern", "Multiple Patterns (AND)"],
    horizontal=True
)if scan_mode == "Single Pattern":

    selected_pattern = st.selectbox(
        "Select Candlestick Pattern",
        list(PATTERN_FUNCTIONS.keys())
    )else:

    selected_patterns = st.multiselect(
        "Select Candlestick Patterns",
        list(PATTERN_FUNCTIONS.keys())
    )LULUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULU
LUULLUULLUULLUULLUULLUULLUULLUULU
LUULULLUULLUULLUULLUULULLULUULLUULLUULLUULULLUULULLUULULUL

LUULLULUULLUULULLUULLULULUULLUULLUULLUULL
ULLULUULLUULLUULLULULUULLUULLUULL
UsymboUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULL
ULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULL
ULULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUULLUUP


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
            progress=False
        )

        if df is None or df.empty:
            return pd.DataFrame()

        # Handle yfinance MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required = ["Open", "High", "Low", "Close", "Volume"]

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

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # Bollinger Bands
    df["BB_MID"] = df["Close"].rolling(20).mean()
    df["BB_STD"] = df["Close"].rolling(20).std()

    df["BB_UPPER"] = df["BB_MID"] + 2 * df["BB_STD"]
    df["BB_LOWER"] = df["BB_MID"] - 2 * df["BB_STD"]

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
# CANDLE CALCULATIONS
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

    # Avoid division by zero
    effective_body = max(body, candle_range * 0.01)

    return (
        lower_wick >= effective_body * 2
        and upper_wick <= effective_body * 0.5
        and close >= open_price * 0.98
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

    previous_bearish = prev_close < prev_open
    current_bullish = curr_close > curr_open

    engulfing = (
        curr_open <= prev_close
        and curr_close >= prev_open
    )

    return previous_bearish and current_bullish and engulfing


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

    midpoint = (prev_open + prev_close) / 2

    return (
        curr_open < prev_close
        and curr_close > midpoint
        and curr_close < prev_open
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

    first_body = abs(
        float(first["Close"]) - float(first["Open"])
    )

    second_body = abs(
        float(second["Close"]) - float(second["Open"])
    )

    third_body = abs(
        float(third["Close"]) - float(third["Open"])
    )

    first_bearish = first["Close"] < first["Open"]
    third_bullish = third["Close"] > third["Open"]

    first_midpoint = (
        float(first["Open"]) + float(first["Close"])
    ) / 2

    small_middle = second_body < first_body * 0.5

    return (
        first_bearish
        and small_middle
        and third_bullish
        and third["Close"] > first_midpoint
        and third_body > second_body
    )


# ============================================================
# ANY BULLISH CANDLE
# ============================================================

def bullish_candle(df, index):

    row = df.iloc[index]

    return (
        is_hammer(row)
        or is_bullish_engulfing(df, index)
        or is_morning_star(df, index)
    )


# ============================================================
# DOUBLE BOTTOM
# ============================================================

def detect_double_bottom(df):

    if len(df) < 40:
        return False

    lows = df["Low"].values

    recent = lows[-40:]

    first_half = recent[:20]
    second_half = recent[20:]

    first_low = np.min(first_half)
    second_low = np.min(second_half)

    if first_low <= 0:
        return False

    difference = abs(first_low - second_low) / first_low

    # Two bottoms within 3%
    similar_lows = difference <= 0.03

    # Find neckline between the two bottoms
    first_pos = np.argmin(first_half)
    second_pos = 20 + np.argmin(second_half)

    if second_pos <= first_pos:
        return False

    between = lows[first_pos:second_pos + 1]

    if len(between) < 5:
        return False

    neckline = np.max(between)

    current_close = float(df["Close"].iloc[-1])

    # Price should have bounced between bottoms
    bounce = (
        neckline - min(first_low, second_low)
    ) / min(first_low, second_low)

    valid_bounce = bounce >= 0.02

    # Current candle near second support
    near_second_bottom = (
        abs(current_close - second_low) / second_low <= 0.04
    )

    return (
        similar_lows
        and valid_bounce
        and near_second_bottom
    )


# ============================================================
# DOUBLE BOTTOM + BULLISH CANDLE
# ============================================================

def strategy_double_bottom(df):

    if len(df) < 40:
        return False

    if not detect_double_bottom(df):
        return False

    return bullish_candle(df, len(df) - 1)


# ============================================================
# CONSOLIDATION / SQUEEZE
# ============================================================

def detect_consolidation(df):

    if len(df) < 30:
        return False

    recent = df.tail(20)

    high = recent["High"].max()
    low = recent["Low"].min()

    current_price = float(recent["Close"].iloc[-1])

    if current_price <= 0:
        return False

    range_percent = (high - low) / current_price

    # Narrow price range
    narrow_range = range_percent <= 0.08

    bb_width = float(df["BB_WIDTH"].iloc[-1])

    # Bollinger squeeze
    squeeze = bb_width <= 0.12

    return narrow_range or squeeze


# ============================================================
# RANGE BREAKOUT
# ============================================================

def strategy_range_breakout(df):

    if len(df) < 30:
        return False

    if not detect_consolidation(df):
        return False

    previous = df.iloc[-2]
    current = df.iloc[-1]

    previous_range = df.iloc[-21:-1]

    resistance = previous_range["High"].max()

    breakout = (
        float(current["Close"]) > resistance
    )

    candle_reversal = (
        is_hammer(current)
        or is_bullish_engulfing(df, len(df) - 1)
    )

    return breakout or candle_reversal


# ============================================================
# TRIPLE BOTTOM
# ============================================================

def detect_triple_bottom(df):

    if len(df) < 60:
        return False

    lows = df["Low"].values[-60:]

    # Divide into 3 sections
    section_size = 20

    low1 = np.min(lows[:20])
    low2 = np.min(lows[20:40])
    low3 = np.min(lows[40:60])

    average_low = (
        low1 + low2 + low3
    ) / 3

    if average_low <= 0:
        return False

    tolerance = 0.04

    similar1 = abs(low1 - average_low) / average_low <= tolerance
    similar2 = abs(low2 - average_low) / average_low <= tolerance
    similar3 = abs(low3 - average_low) / average_low <= tolerance

    return similar1 and similar2 and similar3


# ============================================================
# CUP & HANDLE APPROXIMATION
# ============================================================

def detect_cup_handle(df):

    if len(df) < 80:
        return False

    recent = df.tail(80)

    prices = recent["Close"].values

    left = np.mean(prices[:15])
    middle = np.min(prices[25:55])
    right = np.mean(prices[60:70])

    current = prices[-1]

    if middle <= 0:
        return False

    left_drop = (left - middle) / left
    right_recovery = (right - middle) / middle

    # Cup should have a meaningful U-shaped decline/recovery
    cup = (
        left_drop >= 0.05
        and right_recovery >= 0.03
    )

    # Handle = small recent consolidation
    handle = (
        np.max(prices[-10:])
        - np.min(prices[-10:])
    ) / current <= 0.06

    return cup and handle


# ============================================================
# STRATEGY 3
# ============================================================

def strategy_cup_triple(df):

    return (
        detect_triple_bottom(df)
        or detect_cup_handle(df)
    )


# ============================================================
# STRATEGY 4
# ============================================================

def strategy_custom_candle_ma(df, selected_patterns, ma_choice):

    if len(df) < 55:
        return False

    index = len(df) - 1
    current = df.iloc[index]

    pattern_found = False

    if "Hammer" in selected_patterns:
        pattern_found |= is_hammer(current)

    if "Bullish Engulfing" in selected_patterns:
        pattern_found |= is_bullish_engulfing(df, index)

    if "Piercing Line" in selected_patterns:
        pattern_found |= is_piercing_line(df, index)

    if "Morning Star" in selected_patterns:
        pattern_found |= is_morning_star(df, index)

    if not pattern_found:
        return False

    price = float(current["Close"])

    ema20 = float(current["EMA20"])
    ema50 = float(current["EMA50"])

    near_20 = abs(price - ema20) / ema20 <= 0.03
    near_50 = abs(price - ema50) / ema50 <= 0.03

    above_20 = price >= ema20
    above_50 = price >= ema50

    if ma_choice == "20 EMA":
        return above_20 and near_20

    if ma_choice == "50 EMA":
        return above_50 and near_50

    if ma_choice == "20 EMA or 50 EMA":
        return (
            (above_20 and near_20)
            or
            (above_50 and near_50)
        )

    return False


# ============================================================
# SCAN ONE STOCK
# ============================================================

def scan_stock(
    symbol,
    interval,
    period,
    strategies,
    selected_patterns,
    ma_choice
):

    df = get_stock_data(
        symbol,
        interval,
        period
    )

    if df.empty:
        return None, df

    if len(df) < 30:
        return None, df

    df = add_indicators(df)

    matches = []

    # Strategy 1
    if "Double Bottom + Retest" in strategies:

        if strategy_double_bottom(df):
            matches.append(
                "Double Bottom + Bullish Candle"
            )

    # Strategy 2
    if "Range/Triangle Breakout" in strategies:

        if strategy_range_breakout(df):
            matches.append(
                "Range/Triangle Breakout"
            )

    # Strategy 3
    if "Cup & Handle / Triple Bottom" in strategies:

        if strategy_cup_triple(df):
            matches.append(
                "Cup & Handle / Triple Bottom"
            )

    # Strategy 4
    if "Custom Candlestick + EMA" in strategies:

        if strategy_custom_candle_ma(
            df,
            selected_patterns,
            ma_choice
        ):
            matches.append(
                "Candlestick + EMA"
            )

    if not matches:
        return None, df

    current_price = float(df["Close"].iloc[-1])

    previous_close = float(
        df["Close"].iloc[-2]
    )

    percent_change = (
        (current_price - previous_close)
        / previous_close
    ) * 100

    result = {
        "Symbol": symbol,
        "Current Price": round(current_price, 2),
        "% Change": round(percent_change, 2),
        "Strategy Matched": ", ".join(matches)
    }

    return result, df


# ============================================================
# CHART
# ============================================================

def create_chart(df, symbol, timeframe):

    chart_df = df.tail(150).copy()

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=chart_df.index,
            open=chart_df["Open"],
            high=chart_df["High"],
            low=chart_df["Low"],
            close=chart_df["Close"],
            name="Price"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=chart_df.index,
            y=chart_df["EMA20"],
            mode="lines",
            name="EMA 20"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=chart_df.index,
            y=chart_df["EMA50"],
            mode="lines",
            name="EMA 50"
        )
    )

    fig.update_layout(
        title=f"{symbol} — {timeframe}",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=650,
        hovermode="x unified"
    )

    return fig


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Scanner Settings")

timeframe = st.sidebar.selectbox(
    "Timeframe",
    [
        "5-minute",
        "1-hour",
        "Daily"
    ]
)

selected_timeframe = TIMEFRAME_MAP[timeframe]

st.sidebar.subheader("Strategies")

strategies = st.sidebar.multiselect(
    "Select strategies",
    [
        "Double Bottom + Retest",
        "Range/Triangle Breakout",
        "Cup & Handle / Triple Bottom",
        "Custom Candlestick + EMA"
    ],
    default=[
        "Double Bottom + Retest",
        "Range/Triangle Breakout"
    ]
)


# ============================================================
# CUSTOM STRATEGY SETTINGS
# ============================================================

selected_patterns = []

ma_choice = "20 EMA or 50 EMA"

if "Custom Candlestick + EMA" in strategies:

    st.sidebar.subheader(
        "Custom Candlestick Settings"
    )

    selected_patterns = st.sidebar.multiselect(
        "Candlestick patterns",
        [
            "Hammer",
            "Bullish Engulfing",
            "Piercing Line",
            "Morning Star"
        ],
        default=[
            "Hammer",
            "Bullish Engulfing"
        ]
    )

    ma_choice = st.sidebar.selectbox(
        "Moving Average",
        [
            "20 EMA",
            "50 EMA",
            "20 EMA or 50 EMA"
        ]
    )


# ============================================================
# STOCK UNIVERSE
# ============================================================

st.sidebar.subheader("Stock Universe")

max_stocks = st.sidebar.slider(
    "Number of stocks to scan",
    min_value=10,
    max_value=len(NSE_STOCKS),
    value=min(50, len(NSE_STOCKS)),
    step=10
)

symbols_to_scan = NSE_STOCKS[:max_stocks]


# ============================================================
# SCAN BUTTON
# ============================================================

scan_button = st.sidebar.button(
    "🔍 Run Scanner",
    type="primary",
    use_container_width=True
)


# ============================================================
# MAIN SCANNER
# ============================================================

if scan_button:

    if not strategies:

        st.warning(
            "Please select at least one strategy."
        )

    elif (
        "Custom Candlestick + EMA" in strategies
        and not selected_patterns
    ):

        st.warning(
            "Please select at least one candlestick pattern."
        )

    else:

        results = []
        data_cache = {}

        progress = st.progress(0)

        status = st.empty()

        total = len(symbols_to_scan)

        for i, symbol in enumerate(symbols_to_scan):

            status.text(f"Scanning {symbol} ({i+1}/{total})...")
            
