# KATBOTAI_AGENT_INSTRUCTIONS.md

> **Add this file's contents to your OpenClaw agent's `AGENTS.md`.**
> It teaches your agent everything it needs to use the Katbot.ai API
> to make live trades on Hyperliquid via natural conversation.

---

## What You Can Do With Katbot.ai

You have access to the **Katbot.ai API** at `https://api.katbot.ai`.
Full API reference: **https://api.katbot.ai/docs**

Through this API you can:
- Manage crypto trading portfolios (paper and live Hyperliquid)
- Get AI-powered trade recommendations from the Katbot agent
- Execute and close live trades on Hyperliquid
- Monitor portfolio state, positions, and P&L
- Have a free-form conversation with the trading AI agent

---

## Authentication — How It Works

Katbot uses **Sign-In with Ethereum (SIWE)**. Your MetaMask wallet IS your login.
The `katbot_client.py` script handles this for you automatically.

**Location:** `~/.openclaw/workspace/katbot-identity/katbot_client.py`

It will:
1. Read your wallet address from `katbot_config.json`
2. Read your private key from `$WALLET_PRIVATE_KEY` env var
3. Get a sign-in nonce from the API
4. Sign it with your wallet
5. Exchange the signature for a JWT access token
6. Cache the token in `katbot_token.json` and refresh when needed

**Required environment variables (never put in files):**
```bash
export WALLET_PRIVATE_KEY=0xYourMetaMaskPrivateKey
export KATBOT_HL_AGENT_PRIVATE_KEY=0xYourHyperliquidAgentKey
```

**Test auth:**
```bash
python3 ~/.openclaw/workspace/katbot-identity/katbot_client.py
# Should print: ✅ Authenticated as 0xYour...
```

---

## Using katbot_client.py

Import and use in any Python script:

```python
import sys
sys.path.insert(0, '~/.openclaw/workspace/katbot-identity')
from katbot_client import get_token, _auth

token = get_token()           # auto-authenticates, uses cache
headers = _auth(token)        # returns {"Authorization": "Bearer <token>"}

# For Hyperliquid portfolios, also add agent key:
import os
agent_key = os.getenv('KATBOT_HL_AGENT_PRIVATE_KEY')
hl_headers = {**_auth(token), 'X-Agent-Private-Key': agent_key}
```

**Available helper functions in `katbot_client.py`:**

| Function | What It Does |
|:---|:---|
| `get_token()` | Returns valid JWT (authenticates if needed) |
| `_auth(token)` | Returns auth header dict |
| `authenticate()` | Force fresh SIWE login, saves token |
| `list_portfolios(token)` | List all your portfolios |
| `create_portfolio(token, name, description, initial_balance)` | Create portfolio |
| `get_portfolio(token, portfolio_id, window)` | Get portfolio state |
| `delete_portfolio(token, portfolio_id)` | Delete a portfolio |
| `get_recommendations(token, portfolio_id)` | List saved recommendations |
| `request_recommendation(token, portfolio_id, message)` | Submit recommendation request (async) |
| `poll_recommendation(token, ticket_id, max_wait)` | Poll until recommendation ready |
| `execute_recommendation(token, portfolio_id, rec_id)` | Execute saved recommendation |
| `execute_trade(token, portfolio_id, symbol, side, size_usd, leverage)` | Direct trade |
| `close_position(token, portfolio_id, symbol)` | Close open position |
| `list_trades(token, portfolio_id)` | List trade history |
| `chat(token, portfolio_id, message)` | Chat with trading agent (async) |
| `poll_chat(token, ticket_id, max_wait)` | Poll until chat response ready |

---

## Full API Reference

Base URL: `https://api.katbot.ai`
Interactive docs: `https://api.katbot.ai/docs`

### Auth Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| GET | `/get-nonce/{address}?chain_id=42161` | Get SIWE nonce for signing |
| POST | `/login` | Login with signed message → returns JWT |
| POST | `/refresh` | Exchange refresh token for new access token |
| GET | `/me` | Verify current auth, returns user info |
| GET | `/user` | Get detailed user profile |

### Portfolio Endpoints

All require: `Authorization: Bearer <token>` header.
Hyperliquid portfolios also require: `X-Agent-Private-Key: <key>` header.

