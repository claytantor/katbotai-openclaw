"""
katbot_workflow.py — Full Katbot.ai trading workflow.

Steps:
  1. Get BMI (BTC Momentum Index)
  2. Decide if bullish/bearish enough to trade (|BMI| >= threshold)
  3. Get best/worst performing tokens on Hyperliquid
  4. Update portfolio token selection via API
  5. Request recommendation via API
  6. Present recommendation and ask user to confirm execution

Usage:
  KATBOT_HL_AGENT_PRIVATE_KEY=0x... python3 scripts/katbot_workflow.py --portfolio-id 5
"""
import sys, os, time, json, argparse, importlib.util
import requests

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace/katbot-identity"))

BMI_SCRIPT = os.path.expanduser("~/obsidian-vault/tools/btc_momentum.py")
BASE_URL = "https://api.katbot.ai"

COINGECKO_IDS = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
    'ARB': 'arbitrum', 'HYPE': 'hyperliquid', 'AVAX': 'avalanche-2',
    'LINK': 'chainlink', 'OP': 'optimism', 'INJ': 'injective-protocol',
    'SUI': 'sui', 'APT': 'aptos', 'TIA': 'celestia',
    'DOGE': 'dogecoin', 'ADA': 'cardano', 'DOT': 'polkadot',
    'NEAR': 'near', 'FTM': 'fantom', 'ATOM': 'cosmos',
    'LTC': 'litecoin', 'BCH': 'bitcoin-cash', 'UNI': 'uniswap',
    'AAVE': 'aave', 'MKR': 'maker', 'CRV': 'curve-dao-token',
    'WIF': 'dogwifcoin', 'PEPE': 'pepe', 'BONK': 'bonk',
    'XRP': 'ripple', 'MATIC': 'matic-network', 'RUNE': 'thorchain',
    'STX': 'blockstack', 'ALGO': 'algorand', 'TAO': 'bittensor',
    'SEI': 'sei-network', 'IMX': 'immutable-x',
}

def get_bmi():
    spec = importlib.util.spec_from_file_location("btc_momentum", BMI_SCRIPT)
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    return bm.compute_bmi(bm.fetch_candles())

def get_token_performance(top, bearish):
    ids_str = ','.join(COINGECKO_IDS.values())
    r = requests.get(
        f'https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd&include_24hr_change=true',
        timeout=15)
    data = r.json()
    id_to_sym = {v: k for k, v in COINGECKO_IDS.items()}
    results = [
        {'symbol': id_to_sym[cg_id], 'price': vals.get('usd', 0), 'pct_24h': vals.get('usd_24h_change') or 0}
        for cg_id, vals in data.items() if cg_id in id_to_sym
    ]
    return sorted(results, key=lambda x: x['pct_24h'], reverse=not bearish)[:top]

def api_auth():
    from katbot_client import authenticate
    return authenticate()

def auth_headers(token, agent_key=None):
    h = {'Authorization': f'Bearer {token}'}
    if agent_key:
        h['X-Agent-Private-Key'] = agent_key
    return h

def update_portfolio_tokens(token, portfolio_id, symbols, agent_key):
    r = requests.put(f'{BASE_URL}/portfolio/{portfolio_id}',
        json={'tokens_selected': symbols},
        headers=auth_headers(token, agent_key))
    return r.status_code, r.json()

def request_recommendation(token, portfolio_id, message):
    r = requests.post(f'{BASE_URL}/agent/recommendation/message',
        json={'portfolio_id': portfolio_id, 'message': message},
        headers=auth_headers(token))
    return r.json().get('ticket_id')

def poll_recommendation(token, ticket_id, max_wait=240):
    deadline = time.time() + max_wait
    while time.time() < deadline:
        r = requests.get(f'{BASE_URL}/agent/recommendation/poll/{ticket_id}',
            headers=auth_headers(token))
        data = r.json()
        if data.get('status') in ('COMPLETED', 'complete', 'FAILED'):
            return data
        print("   ...", flush=True)
        time.sleep(5)
    return None

def get_latest_recommendation(token, portfolio_id):
    r = requests.get(f'{BASE_URL}/portfolio/{portfolio_id}/recommendation',
        headers=auth_headers(token))
    recs = r.json()
    if not recs:
        return None
    return sorted(recs, key=lambda x: x['created_at'], reverse=True)[0]

def execute_recommendation(token, portfolio_id, rec_id, agent_key):
    r = requests.post(f'{BASE_URL}/portfolio/{portfolio_id}/execute',
        json={'recommendation_id': rec_id},
        headers=auth_headers(token, agent_key))
    return r.json()

