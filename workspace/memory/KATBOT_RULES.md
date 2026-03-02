# KATBOT_RULES.md — Trading Agent Rules

These rules govern how this OpenClaw agent interacts with the Katbot.ai API.
Load this file every session alongside MEMORY.md.

---

## 🔑 Core Rule: Always Use the Katbot API

**ALWAYS** use the Katbot API at `https://api.katbot.ai` for ALL portfolio operations:
- Portfolio state → `GET /portfolio/{id}`
- Token updates → `PUT /portfolio/{id}`
- Recommendations → `POST /agent/recommendation/message` → poll → `GET /portfolio/{id}/recommendation`
- Execute trades → `POST /portfolio/{id}/execute`
- Close positions → `POST /portfolio/{id}/close-position`

**Never bypass the API** to call the exchange directly. Using the API is how we find bugs,
gaps, and missing features to improve the platform.

If you are tempted to bypass the API, **call it out explicitly** and explain why.

---

## 🔐 Auth

- Auth uses Sign-In with Ethereum (SIWE) — no username/password
- `katbot_client.py` handles SIWE login, token caching, and refresh automatically
- Hyperliquid portfolio operations also require: `X-Agent-Private-Key` header
- Store credentials in environment variables — NEVER in code:
  - `WALLET_PRIVATE_KEY` — your MetaMask wallet private key
  - `KATBOT_HL_AGENT_PRIVATE_KEY` — the agent key from your HL portfolio

---

## 📊 BMI (BTC Momentum Index)

The BMI determines whether to trade and in which direction.

| BMI Value | Signal | Action |
|:---|:---|:---|
| ≥ +15 | BULLISH | Look for LONG opportunities |
| ≤ -15 | BEARISH | Look for SHORT opportunities |
| -15 to +15 | NEUTRAL | Stay flat, no new trades |

Run `scripts/katbot_workflow.py` to get the full BMI → token → recommend → execute pipeline.

---

## 🎯 Token Selection

- **Bullish market**: select top 5 24h gainers on CoinGecko (long candidates)
- **Bearish market**: select worst 5 24h performers on CoinGecko (short candidates)
- Only use tokens traded on Hyperliquid (see `scripts/token_selector.py` for the full list)
- Update portfolio tokens via API before requesting a recommendation

---

## 💬 Reporting to User

When reporting portfolio state always include:
- Total value, cash balance, realized PnL
- Each open position: symbol, side, size, entry price, unrealized PnL
- Current BMI and market signal

When presenting a recommendation always include:
- Symbol, side (LONG/SHORT), entry, TP%, SL%, R/R ratio
- Position size, leverage, confidence
- TradingView link: `https://www.tradingview.com/chart/?symbol=KRAKEN%3A{PAIR}USD`
  - Exception: BTC uses `XBTUSD` not `BTCUSD`

Always ask for user confirmation before executing any trade.

---

## ⚠️ Risk Reminders

- At 1x leverage: treat stop loss as a hard rule
- At 3-5x leverage: remind user that SL% loss is amplified by leverage multiplier
- RSI < 20 or > 80: flag elevated bounce/reversal risk
- Never execute a trade without user confirmation
