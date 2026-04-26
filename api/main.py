from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # PFFM root (where api/ exists)
load_dotenv(BASE_DIR / ".env")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.users import router as users_router
from api.categories import router as categories_router
from api.transactions import router as transactions_router
from api.budgets import router as budgets_router
from api.goals import router as goals_router
from api.alerts import router as alerts_router
from api.badges import router as badges_router
from api.auth import router as auth_router
from api.lean import router as lean_router
from api.ai_chat import router as ai_chat_router
from api.receipts import router as receipts_router
app = FastAPI(title="PFFM API (Firebase)")
from api.ai_insights import router as ai_insights_router
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # for dev (later restrict)
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],)
# Optional: stop the "/" 404
@app.get("/")
def root():
    return {"ok": True, "message": "PFFM API is running. Open /docs"}
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(budgets_router)
app.include_router(goals_router)
app.include_router(alerts_router)
app.include_router(badges_router)
app.include_router(auth_router)
app.include_router(lean_router)
app.include_router(ai_insights_router)
app.include_router(ai_chat_router)
app.include_router(receipts_router)