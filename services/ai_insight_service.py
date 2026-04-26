import os
import json
import traceback
from collections import defaultdict
from typing import Any, Dict
import asyncio

from openai import OpenAI
from services.lean_service import fetch_all_bank_data

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
AI_INSIGHT_MODEL = os.getenv("AI_INSIGHT_MODEL", "gpt-4.1-mini")


INSIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "top_category": {"type": "string"},
        "top_category_amount": {"type": "number"},
        "risk_level": {
            "type": "string",
            "enum": ["low", "moderate", "high"]
        },
        "forecast_next_month_income": {"type": "number"},
        "forecast_next_month_expenses": {"type": "number"},
        "forecast_next_month_savings_rate": {"type": "number"},
        "forecast_basis": {"type": "string"},
        "actions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 3
        }
    },
    "required": [
        "headline",
        "summary",
        "top_category",
        "top_category_amount",
        "risk_level",
        "forecast_next_month_income",
        "forecast_next_month_expenses",
        "forecast_next_month_savings_rate",
        "forecast_basis",
        "actions"
    ],
    "additionalProperties": False
}


def _to_float(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v))
    except Exception:
        return 0.0


def _build_financial_summary(payload: Dict[str, Any], bank_id: str | None) -> Dict[str, Any]:
    banks = payload.get("banks", []) or []
    accounts = payload.get("accounts", []) or []
    transactions = payload.get("transactions", []) or []

    if bank_id:
        accounts = [
            a for a in accounts
            if isinstance(a, dict) and str(a.get("bank_id", "")) == str(bank_id)
        ]
        transactions = [
            t for t in transactions
            if isinstance(t, dict) and str(t.get("bank_id", "")) == str(bank_id)
        ]

    bank_name = "Connected Bank"
    if bank_id:
        for b in banks:
            if isinstance(b, dict) and str(b.get("id", "")) == str(bank_id):
                bank_name = str(b.get("name", "Connected Bank"))
                break
    elif banks and isinstance(banks[0], dict):
        bank_name = str(banks[0].get("name", "Connected Bank"))

    current_balance = 0.0
    if accounts:
        acc = accounts[0]
        bal = acc.get("balance", 0)
        if isinstance(bal, dict):
            current_balance = _to_float(bal.get("available") or bal.get("current") or 0)
        else:
            current_balance = _to_float(bal)

    income = 0.0
    expenses = 0.0
    category_totals = defaultdict(float)
    merchant_totals = defaultdict(float)
    monthly_totals = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})

    for t in transactions:
        if not isinstance(t, dict):
            continue

        amount = _to_float(t.get("amount", 0))
        tx_date = str(t.get("date") or t.get("timestamp") or "").strip()
        month_key = None

        if tx_date:
            try:
                month_key = tx_date[:7]
            except Exception:
                month_key = None

        if amount > 0:
            income += amount
            if month_key:
                monthly_totals[month_key]["income"] += amount

        elif amount < 0:
            spent = abs(amount)
            expenses += spent

            category = str(t.get("category") or "Other")
            merchant = str(t.get("description") or t.get("merchant_name") or "Unknown")

            category_totals[category] += spent
            merchant_totals[merchant] += spent

            if month_key:
                monthly_totals[month_key]["expenses"] += spent

    top_categories = [
        {"name": k, "amount": round(v, 2)}
        for k, v in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    top_merchants = [
        {"name": k, "amount": round(v, 2)}
        for k, v in sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    saving_rate_percent = round(((income - expenses) / income) * 100, 2) if income > 0 else 0.0

    monthly_history = []
    for month, vals in sorted(monthly_totals.items()):
        m_income = round(vals["income"], 2)
        m_expenses = round(vals["expenses"], 2)
        m_saving_rate = round(((m_income - m_expenses) / m_income) * 100, 2) if m_income > 0 else 0.0

        monthly_history.append({
            "month": month,
            "income": m_income,
            "expenses": m_expenses,
            "saving_rate_percent": m_saving_rate,
        })

    last_6_months = monthly_history[-6:]

    if last_6_months:
        weights = list(range(1, len(last_6_months) + 1))
        total_weight = sum(weights)

        forecast_income = round(
            sum(m["income"] * w for m, w in zip(last_6_months, weights)) / total_weight, 2
        )
        forecast_expenses = round(
            sum(m["expenses"] * w for m, w in zip(last_6_months, weights)) / total_weight, 2
        )
    else:
        forecast_income = 0.0
        forecast_expenses = 0.0

    forecast_savings_rate = round(
        ((forecast_income - forecast_expenses) / forecast_income) * 100, 2
    ) if forecast_income > 0 else 0.0

    return {
        "bank_name": bank_name,
        "currency": "AED",
        "current_balance": round(current_balance, 2),
        "current_period_income": round(income, 2),
        "current_period_expenses": round(expenses, 2),
        "saving_rate_percent": saving_rate_percent,
        "top_categories": top_categories,
        "top_merchants": top_merchants,
        "transaction_count": len(transactions),
        "monthly_history": last_6_months,
        "forecast_next_month_income": forecast_income,
        "forecast_next_month_expenses": forecast_expenses,
        "forecast_next_month_savings_rate": forecast_savings_rate,
    }


async def generate_ai_spending_insight(
    customer_id: str,
    bank_id: str | None = None
) -> Dict[str, Any]:
    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Missing OPENAI_API_KEY in .env")

        print(f"[AI INSIGHT] customer_id={customer_id}, bank_id={bank_id}")

        payload = await fetch_all_bank_data(customer_id)
        print("[AI INSIGHT] fetch_all_bank_data success")

        summary = _build_financial_summary(payload, bank_id)
        print("[AI INSIGHT] summary built:", json.dumps(summary, indent=2))

        if summary["transaction_count"] == 0:
            return {
                "headline": "No transaction history yet",
                "summary": "There are no transactions available for this bank yet, so an AI insight cannot be generated.",
                "top_category": "None",
                "top_category_amount": 0,
                "risk_level": "low",
                "forecast_next_month_income": 0.0,
                "forecast_next_month_expenses": 0.0,
                "forecast_next_month_savings_rate": 0.0,
                "forecast_basis": "No forecast available.",
                "actions": [
                    "Connect or refresh your bank data",
                    "Check again after transactions are available"
                ]
            }

        response = await asyncio.to_thread(
            lambda: client.responses.create(
                model=AI_INSIGHT_MODEL,
                input=[
                    {
                        "role": "developer",
                        "content": (
                            "You are a senior fintech spending analyst. "
"Generate concise, professional, practical spending insights for a personal finance dashboard. "
"Base the response only on the provided JSON summary. "
"Do not mention that you are an AI. "
"Keep the wording calm, precise, and useful. "
"Use the provided monthly_history and forecast fields to explain the user's spending pattern and next-month outlook. "
"Do not invent data beyond the provided summary. "
"Keep the summary short and dashboard-friendly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(summary),
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "spending_insight",
                        "strict": True,
                        "schema": INSIGHT_SCHEMA,
                    }
                },
            )
        )

        print("[AI INSIGHT] OpenAI response received")
        print("[AI INSIGHT] output_text:", response.output_text)

        result = json.loads(response.output_text)

        forecast_income = round(summary.get("forecast_next_month_income", 0.0), 2)
        forecast_expenses = round(summary.get("forecast_next_month_expenses", 0.0), 2)
        forecast_rate = round(summary.get("forecast_next_month_savings_rate", 0.0), 2)

        monthly_history = summary.get("monthly_history", []) or []

        if len(monthly_history) >= 2:
            basis = (
                f"Based on a weighted average of the most recent {len(monthly_history)} months, "
                f"with greater weight on newer months."
            )
        elif len(monthly_history) == 1:
            basis = f"Based on the latest available month ({monthly_history[-1]['month']})."
        else:
            basis = "No forecast available."

        result["forecast_next_month_income"] = forecast_income
        result["forecast_next_month_expenses"] = forecast_expenses
        result["forecast_next_month_savings_rate"] = forecast_rate
        result["forecast_basis"] = basis

        

        return result

    except Exception as e:
        print("[AI INSIGHT SERVICE ERROR]", str(e))
        traceback.print_exc()
        return {
            "headline": "Insight temporarily unavailable",
            "summary": "Your spending data was loaded, but the AI insight service could not generate a result right now.",
            "top_category": "Unknown",
            "top_category_amount": 0,
            "risk_level": "low",
            "forecast_next_month_income": 0.0,
            "forecast_next_month_expenses": 0.0,
            "forecast_next_month_savings_rate": 0.0,
            "forecast_basis": "No forecast available.",
            "actions": [
                "Try refreshing again in a moment",
                "Check backend logs for the exact AI error"
            ]
        }