| Method | Endpoint | Description |
|:---|:---|:---|
| GET | `/portfolio` | List all your portfolios |
| POST | `/portfolio` | Create a new portfolio |
| GET | `/portfolio/{id}` | Get portfolio state (positions, P&L, value) |
| PUT | `/portfolio/{id}` | Update portfolio settings (name, tokens, etc.) |
| DELETE | `/portfolio/{id}` | Delete a portfolio |
| GET | `/portfolio/{id}/tokens` | List available trading tokens |
| GET | `/portfolio/{id}/chain-info` | Get chain/exchange info for portfolio |

**GET /portfolio/{id} parameters:**
- `window` (required): time window — `"1d"`, `"7d"`, `"30d"`
- `user_master_address`: your wallet address (for HL portfolios)
- `granularity`: data granularity — `"15m"`, `"1h"`, `"4h"`, `"24h"`
- `X-Agent-Private-Key` (header): required for Hyperliquid portfolios

**GET /portfolio/{id} response includes:**
```json
{
  "total_value_usd": 1024.50,
  "cash_balance_usd": 771.50,
  "realized_pnl_usd": 4.82,
  "open_positions": [
    {
      "symbol": "BTC",
      "side": "long",
      "size": 0.004,
      "entry_price": 65000.0,
      "unrealized_pnl": 12.50
    }
  ]
}
```

**PUT /portfolio/{id} body:**
```json
{
  "name": "new-name",
  "tokens_selected": ["BTC", "ETH", "SOL", "NEAR"],
  "max_history_messages": 50
}
```

**POST /portfolio body:**
```json
{
  "name": "my-hl-mainnet",
  "description": "Live trading portfolio",
  "initial_balance": 1000.0,
  "portfolio_type": "HYPERLIQUID",
  "is_testnet": false,
  "tokens_selected": ["BTC", "ETH", "SOL"]
}
```

### Recommendation Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| POST | `/agent/recommendation/message` | Submit recommendation request (async) |
| GET | `/agent/recommendation/poll/{ticket_id}` | Poll for result |
| GET | `/portfolio/{id}/recommendation` | List saved recommendations |
| PUT | `/portfolio/{id}/recommendation/{rec_id}` | Update a recommendation |
| DELETE | `/portfolio/{id}/recommendation` | Delete recommendation(s) |

**POST /agent/recommendation/message body:**
```json
{
  "portfolio_id": 5,
  "message": "What is your highest conviction trade right now?"
}
```

**Poll response when complete:**
```json
{
  "status": "COMPLETED",
  "response": {
    "response": "## LONG BTC/USD\n\nEntry: $65,000..."
  }
}
```

**GET /portfolio/{id}/recommendation response (each item):**
```json
{
  "id": 22,
  "action": "BUY",
  "pair": "NEAR/USD",
  "entry_price": "1.3163",
  "take_profit_pct": "15.0",
  "stop_loss_pct": "5.0",
  "recommended_position_size_usd": "319.50",
  "leverage_amount": "5.0",
  "confidence": "0.82",
  "created_at": "2026-03-02T15:13:00Z"
}
```

### Trade Execution Endpoints

| Method | Endpoint | Description | Requires Agent Key |
|:---|:---|:---|:---|
| POST | `/portfolio/{id}/execute` | Execute a saved recommendation | ✅ |
| POST | `/portfolio/{id}/close-position` | Close an open position | ✅ |

**POST /portfolio/{id}/execute body:**
```json
{ "recommendation_id": 22 }
```

**POST /portfolio/{id}/close-position body:**
```json
{ "symbol": "NEAR" }
```

### Agent Chat Endpoints

For free-form conversation with the Katbot trading AI (no structured recommendation):

| Method | Endpoint | Description |
|:---|:---|:---|
| POST | `/agent/chat/message` | Send chat message (async) |
| GET | `/agent/chat/poll/{ticket_id}` | Poll for chat response |
| GET | `/portfolio/{id}/conversation` | Get conversation history |
| DELETE | `/portfolio/{id}/conversation` | Clear conversation history |

**POST /agent/chat/message body:**
```json
{
  "portfolio_id": 5,
  "message": "What do you think about BTC right now?"
}
```

### Debug / Diagnostics

| Method | Endpoint | Description |
|:---|:---|:---|
| GET | `/health` | API health check |
| GET | `/portfolio/{id}/agent-approval-status/{agent_address}` | Check if agent is approved on HL |
| POST | `/portfolio/validate-hyperliquid` | Validate HL connection |
| GET | `/plans` | List available subscription plans |

---

## The Standard Trading Workflow

When your user asks about trading, follow this systematic process:

