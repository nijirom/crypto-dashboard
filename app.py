import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from streamlit_autorefresh import st_autorefresh

# Page Configuration
st.set_page_config(page_title="Live Crypto Breakout Dashboard", layout="wide")

# Auto-refresh every 30 seconds (30000 ms)
st_autorefresh(interval=30_000, limit=None, key="live_refresh")

# Dense, terminal-style CSS
st.markdown("""
<style>
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }
    div[data-testid="column"] {
        width: 100% !important;
        flex: 1 1 auto;
        min-width: 0px;
    }
    header[data-testid="stHeader"] {
        background-color: rgba(255,255,255,0);
    }
    h1 {
        font-size: 1.6rem !important;
        padding-bottom: 0 !important;
    }
    div[data-testid="stPlotlyChart"] {
        margin-bottom: -1rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("Breakout Dashboard")


# Data Fetching
@st.cache_data(ttl=300)  # Cache for 5 minutes to respect API rate limits
def fetch_coingecko_data() -> pd.DataFrame:
    """
    Fetch the top 100 cryptocurrencies from CoinGecko and calculate
    technical-analysis proxy metrics for the dashboard.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or len(data) == 0:
            st.error("⚠ CoinGecko returned unexpected data. Please try again later.")
            st.stop()

        df = pd.DataFrame(data)

        # Map columns
        df["Ticker"] = df["symbol"].str.upper()
        df["Price Change 1D%"] = pd.to_numeric(
            df["price_change_percentage_24h_in_currency"], errors="coerce"
        ).fillna(0)
        df["Price Change 1W%"] = pd.to_numeric(
            df["price_change_percentage_7d_in_currency"], errors="coerce"
        ).fillna(0)
        df["Volume"] = pd.to_numeric(df["total_volume"], errors="coerce").fillna(0)

        # Z-Scores
        def zscore(series: pd.Series) -> pd.Series:
            std = series.std()
            if std == 0:
                return series * 0.0
            return (series - series.mean()) / std

        df["Price Z-Score 1D"] = zscore(df["Price Change 1D%"])
        df["OI Z-Score 1D"] = zscore(df["Volume"])  # Volume as OI proxy

        # Relative Strength (momentum blend)
        df["Relative Strength"] = (
            df["Price Change 1D%"] * 0.4 + df["Price Change 1W%"] * 0.6
        )
        df["Relative Strength Z-Score 1D"] = zscore(df["Relative Strength"])

        # Forecast proxies
        df["Volatility Breakout"] = df["Price Change 1D%"].abs()
        df["Composite Forecast"] = (df["OI Z-Score 1D"] + df["Price Z-Score 1D"]) / 2
        df["HTF-Breakout Forecast"] = df["Price Change 1W%"]

        # Signal flag for scatter coloring
        df["Signal"] = np.where(df["Composite Forecast"] > 1.0, "High", "Normal")

        return df

    except Exception as exc:
        st.error(f"⚠ API error: {exc}. Please try again later.")
        st.stop()


df = fetch_coingecko_data()


# Chart Builder: Scatter
def create_scatter(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
) -> px.scatter:
    fig = px.scatter(
        data,
        x=x_col,
        y=y_col,
        hover_name="Ticker",
        title=title,
        color="Signal",
        color_discrete_map={"High": "#FFA500", "Normal": "#5DADE2"},
        template="plotly_white",
    )
    # Quadrant reference lines
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="lightgray")
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="lightgray")

    fig.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
        height=300,
        font=dict(size=10),
        title_font=dict(size=13, family="Arial", color="#333"),
    )
    fig.update_traces(marker=dict(size=7, opacity=0.85))
    return fig


# Chart Builder: Horizontal Bar
def create_bar(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    bar_color: str = "#5DADE2",
) -> px.bar:
    df_sorted = data.sort_values(by=x_col, ascending=True).tail(30)
    fig = px.bar(
        df_sorted,
        x=x_col,
        y=y_col,
        orientation="h",
        title=title,
        color_discrete_sequence=[bar_color],
        template="plotly_white",
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        height=520,
        yaxis=dict(title=None, tickfont=dict(size=9)),
        xaxis=dict(title=None),
        title_font=dict(size=13, family="Arial", color="#333"),
    )
    return fig


# Dashboard Layout
# Refresh button (clears the 5-min cache immediately)
st.button("Refresh Data Now", on_click=st.cache_data.clear)

# ROW 1 Market Overview Scatter Plots
r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    st.plotly_chart(
        create_scatter(df, "Price Change 1W%", "Price Change 1D%", "Price Change"),
        use_container_width=True,
    )
with r1c2:
    st.plotly_chart(
        create_scatter(df, "OI Z-Score 1D", "Price Z-Score 1D", "Vol / OI Z-Score"),
        use_container_width=True,
    )
with r1c3:
    st.plotly_chart(
        create_scatter(
            df, "Relative Strength Z-Score 1D", "Price Z-Score 1D", "Relative Strength"
        ),
        use_container_width=True,
    )

# ROW 2 — Breakout Forecast Scatter Plots
r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    st.plotly_chart(
        create_scatter(df, "Composite Forecast", "Price Z-Score 1D", "Composite Breakout"),
        use_container_width=True,
    )
with r2c2:
    st.plotly_chart(
        create_scatter(
            df, "Volatility Breakout", "Price Z-Score 1D", "Volatility Breakout"
        ),
        use_container_width=True,
    )
with r2c3:
    st.plotly_chart(
        create_scatter(
            df, "HTF-Breakout Forecast", "Price Z-Score 1D", "HTF Breakout"
        ),
        use_container_width=True,
    )

# ROW 3 Ranking Bar Charts
r3c1, r3c2, r3c3, r3c4 = st.columns(4)
with r3c1:
    st.plotly_chart(
        create_bar(df, "Composite Forecast", "Ticker", "Composite Score"),
        use_container_width=True,
    )
with r3c2:
    st.plotly_chart(
        create_bar(df, "Volatility Breakout", "Ticker", "Volatility Score"),
        use_container_width=True,
    )
with r3c3:
    st.plotly_chart(
        create_bar(df, "HTF-Breakout Forecast", "Ticker", "HTF Score"),
        use_container_width=True,
    )
with r3c4:
    st.plotly_chart(
        create_bar(
            df, "Relative Strength", "Ticker", "Relative Strength", bar_color="#EF8E5B"
        ),
        use_container_width=True,
    )

# Footer
st.caption("Data auto-refreshes every 30 seconds · Source: CoinGecko Public API")
