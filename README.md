# crypto-dashboard

A real-time dashboard that visualizes breakout signals and technical-analysis proxies for the top 100 cryptocurrencies using CoinGecko data.

## Features

- **Live data** from the CoinGecko public API (auto-refreshes every 30s, cached for 5 min)
- **8 scatter plots** covering price change, volume/OI z-scores, relative strength, funding, composite/volatility/HTF breakout forecasts, and carry
- **4 ranked bar charts** for composite, volatility, HTF, and relative strength scores
- Automatic fallback to mock data when the API is unavailable