```
1. CHECK BMI
   → Use scripts/katbot_workflow.py or btc_momentum.py
   → BMI ≥ +15: BULLISH — look for LONGs
   → BMI ≤ -15: BEARISH — look for SHORTs
   → |BMI| < 15: NEUTRAL — stay flat, tell user

2. SELECT TOKENS
   → Bullish: top 5 CoinGecko 24h gainers traded on Hyperliquid
   → Bearish: worst 5 CoinGecko 24h performers on Hyperliquid
   → Update via PUT /portfolio/{id} {"tokens_selected": [...]}

3. REQUEST RECOMMENDATION
   → POST /agent/recommendation/message with market context
   → Poll GET /agent/recommendation/poll/{ticket_id} every 5s
   → Retrieve structured data from GET /portfolio/{id}/recommendation

4. PRESENT TO USER
   → Symbol, side (LONG/SHORT), entry, TP%, SL%, R/R, size, leverage, confidence
   → TradingView link: https://www.tradingview.com/chart/?symbol=KRAKEN%3A{SYMBOL}USD
   → BTC exception: use XBTUSD not BTCUSD
   → ALWAYS ask for confirmation before executing

5. EXECUTE (only with user approval)
   → POST /portfolio/{id}/execute {"recommendation_id": N}
   → Confirm via GET /portfolio/{id}

6. MONITOR
   → Report state on request via GET /portfolio/{id}
   → Close via POST /portfolio/{id}/close-position on user request
```

---

## How to Run the Full Workflow Script

```bash
# Full automated workflow: BMI check → token select → recommend → confirm → execute
KATBOT_HL_AGENT_PRIVATE_KEY=0x... python3 scripts/katbot_workflow.py \
  --portfolio-id 5 \
  --bmi-threshold 15 \
  --top 5

# Just check tokens (no trade)
python3 scripts/token_selector.py --top 5 --direction bullish
python3 scripts/token_selector.py --top 5 --direction bearish
```

---

## How to Respond to Common User Requests

**"How's the portfolio doing?"**
→ Call `GET /portfolio/{id}` with agent key header
→ Report: total value, cash, realized PnL, each open position with uPnL

**"How's the market?"**
→ Check BMI + fetch top movers from CoinGecko
→ Report: BMI value/signal, BTC 24h, top gainers and losers

**"Run the workflow" / "Check for a trade"**
→ Run full workflow: BMI → tokens → recommendation → present → confirm

**"Get a [long/short] recommendation"**
→ Update tokens for the direction (gainers for long, losers for short)
→ POST /agent/recommendation/message with directional bias
→ Present recommendation, ask to confirm

**"Set portfolio tokens to X, Y, Z"**
→ PUT /portfolio/{id} {"tokens_selected": ["X", "Y", "Z"]}

**"Execute" / "Yes" / "Let's go"** (after a recommendation was presented)
→ POST /portfolio/{id}/execute {"recommendation_id": N}
→ Confirm via GET /portfolio/{id}

**"Close the position" / "Get out"**
→ POST /portfolio/{id}/close-position {"symbol": "X"}
→ Report final state via GET /portfolio/{id}

---

## Important Rules

1. **Always use the API** — never call the exchange directly
2. **Always confirm before executing** — never trade without explicit user approval
3. **Always include X-Agent-Private-Key** for Hyperliquid portfolio operations
4. **Report risk clearly** — especially at leverage > 1x (loss % = SL% × leverage)
5. **Token refresh is automatic** — `get_token()` handles it; delete `katbot_token.json` to force re-auth
6. **Recommendations are async** — always poll after submitting, don't assume immediate result

---

## Error Handling

| Error | Cause | Fix |
|:---|:---|:---|
| 401 Unauthorized | JWT expired | `get_token()` auto-refreshes; if failing delete `katbot_token.json` |
| 400 Bad Request | Missing `X-Agent-Private-Key` | Add `KATBOT_HL_AGENT_PRIVATE_KEY` to headers |
| 402 Token limit exceeded | Too many tokens for plan | Reduce `tokens_selected` count or upgrade plan |
| 404 Not Found | Portfolio ID wrong | Check `GET /portfolio` to list your portfolio IDs |
| Recommendation FAILED | Agent error | Check subscription plan, retry with simpler message |
| Trade won't fill | Thin orderbook (testnet) | Switch to mainnet or use BTC/ETH |

---

*Full API docs: https://api.katbot.ai/docs*
*Support: https://discord.gg/ZP73Y8zn*
