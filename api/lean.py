import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from services.lean_service import (
    get_access_token,
    create_customer,
    create_link_session,
    get_customer_token,
    get_link_config,
    fetch_all_bank_data,
    get_entities_for_customer,
    get_accounts,
    get_balance,
    get_transactions,
    LeanError,
)

router = APIRouter(prefix="/lean", tags=["Lean"])


@router.get("/token")
async def api_get_lean_token():
    try:
        return await get_access_token()
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/customer")
async def api_create_customer(app_user_id: str = Query(...)):
    try:
        return await create_customer(app_user_id)
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/customer-token")
async def api_get_customer_token(customer_id: str = Query(...)):
    try:
        return await get_customer_token(customer_id)
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/link-session")
async def api_create_link_session(customer_id: str = Query(...)):
    try:
        return await create_link_session(customer_id)
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/link-config")
async def api_get_link_config(customer_id: str = Query(...)):
    try:
        return await get_link_config(customer_id)
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/data")
async def lean_data(customer_id: str = Query(...)):
    try:
        return await fetch_all_bank_data(customer_id)
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}")
    
@router.get("/entities")
async def api_get_entities(customer_id: str = Query(...)):
    try:
        return await get_entities_for_customer(customer_id)
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/accounts")
async def api_accounts(customer_id: str = Query(...), entity_id: str = Query(...)):
    try:
        cust = await get_customer_token(customer_id)
        customer_token = cust["access_token"]

        accounts = await get_accounts(customer_token, entity_id)
        return {"entity_id": entity_id, "accounts": accounts}
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/balance")
async def api_balance(customer_id: str = Query(...), entity_id: str = Query(...), account_id: str = Query(...)):
    try:
        cust = await get_customer_token(customer_id)
        customer_token = cust["access_token"]

        balances = await get_balance(customer_token, entity_id, account_id)
        return {"entity_id": entity_id, "account_id": account_id, "balances": balances}
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions")
async def api_transactions(customer_id: str = Query(...), entity_id: str = Query(...), account_id: str = Query(...)):
    try:
        cust = await get_customer_token(customer_id)
        customer_token = cust["access_token"]

        tx = await get_transactions(customer_token, entity_id, account_id)
        return {"entity_id": entity_id, "account_id": account_id, "transactions": tx}
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/link-page", response_class=HTMLResponse)
async def lean_link_page(customer_id: str = Query(...)):
    """
    Renders an HTML page that hosts Lean's official Web SDK and immediately
    calls Lean.connect(config). The page is served from this backend's origin
    so the SDK has a real HTTP origin to work in (loadHtmlString in a mobile
    WebView gives 'about:blank' which Lean rejects).

    On success / cancel / error the SDK's callback navigates the page to
    `/lean-callback?status=...` — the mobile WebView intercepts that URL
    *before* loading and emits the status to the dashboard.
    """
    try:
        config = await get_link_config(customer_id)
    except LeanError as e:
        raise HTTPException(status_code=400, detail=str(e))

    sdk_config = {
        "app_token": config["app_token"],
        "customer_id": config["customer_id"],
        "access_token": config["access_token"],
        "customer_token": config["access_token"],
        "permissions": ["identity", "accounts", "transactions", "balance"],
        "sandbox": True,
    }
    config_json = json.dumps(sdk_config)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Connect Bank</title>
  <style>
    html, body {{
      margin: 0; padding: 0; height: 100%; background: #FFD6E6;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    #status {{
      display: flex; align-items: center; justify-content: center; height: 100%;
      color: #3A1B52; font-weight: 600; padding: 16px; text-align: center;
    }}
  </style>
  <script src="https://cdn.leantech.me/link/loader/prod/ae/latest/lean-link-loader.min.js"></script>
</head>
<body>
  <div id="status">Loading bank connection…</div>
  <script>
    var CONFIG = {config_json};

    function leaveTo(payload) {{
      var qs = encodeURIComponent(JSON.stringify(payload || {{}}));
      window.location.href = '/lean-callback?payload=' + qs;
    }}

    function startLean() {{
      if (!window.Lean) {{
        document.getElementById('status').innerText =
          'Lean SDK failed to load. Check your internet.';
        leaveTo({{ status: 'ERROR', message: 'Lean SDK not loaded' }});
        return;
      }}
      CONFIG.callback = function(response) {{ leaveTo(response); }};
      try {{
        window.Lean.connect(CONFIG);
      }} catch (e) {{
        leaveTo({{ status: 'ERROR', message: String(e) }});
      }}
    }}

    if (document.readyState === 'complete') {{
      startLean();
    }} else {{
      window.addEventListener('load', startLean);
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


