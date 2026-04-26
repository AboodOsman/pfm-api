import os
from typing import Any
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _top_categories(transactions: list[dict[str, Any]]) -> list[tuple[str, float]]:
    by_category = {}

    for t in transactions:
        raw_amount = t.get("amount", 0)
        try:
            amount = float(raw_amount)
        except Exception:
            amount = 0.0

        # only expenses
        if amount >= 0:
            continue

        category = (
            str(t.get("ai_category") or t.get("category") or "Other").strip()
            or "Other"
        )

        by_category[category] = by_category.get(category, 0.0) + abs(amount)

    return sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:5]


def _recent_transactions_text(transactions: list[dict[str, Any]]) -> str:
    recent = transactions[:5]
    if not recent:
        return "- No recent transactions"

    lines = []
    for t in recent:
        desc = t.get("description") or t.get("merchant_name") or "Transaction"
        amount = t.get("amount", 0)
        date = t.get("date") or t.get("timestamp") or ""
        lines.append(f"- {desc} | {amount} AED | {date}")

    return "\n".join(lines)


def _goals_text(goals: list[dict[str, Any]]) -> str:
    if not goals:
        return "- No goals found"

    lines = []
    for g in goals:
        name = g.get("name", "Goal")
        target = g.get("targetAmount", 0)
        saved = g.get("savedAmount", 0)
        lines.append(f"- {name}: saved {saved} / target {target} AED")

    return "\n".join(lines)


def generate_finance_reply(
    user_id: str,
    question: str,
    totals: dict[str, Any],
    transactions: list[dict[str, Any]],
    goals: list[dict[str, Any]],
) -> str:
    balance = totals.get("balance", 0)
    income = totals.get("income", 0)
    expenses = totals.get("expenses", 0)

    categories = _top_categories(transactions)
    categories_text = (
        "\n".join([f"- {name}: {amount:.2f} AED" for name, amount in categories])
        if categories
        else "- No category data"
    )

    recent_tx_text = _recent_transactions_text(transactions)
    goals_summary = _goals_text(goals)

    system_prompt = """
You are Pocket Assistant, a smart finance assistant inside a personal finance app.

Use only the provided user account data.
Answer in a natural, helpful, clear way.
Be specific when data exists.
If the user asks for advice, base it on their spending, goals, and totals.
Keep answers concise but useful.
"""

    user_prompt = f"""
User ID: {user_id}

Account totals:
- Balance: {balance} AED
- Income: {income} AED
- Expenses: {expenses} AED

Top categories:
{categories_text}

Recent transactions:
{recent_tx_text}

Goals:
{goals_summary}

User question:
{question}
"""

    response = client.responses.create(
    model="gpt-4.1-mini",
    input=[
        {
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": system_prompt,
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": user_prompt,
                }
            ],
        },
    ],
)



    return response.output_text.strip() or "No response."