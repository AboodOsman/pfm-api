import os
import httpx
from typing import Any, Dict, List, Optional
from services.mock_wallet_service import build_connected_wallet_payload
from services.cache import mock_wallet_cache
LEAN_AUTH_BASE_URL = os.getenv("LEAN_AUTH_BASE_URL", "https://auth.sandbox.leantech.me")
LEAN_API_BASE_URL = os.getenv("LEAN_API_BASE_URL", "https://sandbox.leantech.me")
LEAN_DATA_BASE_URL= os.getenv("LEAN_DATA_BASE_URL","https://sandbox.leantech.me")
LEAN_CLIENT_ID = os.getenv("LEAN_CLIENT_ID")
LEAN_CLIENT_SECRET = os.getenv("LEAN_CLIENT_SECRET")
LEAN_APP_TOKEN = os.getenv("LEAN_APP_TOKEN")
LEAN_REDIRECT_URL = os.getenv("LEAN_REDIRECT_URL", "http://localhost:5173/lean-callback")


class LeanError(Exception):
    pass


async def get_access_token() -> dict:
    if not LEAN_CLIENT_ID or not LEAN_CLIENT_SECRET:
        raise LeanError("Missing LEAN_CLIENT_ID or LEAN_CLIENT_SECRET in .env")

    url = f"{LEAN_AUTH_BASE_URL}/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "scope": "api",
        "client_id": LEAN_CLIENT_ID,
        "client_secret": LEAN_CLIENT_SECRET,
    }

    async with httpx.AsyncClient(timeout=25) as client:
        r = await client.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})

    if r.status_code != 200:
        raise LeanError(f"Lean token error {r.status_code}: {r.text}")

    return r.json()


async def create_customer(app_user_id: str) -> dict:
    token_data = await get_access_token()
    access_token = token_data["access_token"]

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    url_create = f"{LEAN_API_BASE_URL}/customers/v1"
    payload = {"app_user_id": app_user_id}

    async with httpx.AsyncClient(timeout=25) as client:
        r = await client.post(url_create, json=payload, headers=headers)

    if r.status_code == 409:
        url_get = f"{LEAN_API_BASE_URL}/customers/v1/app-user-id/{app_user_id}"
        async with httpx.AsyncClient(timeout=25) as client:
            r2 = await client.get(url_get, headers=headers)

        if r2.status_code != 200:
            raise LeanError(f"Customer exists but lookup failed {r2.status_code}: {r2.text}")

        existing = r2.json()
        customer_id = existing.get("customer_id") or (existing.get("customer") or {}).get("customer_id")
        if not customer_id:
            raise LeanError(f"Customer exists but no customer_id in lookup response: {existing}")

        return {"status": "CUSTOMER_ALREADY_EXISTS", "customer_id": customer_id}

    if r.status_code not in (200, 201):
        raise LeanError(f"Customer creation failed {r.status_code}: {r.text}")

    created = r.json()
    customer_id = created.get("customer_id") or (created.get("customer") or {}).get("customer_id")
    if not customer_id:
        raise LeanError(f"Create succeeded but no customer_id returned: {created}")

    return {"status": "CUSTOMER_CREATED", "customer_id": customer_id}


async def get_customer_token(customer_id: str) -> dict:
    if not LEAN_CLIENT_ID or not LEAN_CLIENT_SECRET:
        raise LeanError("Missing LEAN_CLIENT_ID or LEAN_CLIENT_SECRET in .env")

    url = f"{LEAN_AUTH_BASE_URL}/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "scope": f"customer.{customer_id}",
        "client_id": LEAN_CLIENT_ID,
        "client_secret": LEAN_CLIENT_SECRET,
        "audience":"https://sandbox.leantech.me",
    }

    async with httpx.AsyncClient(timeout=25) as client:
        r = await client.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})

    if r.status_code != 200:
        raise LeanError(f"Customer token failed {r.status_code}: {r.text}")

    return r.json()


async def create_link_session(customer_id: str) -> dict:
    token_data = await get_access_token()
    access_token = token_data["access_token"]

    url = f"{LEAN_API_BASE_URL}/connect/v1/customers/{customer_id}/link"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = {"redirect_url": LEAN_REDIRECT_URL}

    async with httpx.AsyncClient(timeout=25) as client:
        r = await client.post(url, json=data, headers=headers)

    if r.status_code != 200:
        raise LeanError(f"Link session failed {r.status_code}: {r.text}")

    return r.json()