def main():
    parser = argparse.ArgumentParser(description='Katbot full trading workflow')
    parser.add_argument('--portfolio-id', type=int, default=5)
    parser.add_argument('--top', type=int, default=5)
    parser.add_argument('--bmi-threshold', type=int, default=15)
    parser.add_argument('--agent-key', type=str,
        default=os.getenv('KATBOT_HL_AGENT_PRIVATE_KEY'))
    args = parser.parse_args()

    if not args.agent_key:
        print("ERROR: Set KATBOT_HL_AGENT_PRIVATE_KEY or pass --agent-key")
        sys.exit(1)

    print("=" * 55)
    print("  😼 KATBOT TRADING WORKFLOW")
    print("=" * 55)

    # ── 1. BMI ──────────────────────────────────────────
    print("\n[1/5] 📡 Getting BTC Momentum Index...")
    bmi_data = get_bmi()
    bmi = bmi_data['bmi']
    signal = bmi_data['signal']
    btc_pct = bmi_data['btc_24h_pct']
    print(f"      BMI: {bmi:+d} ({signal}) | BTC 24h: {btc_pct:+.2f}%")

    # ── 2. Trade decision ────────────────────────────────
    print(f"\n[2/5] 🧠 Trade Decision (threshold ±{args.bmi_threshold})...")
    bullish = bmi >= args.bmi_threshold
    bearish = bmi <= -args.bmi_threshold

    if not bullish and not bearish:
        print(f"      ⛔ BMI {bmi:+d} is neutral. No trade. Re-run when |BMI| >= {args.bmi_threshold}.")
        sys.exit(0)

    direction = "BULLISH 🚀 (LONG bias)" if bullish else "BEARISH 🐻 (SHORT bias)"
    print(f"      ✅ {direction}")

    # ── 3. Token selection ───────────────────────────────
    action_word = "top gainers" if bullish else "worst performers"
    print(f"\n[3/5] 🔍 Fetching {action_word} (top {args.top})...")
    tokens = get_token_performance(args.top, bearish)
    print(f"\n      {'Symbol':<8} {'Price':>10} {'24h %':>8}  Trade")
    print("      " + "-" * 38)
    for t in tokens:
        trade = "▲ LONG" if bullish else "▼ SHORT"
        print(f"      {t['symbol']:<8} ${t['price']:>9,.4f} {t['pct_24h']:>+7.2f}%  {trade}")
    symbols = [t['symbol'] for t in tokens]

    # ── 4. Update portfolio ──────────────────────────────
    print(f"\n[4/5] 📝 Updating portfolio {args.portfolio_id} tokens → {symbols}...")
    token = api_auth()
    status, resp = update_portfolio_tokens(token, args.portfolio_id, symbols, args.agent_key)
    if status in (200, 201):
        print(f"      ✅ Tokens updated")
    else:
        print(f"      ⚠️  {status}: {resp}")

    # ── 5. Recommendation ────────────────────────────────
    print(f"\n[5/5] 🤖 Requesting recommendation...")
    msg = (f"Market is {'bullish' if bullish else 'bearish'}, BMI {bmi:+d}, BTC 24h {btc_pct:+.2f}%. "
           f"Focus on {'long' if bullish else 'short'} setups in the selected tokens. "
           f"What is your highest conviction trade right now?")
    ticket_id = request_recommendation(token, args.portfolio_id, msg)
    print(f"      Ticket: {ticket_id} | Polling", end="", flush=True)
    result = poll_recommendation(token, ticket_id)

    if not result or result.get('status') == 'FAILED':
        print(f"\n      ❌ Failed: {result}")
        sys.exit(1)

    print(f"\n\n{'=' * 55}")
    print("  📊 AGENT RECOMMENDATION")
    print('=' * 55)
    print(result.get('response', {}).get('response', ''))

    rec = get_latest_recommendation(token, args.portfolio_id)
    if not rec:
        print("\n⚠️  No saved recommendation found.")
        sys.exit(0)

    print(f"\n{'=' * 55}")
    print(f"  #{rec['id']} | {rec['action']} {rec['pair']}")
    print(f"  Entry: ${float(rec.get('entry_price',0)):,.4f} | "
          f"TP: {rec.get('take_profit_pct','?')}% | SL: {rec.get('stop_loss_pct','?')}%")
    print(f"  Size:  ${float(rec.get('recommended_position_size_usd',0)):,.2f} | "
          f"Leverage: {rec.get('leverage_amount','?')}x | "
          f"Confidence: {float(rec.get('confidence',0))*100:.0f}%")
    print('=' * 55)

    answer = input("\n🚀 Execute this trade? (yes/no): ").strip().lower()
    if answer in ('yes', 'y'):
        print("Executing via API...")
        exec_result = execute_recommendation(token, args.portfolio_id, rec['id'], args.agent_key)
        if exec_result.get('success'):
            print("✅ Trade executed successfully!")
        else:
            print(f"❌ Failed: {exec_result.get('error')}")
    else:
        print("⏭️  Skipped. Recommendation saved.")

if __name__ == "__main__":
    main()
