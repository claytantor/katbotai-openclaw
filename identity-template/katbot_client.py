"""
tubman_client.py — Katbot API client for Tubman agent.

Handles auth (SIWE), token refresh, and all key API operations:
- Portfolio management
- Recommendations
- Trade execution
- Agent chat
"""

import json
import os
import time
import requests
from eth_account import Account
from eth_account.messages import encode_defunct

BASE_URL = "https://api.katbot.ai"
IDENTITY_FILE = os.path.join(os.path.dirname(__file__), "tubman_wallet.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "tubman_token.json")


# ─────────────────────────────────────────────
# Identity + Auth
# ─────────────────────────────────────────────

def load_identity():
    with open(IDENTITY_FILE) as f:
        data = json.load(f)
    return data["address"], data["private_key"]


def authenticate() -> str:
    """Perform SIWE login and return a fresh JWT. Saves token to disk."""
    address, private_key = load_identity()

    # Step 1: Get nonce / message to sign
    r = requests.get(f"{BASE_URL}/get-nonce/{address}?chain_id=42161")
    r.raise_for_status()
    message_text = r.json()["message"]

    # Step 2: Sign
    signable = encode_defunct(text=message_text)
    signed = Account.sign_message(signable, private_key)
    signature = signed.signature.hex()

    # Step 3: Login
    r = requests.post(f"{BASE_URL}/login", json={"address": address, "signature": signature, "chain_id": 42161})
    r.raise_for_status()
    token_data = r.json()

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"✅ Authenticated as {address}")
    return token_data["access_token"]


def get_token() -> str:
    """Return cached token or re-authenticate if missing/expired."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            data = json.load(f)
        token = data.get("access_token", "")
        if token:
            # Quick validity check — try /me
            r = requests.get(f"{BASE_URL}/me", headers=_auth(token))
            if r.status_code == 200:
                return token
    return authenticate()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────
# Portfolio
# ─────────────────────────────────────────────

def list_portfolios(token: str) -> list:
    r = requests.get(f"{BASE_URL}/portfolio", headers=_auth(token))
    r.raise_for_status()
    return r.json()


def create_portfolio(token: str, name: str, description: str = "", initial_balance: float = 10000.0) -> dict:
    payload = {
        "name": name,
        "description": description,
        "initial_balance": initial_balance,
    }
    r = requests.post(f"{BASE_URL}/portfolio", json=payload, headers=_auth(token))
    r.raise_for_status()
    return r.json()


def get_portfolio(token: str, portfolio_id: str, window: str = "1d") -> dict:
    r = requests.get(f"{BASE_URL}/portfolio/{portfolio_id}", params={"window": window}, headers=_auth(token))
    r.raise_for_status()
    return r.json()


def delete_portfolio(token: str, portfolio_id: str) -> dict:
    r = requests.delete(f"{BASE_URL}/portfolio/{portfolio_id}", headers=_auth(token))
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────

def get_recommendations(token: str, portfolio_id: str) -> list:
    r = requests.get(f"{BASE_URL}/portfolio/{portfolio_id}/recommendation", headers=_auth(token))
    r.raise_for_status()
    return r.json()


def request_recommendation(token: str, portfolio_id: str, message: str) -> dict:
    """Submit a recommendation request to the agent (async, returns ticket)."""
    payload = {"portfolio_id": portfolio_id, "message": message}
    r = requests.post(f"{BASE_URL}/agent/recommendation/message", json=payload, headers=_auth(token))
    r.raise_for_status()
    return r.json()


def poll_recommendation(token: str, ticket_id: str, max_wait: int = 60) -> dict:
    """Poll until recommendation is ready or timeout."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/agent/recommendation/poll/{ticket_id}", headers=_auth(token))
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "complete":
            return data
        time.sleep(2)
    raise TimeoutError(f"Recommendation not ready after {max_wait}s")


# ─────────────────────────────────────────────
# Trading
# ─────────────────────────────────────────────

def execute_trade(token: str, portfolio_id: str, symbol: str, side: str, size_usd: float, leverage: float = 1.0) -> dict:
    """Execute a market trade. side: 'long' or 'short'."""
    payload = {
        "symbol": symbol,
        "side": side,
        "position_size_usd": size_usd,
        "leverage": leverage,
    }
    r = requests.post(f"{BASE_URL}/portfolio/{portfolio_id}/trade", json=payload, headers=_auth(token))
    r.raise_for_status()
    return r.json()


def execute_recommendation(token: str, portfolio_id: str, rec_id: str) -> dict:
    """Execute an existing recommendation by ID."""
    r = requests.post(f"{BASE_URL}/portfolio/{portfolio_id}/execute",
                      json={"recommendation_id": rec_id}, headers=_auth(token))
    r.raise_for_status()
    return r.json()


def close_position(token: str, portfolio_id: str, symbol: str) -> dict:
    r = requests.post(f"{BASE_URL}/portfolio/{portfolio_id}/close-position",
                      json={"symbol": symbol}, headers=_auth(token))
    r.raise_for_status()
    return r.json()


def list_trades(token: str, portfolio_id: str) -> list:
    r = requests.get(f"{BASE_URL}/portfolio/{portfolio_id}/trade", headers=_auth(token))
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────
# Agent Chat
# ─────────────────────────────────────────────

def chat(token: str, portfolio_id: str, message: str) -> dict:
    """Send a chat message to the portfolio agent (async, returns ticket)."""
    payload = {"portfolio_id": portfolio_id, "message": message}
    r = requests.post(f"{BASE_URL}/agent/chat/message", json=payload, headers=_auth(token))
    r.raise_for_status()
    return r.json()


def poll_chat(token: str, ticket_id: str, max_wait: int = 60) -> dict:
    """Poll until chat response is ready."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/agent/chat/poll/{ticket_id}", headers=_auth(token))
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "complete":
            return data
        time.sleep(2)
    raise TimeoutError(f"Chat response not ready after {max_wait}s")


# ─────────────────────────────────────────────
# Quick smoke test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Tubman Client Smoke Test ===")
    token = get_token()

    print("\n[1] Listing portfolios...")
    portfolios = list_portfolios(token)
    print(f"    Found {len(portfolios)} portfolio(s)")

    if not portfolios:
        print("\n[2] Creating first portfolio...")
        p = create_portfolio(token, name="Tubman-Alpha", description="Agent-managed paper trading portfolio", initial_balance=10000.0)
        print(f"    Created: {p}")
        portfolio_id = p["id"]
    else:
        portfolio_id = portfolios[0]["id"]
        print(f"    Using existing portfolio: {portfolio_id}")

    print(f"\n[3] Getting portfolio state for {portfolio_id}...")
    state = get_portfolio(token, portfolio_id)
    print(f"    Cash: ${state.get('cash_balance_usd', 'N/A')}")
    print(f"    Total Value: ${state.get('total_value_usd', 'N/A')}")
    print(f"    Open Positions: {len(state.get('open_positions', []))}")

    print("\n✅ Smoke test complete. Tubman is operational.")
