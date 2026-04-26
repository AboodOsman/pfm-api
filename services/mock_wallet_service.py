from __future__ import annotations
from services.categorization_service import categorize_transaction

import hashlib
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


BANK_ONE_MERCHANTS = [
    ("Carrefour", "Groceries"),
    ("Lulu Hypermarket", "Groceries"),
    ("Union Coop", "Groceries"),
    ("Talabat", "Food & Delivery"),
    ("Deliveroo", "Food & Delivery"),
    ("KFC", "Dining"),
    ("McDonald's", "Dining"),
    ("Costa Coffee", "Dining"),
    ("Starbucks", "Dining"),
    ("RTA", "Transport"),
    ("Careem", "Transport"),
    ("Uber", "Transport"),
    ("DEWA", "Utilities"),
    ("Etisalat", "Telecom"),
    ("Amazon", "Shopping"),
    ("Noon", "Shopping"),
    ("Zara", "Shopping"),
    ("H&M", "Shopping"),
    ("Vox Cinemas", "Entertainment"),
    ("Netflix", "Entertainment"),
]

BANK_TWO_MERCHANTS = [
    ("Spinneys", "Groceries"),
    ("Waitrose", "Groceries"),
    ("Choithrams", "Groceries"),
    ("Noon", "Shopping"),
    ("Namshi", "Shopping"),
    ("Amazon", "Shopping"),
    ("Apple Store", "Shopping"),
    ("Dubai Mall", "Shopping"),
    ("Careem", "Transport"),
    ("Uber", "Transport"),
    ("Emirates", "Travel"),
    ("Air Arabia", "Travel"),
    ("Booking.com", "Travel"),
    ("Etisalat", "Telecom"),
    ("du", "Telecom"),
    ("DEWA", "Utilities"),
    ("Deliveroo", "Food & Delivery"),
    ("Talabat", "Food & Delivery"),
    ("Shake Shack", "Dining"),
    ("Five Guys", "Dining"),
    ("Shein", "Shopping"),
]