async def get_link_config(customer_id: str) -> dict:
    if not LEAN_APP_TOKEN:
        raise LeanError("Missing LEAN_APP_TOKEN in .env")

    customer_token = await get_customer_token(customer_id)

    return {
        "customer_id": customer_id,
        "access_token": customer_token["access_token"],
        "token_type": customer_token.get("token_type", "Bearer"),
        "expires_in": customer_token.get("expires_in"),
        "app_token": LEAN_APP_TOKEN,
        "sandbox": True,
    }


async def get_entities_for_customer(customer_id: str) -> List[Dict[str, Any]]:
    token_data = await get_access_token()
    access_token = token_data["access_token"]

    url = f"{LEAN_API_BASE_URL}/customers/v1/{customer_id}/entities"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
        r = await client.get(url, headers=headers)

    if r.status_code != 200:
        raise LeanError(f"Get entities failed {r.status_code}: {r.text}")

    data = r.json()
    if isinstance(data, dict) and "entities" in data:
        return data["entities"] or []
    if isinstance(data, list):
        return data
    return []


def _pick_latest_entity(entities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not entities:
        return None

    def key_fn(e: Dict[str, Any]) -> str:
        return str(e.get("updated_at") or e.get("created_at") or "")

    return sorted(entities, key=key_fn, reverse=True)[0]


# -----------------------------
# DATA API (FIXED)
# -----------------------------
def _data_headers(customer_token: str, entity_id: str) -> Dict[str, str]:
    if not LEAN_APP_TOKEN:
        raise LeanError("Missing LEAN_APP_TOKEN in .env")

    return {
        "Authorization": f"Bearer {customer_token}",
        "x-lean-app-token": LEAN_APP_TOKEN,
        "x-lean-entity-id": entity_id,
        "accept": "application/json",
    }


async def get_accounts(entity_id: str):
    token_data = await get_access_token()  # API token
    api_token = token_data["access_token"]

    url = f"{LEAN_DATA_BASE_URL}/data/v2/accounts"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "accept": "application/json",
    }

    params = {
        "entity_id": entity_id
    }

    async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
        r = await client.get(url, headers=headers, params=params)

    print("STATUS:", r.status_code)
    print("BODY:", r.text)

    if r.status_code != 200:
        raise LeanError(f"Get accounts failed {r.status_code}: {r.text}")

    return r.json()


async def get_balance(customer_token: str, entity_id: str, account_id: str) -> List[Dict[str, Any]]:
    url = f"{LEAN_DATA_BASE_URL}/data/v2/accounts/{account_id}/balances"
    headers = _data_headers(customer_token, entity_id)

    async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
        r = await client.get(url, headers=headers)

    if r.status_code != 200:
        raise LeanError(f"Get balances failed {r.status_code}: {r.text}")

    data = r.json()
    return data.get("balances", data) if isinstance(data, dict) else data


async def get_transactions(customer_token: str, entity_id: str, account_id: str) -> List[Dict[str, Any]]:
    url = f"{LEAN_DATA_BASE_URL}/data/v2/accounts/{account_id}/transactions"
    headers = _data_headers(customer_token, entity_id)

    async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
        r = await client.get(url, headers=headers)

    if r.status_code != 200:
        raise LeanError(f"Get transactions failed {r.status_code}: {r.text}")

    data = r.json()
    return data.get("transactions", data) if isinstance(data, dict) else data

async def get_identity(customer_token: str, entity_id: str, account_id: str) -> Dict[str, Any]:
    url = f"{LEAN_DATA_BASE_URL}/data/v2/accounts/{account_id}/identity"
    headers = _data_headers(customer_token, entity_id)

    async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
        r = await client.get(url, headers=headers)

    if r.status_code != 200:
        raise LeanError(f"Get identity failed {r.status_code}: {r.text}")

    return r.json()

async def fetch_all_bank_data(customer_id: str) -> Dict[str, Any]:
    """
    Demo mode (default): returns fake banks + transactions locally.
    Real Lean mode: set USE_MOCK_WALLET=0 in your .env

    Result is cached per-customer for 5 minutes — the mock data is deterministic
    from customer_id, so a stale cached value is identical to a fresh one.
    """
    cached = mock_wallet_cache.get(customer_id)
    if cached is not None:
        return cached

    use_mock = os.getenv("USE_MOCK_WALLET", "1").strip() != "0"
    if use_mock:
        payload = build_connected_wallet_payload(customer_id, tx_per_bank=25)
    else:
        # (optional) your real Lean logic can stay below if you still want it
        # ...
        payload = build_connected_wallet_payload(customer_id, tx_per_bank=25)

    mock_wallet_cache[customer_id] = payload
    return payload