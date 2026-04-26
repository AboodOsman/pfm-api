# services/categorization_service.py

import os
import re
import json
from typing import Dict, List, Optional, Tuple

from repositories.category_repository import get_all_categories
from services.cache import categorize_cache

try:
    # New OpenAI Python SDK style
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore


# -----------------------------
# Keyword fallback rules
# -----------------------------
# (pattern, category_name, confidence)
KEYWORD_RULES: List[Tuple[str, str, float]] = [
    (r"\b(starbucks|coffee|cafe|pizza|burger|kfc|mcdonald|hardee|hardees|subway|talabat|deliveroo)\b", "Food", 0.95),
    (r"\b(grocery|groceries|supermarket|carrefour|lulu|coop|spinneys|choithrams)\b", "Groceries", 0.95),
    (r"\b(uber|careem|taxi|metro|bus|tram|fuel|petrol|gas)\b", "Transport", 0.95),
    (r"\b(rent|landlord|lease)\b", "Rent", 1.00),
    (r"\b(electric|water|internet|wifi|bill|utilities|dewa|sewa|etisalat|du)\b", "Bills", 0.90),
    (r"\b(amazon|noon|ikea|zara|hm|h&m|shopping|mall)\b", "Shopping", 0.90),
    (r"\b(pharmacy|hospital|clinic|doctor|dentist|medicine)\b", "Health", 0.90),
    (r"\b(cinema|movie|netflix|spotify|game|entertainment)\b", "Entertainment", 0.85),
    (r"\b(course|tuition|university|udemy|book|education)\b", "Education", 0.85),
    (r"\b(salary|payroll|wage)\b", "Salary", 0.95),
]


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _load_categories() -> Tuple[Dict[str, int], Dict[int, str]]:
    """
    Loads categories from Firestore and returns:
      name_to_id: {"Food": 1, ...}
      id_to_name: {1: "Food", ...}
    """
    cats = get_all_categories()
    name_to_id: Dict[str, int] = {}
    id_to_name: Dict[int, str] = {}

    for c in cats:
        name = (c.get("name") or "").strip()
        cid = c.get("category_id")
        if name and isinstance(cid, int):
            name_to_id[name] = cid
            id_to_name[cid] = name

    return name_to_id, id_to_name


def _fallback_by_keywords(description: str, allowed_names: List[str]) -> Dict:
    """
    Returns:
      {"category_name": str, "confidence": float, "source": "keyword"|"default"}
    """
    text = _normalize_text(description)
    allowed_set = set(allowed_names)

    for pattern, cat_name, conf in KEYWORD_RULES:
        if cat_name in allowed_set and re.search(pattern, text, flags=re.IGNORECASE):
            return {"category_name": cat_name, "confidence": conf, "source": "keyword"}

    default = "Other" if "Other" in allowed_set else allowed_names[-1]
    return {"category_name": default, "confidence": 0.50, "source": "default"}


def _ai_classify(description: str, allowed_names: List[str]) -> Optional[Dict]:
    """
    Returns dict with:
      {"category_name": str, "confidence": float, "source": "ai"}
    or None if AI isn't available / fails / no key / quota error.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None

    client = OpenAI(api_key=api_key)

    # ✅ No change needed — this is already correct
    system_prompt = (
        "You are a strict financial transaction classifier. "
        "You MUST choose exactly one category from the allowed list. "
        "Return ONLY valid JSON in this exact format:\n"
        '{"category":"<one allowed category>","confidence":<number between 0 and 1>}\n'
        "No extra keys. No explanation."
    )

    user_prompt = (
        f"Allowed categories: {allowed_names}\n"
        f"Transaction description: {description}\n"
        "Return JSON now."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=80,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = (resp.choices[0].message.content or "").strip()
        data = json.loads(content)

        cat = str(data.get("category", "")).strip()
        conf = float(data.get("confidence", 0.0))

        if cat not in allowed_names:
            return None

        conf = max(0.0, min(1.0, conf))
        return {"category_name": cat, "confidence": conf, "source": "ai"}

    except Exception:
        # covers quota errors, network errors, bad JSON, etc.
        return None


def categorize_transaction(description: str) -> Dict:
    """
    Main function used by your transaction flow.

    Returns:
      {
        "category_id": int | None,
        "category_name": str,
        "confidence": float,
        "source": "ai" | "keyword" | "default" | "no_categories"
      }

    Cached by description for 24h — results are deterministic per merchant
    string and the merchant set is small.
    """
    cache_key = _normalize_text(description)
    cached = categorize_cache.get(cache_key)
    if cached is not None:
        return cached

    name_to_id, _ = _load_categories()
    if not name_to_id:
        # Don't cache empty-categories result — could be a transient state.
        return {
            "category_id": None,
            "category_name": "Other",
            "confidence": 0.0,
            "source": "no_categories",
        }

    allowed_names = list(name_to_id.keys())

    # ✅ 1) Keywords first (fast + reliable)
    fb = _fallback_by_keywords(description, allowed_names)
    if fb["source"] == "keyword":
        cat_name = fb["category_name"]
        result = {
            "category_id": name_to_id[cat_name],
            "category_name": cat_name,
            "confidence": float(fb["confidence"]),
            "source": fb["source"],
        }
        categorize_cache[cache_key] = result
        return result

    # ✅ 2) AI second (handles unknown words)
    ai_result = _ai_classify(description, allowed_names)
    if ai_result:
        cat_name = ai_result["category_name"]
        result = {
            "category_id": name_to_id[cat_name],
            "category_name": cat_name,
            "confidence": float(ai_result["confidence"]),
            "source": ai_result["source"],
        }
        categorize_cache[cache_key] = result
        return result

    # ✅ 3) Default last
    cat_name = fb["category_name"]
    result = {
        "category_id": name_to_id[cat_name],
        "category_name": cat_name,
        "confidence": float(fb["confidence"]),
        "source": "default",
    }
    categorize_cache[cache_key] = result
    return result