def _seed_from_customer(customer_id: str) -> int:
    h = hashlib.sha256(customer_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _user_income_profile(rng: random.Random) -> Dict[str, float]:
    salary = rng.choice([4000, 4500, 5000, 5500, 6000, 7000, 8000])
    rent = rng.choice([0, 1200, 1500, 1800, 2000, 2500])
    freelance_base = rng.choice([0, 500, 800, 1200, 1500])
    return {
        "salary": float(salary),
        "rent": float(rent),
        "freelance_base": float(freelance_base),
    }


def _income_tx(
    *,
    bank_id: str,
    bank_name: str,
    account_id: str,
    tx_id: str,
    tx_date: datetime,
    amount: float,
    description: str,
    income_source: str,
) -> Dict[str, Any]:
    return {
        "id": tx_id,
        "bank_id": bank_id,
        "bank_name": bank_name,
        "account_id": account_id,
        "timestamp": tx_date.isoformat(),
        "date": tx_date.strftime("%Y-%m-%d"),
        "description": description,
        "amount": round(amount, 2),
        "currency": "AED",
        "txn_type": "INCOME",
        "direction": "in",
        "income_source": income_source,
        "ai_category": "Income",
        "category": "Income",
        "category_id": None,
        "ai_confidence": 1.0,
        "categorization_source": "system",
    }


def _expense_tx(
    *,
    rng: random.Random,
    bank_id: str,
    bank_name: str,
    account_id: str,
    tx_id: str,
    tx_date: datetime,
) -> Dict[str, Any]:
    merchant_pool = (
        BANK_ONE_MERCHANTS if "one" in bank_name.lower() else BANK_TWO_MERCHANTS
    )
    merchant, _old_category = rng.choice(merchant_pool)

    if merchant in ["RTA", "Careem", "Uber"]:
        amount = -round(rng.uniform(15, 120), 2)
    elif merchant in ["DEWA", "Etisalat", "du", "Netflix"]:
        amount = -round(rng.uniform(80, 450), 2)
    elif merchant in ["Amazon", "Noon", "Zara", "H&M", "Namshi", "Shein", "Apple Store"]:
        amount = -round(rng.uniform(50, 650), 2)
    elif merchant in ["Emirates", "Air Arabia", "Booking.com"]:
        amount = -round(rng.uniform(200, 1500), 2)
    else:
        amount = -round(rng.uniform(20, 280), 2)

    cat = categorize_transaction(merchant)
    ai_category = cat.get("category_name", "Other")
    category_id = cat.get("category_id")
    ai_confidence = float(cat.get("confidence", 0.0))
    categorization_source = cat.get("source", "ai")

    return {
        "id": tx_id,
        "bank_id": bank_id,
        "bank_name": bank_name,
        "account_id": account_id,
        "timestamp": tx_date.isoformat(),
        "date": tx_date.strftime("%Y-%m-%d"),
        "description": merchant,
        "amount": amount,
        "currency": "AED",
        "txn_type": "EXPENSE",
        "direction": "out",
        "income_source": None,
        "ai_category": ai_category,
        "category": ai_category,
        "category_id": category_id,
        "ai_confidence": ai_confidence,
        "categorization_source": categorization_source,
    }


def build_connected_wallet_payload(
    customer_id: str,
    *,
    connected_banks: Optional[List[Dict[str, Any]]] = None,
    tx_per_bank: int = 25,
) -> Dict[str, Any]:
    now = datetime.utcnow()
    seed = _seed_from_customer(customer_id)
    master_rng = random.Random(seed)

    banks = connected_banks or [
        {"id": "mockbank1", "name": "MockBank One", "connected_at": now.isoformat()},
        {"id": "mockbank2", "name": "MockBank Two", "connected_at": now.isoformat()},
    ]

    accounts: List[Dict[str, Any]] = []
    transactions: List[Dict[str, Any]] = []

    profile = _user_income_profile(master_rng)

    for idx, bank in enumerate(banks):
        bank_id = str(bank["id"])
        bank_name = str(bank["name"])
        account_id = f"{bank_id}_acc_1"
        rng = random.Random(seed + (idx + 1) * 100_000)

        bank_transactions: List[Dict[str, Any]] = []

        for month_offset in range(6):
            base_month = now.month - month_offset
            year = now.year
            month = base_month

            while month <= 0:
                month += 12
                year -= 1

            monthly_count = rng.randint(20, 25)

            salary_day = rng.randint(1, 3)
            salary_date = datetime(year, month, min(salary_day, 28), 9, 0, 0)
            bank_transactions.append(
                _income_tx(
                    bank_id=bank_id,
                    bank_name=bank_name,
                    account_id=account_id,
                    tx_id=f"{bank_id}salary{year}_{month}",
                    tx_date=salary_date,
                    amount=profile["salary"],
                    description="Monthly Salary",
                    income_source="salary",
                )
            )

            if profile["rent"] > 0:
                rent_day = rng.randint(4, 8)
                rent_date = datetime(year, month, min(rent_day, 28), 10, 0, 0)
                bank_transactions.append(
                    _income_tx(
                        bank_id=bank_id,
                        bank_name=bank_name,
                        account_id=account_id,
                        tx_id=f"{bank_id}rent{year}_{month}",
                        tx_date=rent_date,
                        amount=profile["rent"],
                        description="Accommodation Rent Received",
                        income_source="rent",
                    )
                )

            if rng.random() < 0.8 and profile["freelance_base"] > 0:
                freelance_amount = max(
                    150.0,
                    profile["freelance_base"] + rng.uniform(-300, 700),
                )
                freelance_day = rng.randint(10, 20)
                freelance_date = datetime(
                    year, month, min(freelance_day, 28), 11, 0, 0
                )
                bank_transactions.append(
                    _income_tx(
                        bank_id=bank_id,
                        bank_name=bank_name,
                        account_id=account_id,
                        tx_id=f"{bank_id}freelance{year}_{month}",
                        tx_date=freelance_date,
                        amount=freelance_amount,
                        description="Freelance Payment",
                        income_source="freelance",
                    )
                )

            extra_income_count = rng.randint(0, 2)
            for k in range(extra_income_count):
                source = rng.choice(["cash_deposit", "transfer_in"])
                desc = "Cash Deposit" if source == "cash_deposit" else "Transfer Received"
                amount = rng.uniform(100, 1200)
                day = rng.randint(6, 27)
                dt = datetime(year, month, min(day, 28), 12, 0, 0)
                bank_transactions.append(
                    _income_tx(
                        bank_id=bank_id,
                        bank_name=bank_name,
                        account_id=account_id,
                        tx_id=f"{bank_id}{source}{year}{month}{k}",
                        tx_date=dt,
                        amount=amount,
                        description=desc,
                        income_source=source,
                    )
                )

            current_month_prefix = f"{year}-{str(month).zfill(2)}"
            current_month_tx_count = len(
                [t for t in bank_transactions if t["date"].startswith(current_month_prefix)]
            )
            remaining = monthly_count - current_month_tx_count

            for j in range(max(remaining, 0)):
                day = rng.randint(1, 28)
                dt = datetime(
                    year,
                    month,
                    day,
                    rng.randint(8, 22),
                    rng.randint(0, 59),
                    0,
                )
                bank_transactions.append(
                    _expense_tx(
                        rng=rng,
                        bank_id=bank_id,
                        bank_name=bank_name,
                        account_id=account_id,
                        tx_id=f"{bank_id}expense{year}{month}{j}",
                        tx_date=dt,
                    )
                )

        bank_transactions.sort(key=lambda t: t["timestamp"], reverse=True)
        transactions.extend(bank_transactions)

        balance = 5000.0 + sum(float(t["amount"]) for t in bank_transactions)

        accounts.append(
            {
                "account_id": account_id,
                "bank_id": bank_id,
                "bank_name": bank_name,
                "currency": "AED",
                "balance": round(balance, 2),
                "type": "CURRENT",
                "last4": str((seed + idx + 17) % 10000).zfill(4),
            }
        )

    transactions.sort(key=lambda t: t["timestamp"], reverse=True)

    income = sum(float(t["amount"]) for t in transactions if float(t["amount"]) > 0)
    expenses = -sum(float(t["amount"]) for t in transactions if float(t["amount"]) < 0)
    total_balance = sum(float(a["balance"]) for a in accounts)

    summary = {
        "currency": "AED",
        "balance": round(total_balance, 2),
        "income_month": round(income, 2),
        "expenses_month": round(expenses, 2),
        "is_user_override": False,
    }

    identity = {
        "name": "Demo User",
        "address": "Dubai, UAE",
    }

    return {
        "customer_id": customer_id,
        "connected": True,
        "banks": banks,
        "accounts": accounts,
        "transactions": transactions,
        "identity": identity,
        "summary": summary,
    }