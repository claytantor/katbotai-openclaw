# katbotai-openclaw

> **Add live crypto trading superpowers to any OpenClaw agent using [Katbot.ai](https://katbot.ai).**

This repository contains everything you need to configure an OpenClaw agent to:
- Monitor the **BTC Momentum Index (BMI)** for directional trade signals
- Automatically select the **best-performing tokens** from Hyperliquid
- Request **AI-powered trade recommendations** from the Katbot agent
- **Execute and manage live trades** on Hyperliquid — all from natural conversation

> ⚠️ **Live trading involves real financial risk. Read the full setup carefully, start with testnet, and never risk more than you can afford to lose.**

---

## What You'll Need

| Requirement | Notes |
|:---|:---|
| [OpenClaw](https://docs.openclaw.ai) | Installed and running |
| [Katbot.ai account](https://katbot.ai) | Whitelisted (pre-alpha) |
| [MetaMask](https://metamask.io) | Connected to Arbitrum network |
| [Hyperliquid account](https://app.hyperliquid.xyz) | Testnet or Mainnet |
| Python 3.11+ + `uv` | For running the trading scripts |

---

## How It Works

```
You (chat) ─→ OpenClaw Agent ─→ https://api.katbot.ai ─→ Hyperliquid
```

Your OpenClaw agent uses the **Katbot API** to get recommendations and execute trades.
The agent never holds your private keys in memory — they live in environment variables
and are only used to sign trade requests.

---

## Repo Structure

```
katbotai-openclaw/
├── README.md                        ← You are here
├── scripts/
│   ├── katbot_client.py             ← API client (SIWE auth, all API ops)
│   ├── katbot_workflow.py           ← Full trading workflow (BMI → trade)
│   └── token_selector.py           ← CoinGecko token selection by momentum
├── workspace/
│   ├── KATBOT_AGENT.md             ← Agent instructions (add to AGENTS.md)
│   └── memory/
│       └── KATBOT_RULES.md         ← Trading rules loaded each session
└── identity-template/
    ├── katbot_config.json           ← Config template (fill in your values)
    └── .env.example                 ← Environment variable template
```

---

## Step-by-Step Setup

### 1. Install Python Dependencies

```bash
pip install requests eth-account
# or with uv:
uv add requests eth-account
```

### 2. Set Up Your Identity

Create an identity folder for your agent:

```bash
mkdir -p ~/.openclaw/workspace/katbot-identity
cp identity-template/katbot_config.json ~/.openclaw/workspace/katbot-identity/
cp scripts/katbot_client.py ~/.openclaw/workspace/katbot-identity/
```

Edit `katbot_config.json` with your wallet address and portfolio details:

```json
{
  "base_url": "https://api.katbot.ai",
  "wallet_address": "0xYourMetaMaskWalletAddress",
  "portfolio_id": 5,
  "portfolio_name": "my-hl-mainnet",
  "chain_id": 42161
}
```

Set your credentials as environment variables (**never put private keys in files**):

```bash
export WALLET_PRIVATE_KEY=0xYourWalletPrivateKey
export KATBOT_HL_AGENT_PRIVATE_KEY=0xYourAgentPrivateKey
```

Add these to your shell profile (`~/.bashrc` or `~/.zshrc`) to persist them.

### 3. Authenticate with Katbot

The `katbot_client.py` handles SIWE (Sign-In with Ethereum) authentication automatically.
Test it:

```bash
python3 scripts/katbot_client.py
# Should print: ✅ Authenticated as 0xYour...
# Then list your portfolios and show portfolio state
```

### 4. Create a Katbot Portfolio

If you don't have a portfolio yet, create one via the API:

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from katbot_client import get_token, _auth
import requests, os

token = get_token()
r = requests.post('https://api.katbot.ai/portfolio', json={
    'name': 'my-hl-mainnet',
    'description': 'OpenClaw agent-managed portfolio',
    'initial_balance': 1000.0,
    'portfolio_type': 'HYPERLIQUID',
    'is_testnet': False,
    'tokens_selected': ['BTC', 'ETH', 'SOL']
}, headers=_auth(token))
data = r.json()
print(f'Portfolio ID:    {data[\"id\"]}')
print(f'Agent Address:   {data[\"agent_address\"]}')
print(f'Agent Priv Key:  {data[\"agent_private_key\"]}')
print('Save the Agent Private Key as KATBOT_HL_AGENT_PRIVATE_KEY!')
"
```

> ⚠️ The `agent_private_key` is shown **once**. Save it immediately as your `KATBOT_HL_AGENT_PRIVATE_KEY` environment variable.

### 5. Authorize the Agent on Hyperliquid

1. Copy the `agent_address` from the portfolio creation response
2. Go to **[app.hyperliquid.xyz](https://app.hyperliquid.xyz)** → Settings → API
3. Add agent address as an **API Wallet** with trading permissions
4. Set expiry to **180 days**
5. Confirm the MetaMask transaction

See [Katbot Hyperliquid Guide](https://docs.katbot.ai/guides/hyperliquid) for screenshots.

### 6. Test the Full Workflow

```bash
KATBOT_HL_AGENT_PRIVATE_KEY=0x... \
python3 scripts/katbot_workflow.py \
  --portfolio-id 5 \
  --bmi-threshold 15 \
  --top 5
```

This will:
1. Check the BMI — if neutral, it exits cleanly with no trade
2. Select top/worst 5 tokens based on the market direction
3. Update your portfolio token list
4. Request a recommendation from the Katbot AI agent
5. Present the recommendation with entry, TP, SL, R/R, leverage
6. Ask you to confirm before executing

### 7. Add to Your OpenClaw Agent

Copy the agent instructions into your workspace:

```bash
# Add trading rules to your agent's memory
cp workspace/memory/KATBOT_RULES.md ~/.openclaw/workspace/memory/

# Add agent instructions — merge into your existing AGENTS.md
cat workspace/KATBOT_AGENT.md >> ~/.openclaw/workspace/AGENTS.md
```

Then update your `MEMORY.md` to tell the agent where everything lives:

```markdown
## Katbot Trading Setup
- API: https://api.katbot.ai
- Identity: ~/.openclaw/workspace/katbot-identity/
- Client: katbot_client.py
- Portfolio ID: 5 (my-hl-mainnet)
- Rules: memory/KATBOT_RULES.md (read every session)
```

---

## Using Your Agent

Once set up, just talk to your OpenClaw agent naturally:

```
"How's the market looking?"
→ Agent checks BMI and reports BTC momentum + top movers

"Run the trading workflow"
→ Agent checks BMI, selects tokens, gets recommendation, asks to confirm

"How's the portfolio doing?"
→ Agent queries API and reports positions + uPnL

"Set the portfolio tokens to NEAR, AAVE, SUI, ARB"
→ Agent updates tokens via API

"Get a recommendation for a short"
→ Agent requests recommendation with bearish bias

"Close the position"
→ Agent closes via API after confirmation
```

---

## The Workflow in Detail

### BMI — When to Trade

The BTC Momentum Index (BMI) tells us whether the market is trending strongly enough to trade.

| BMI | Signal | Action |
|:---|:---|:---|
| ≥ +15 | BULLISH | Select top gainers → get LONG recommendation |
| ≤ -15 | BEARISH | Select worst performers → get SHORT recommendation |
| -15 to +15 | NEUTRAL | Stay flat. No trade. |

The workflow exits cleanly if BMI is neutral — protecting you from low-conviction trades.

### Token Selection Strategy

**Bullish market** → Pick the top 5 CoinGecko 24h gainers that are traded on Hyperliquid.
These are the momentum leaders most likely to continue higher.

**Bearish market** → Pick the 5 worst 24h performers on Hyperliquid.
These are the weakest tokens most likely to continue lower.

Use `scripts/token_selector.py` to run this independently:

```bash
python3 scripts/token_selector.py --top 5 --direction bullish
python3 scripts/token_selector.py --top 5 --direction bearish
```

### Leverage Guidelines

The Katbot agent recommends leverage based on market conditions. General guidelines:

| Condition | Leverage |
|:---|:---|
| RSI < 20 or > 80 (extreme) | 1x only — high reversal risk |
| Clear trend, BMI ±15–30 | 1–2x |
| Strong momentum, BMI ±30+ | 2–5x |
| Textbook breakout, high volume | Up to 5x |

> At 5x leverage, a 5% stop loss = 25% of your margin at risk. Always honor your stops.

---

## Agent Prompt Templates

Use these prompts to prime a new agent session or include in your `AGENTS.md`:

### Initial Setup Prompt

```
You are a live trading assistant connected to Katbot.ai via the API at https://api.katbot.ai.
You use the BTC Momentum Index (BMI) to determine market direction, select the best tokens
from Hyperliquid, request AI trade recommendations, and execute trades — but only with
explicit user confirmation.

Your operating rules are in memory/KATBOT_RULES.md. Read them before every trading session.
Your identity and API client are in ~/.openclaw/workspace/katbot-identity/.

Never bypass the API. Never execute a trade without user confirmation.
Always report portfolio state using the API, not the exchange directly.
```

### Session Start Prompt

```
Read memory/KATBOT_RULES.md. Then check the current portfolio state and BMI.
Report: current positions with uPnL, cash balance, and market signal.
If BMI is outside the neutral range (|BMI| >= 15), flag it and ask if the user wants to run the workflow.
```

### Market Check Prompt

```
Check the current BMI and top movers. Report:
1. BMI value and signal
2. BTC 24h performance
3. Top 5 gainers and worst 5 performers among Hyperliquid tokens
4. Whether we should be looking at longs, shorts, or staying flat
```

---

## API Reference

Full Swagger docs: **[https://api.katbot.ai/docs](https://api.katbot.ai/docs)**

| Operation | Method | Endpoint |
|:---|:---|:---|
| Get nonce | GET | `/get-nonce/{address}?chain_id=42161` |
| Login | POST | `/login` |
| Verify auth | GET | `/me` |
| List portfolios | GET | `/portfolio` |
| Create portfolio | POST | `/portfolio` |
| Portfolio state | GET | `/portfolio/{id}` |
| Update tokens | PUT | `/portfolio/{id}` |
| Request recommendation | POST | `/agent/recommendation/message` |
| Poll recommendation | GET | `/agent/recommendation/poll/{ticket_id}` |
| Get recommendation | GET | `/portfolio/{id}/recommendation` |
| Execute trade | POST | `/portfolio/{id}/execute` |
| Close position | POST | `/portfolio/{id}/close-position` |

---

## Troubleshooting

**401 Unauthorized** — JWT expired. `katbot_client.py` will auto-refresh. If it fails, delete `katbot_token.json` and re-run.

**403 / Agent key rejected** — Verify `KATBOT_HL_AGENT_PRIVATE_KEY` matches the agent address added to Hyperliquid.

**Recommendation FAILED** — Check your Katbot subscription includes AI recommendations. Contact support on Discord.

**Trade won't fill** — On testnet, some pairs have thin orderbooks. Try mainnet or switch to BTC/ETH.

**BMI always neutral** — BMI is based on BTC 4h momentum. In choppy, sideways markets this is expected and correct — it's protecting you from bad trades.

---

## Contributing

Found a bug? Have an improvement? PRs welcome.

This repo is the living configuration for an agent that trades real money.
Every improvement helps real users make better decisions.

---

## Resources

- [Katbot.ai](https://katbot.ai)
- [Katbot API Docs](https://api.katbot.ai/docs)
- [OpenClaw Docs](https://docs.openclaw.ai)
- [Hyperliquid](https://app.hyperliquid.xyz)
- [Katbot Discord](https://discord.gg/ZP73Y8zn)
- [OpenClaw Discord](https://discord.com/invite/clawd)

---

> Built by [Tubman Clawbot](https://github.com/tubmanclaw) 😼 — the OpenClaw agent that trades its own portfolio.
