"""
Simple in-process cache layer for Firestore reads.

Goals:
- Reduce Firestore read quota usage.
- Speed up endpoints that re-read identical data many times.
- Stay behavior-identical: every cache invalidates on the corresponding write.

Caches are scoped per-process. Multiple Render workers each get their own cache,
which is fine — the data is read-mostly and TTLs are short.
"""

from cachetools import TTLCache

# Categories rarely change (seeded once at deploy). Long TTL.
categories_cache: TTLCache = TTLCache(maxsize=4, ttl=3600)  # 1 hour

# User lookups by id and by email. Short TTL so profile updates show up quickly.
user_by_id_cache: TTLCache = TTLCache(maxsize=2048, ttl=60)  # 60s
user_by_email_cache: TTLCache = TTLCache(maxsize=2048, ttl=60)  # 60s

# Mock wallet data is deterministic from customer_id but takes CPU to generate
# 150 transactions. Cache for 5 minutes.
mock_wallet_cache: TTLCache = TTLCache(maxsize=512, ttl=300)  # 5 min

# Categorization is deterministic per description and the merchant set is small.
# A long TTL is fine; results don't change for a given string.
categorize_cache: TTLCache = TTLCache(maxsize=4096, ttl=86400)  # 24h

# AI spending insight per (customer_id, bank_id). Mock data is deterministic
# from customer_id, so the insight doesn't meaningfully change minute-to-minute.
# 30 minutes balances freshness vs OpenAI cost.
ai_insight_cache: TTLCache = TTLCache(maxsize=512, ttl=1800)  # 30 min


def invalidate_ai_insight(customer_id: str = None) -> None:
    if customer_id is None:
        ai_insight_cache.clear()
        return
    # Drop any cached entry for this customer (any bank_id)
    keys = [k for k in list(ai_insight_cache.keys()) if k[0] == customer_id]
    for k in keys:
        ai_insight_cache.pop(k, None)


def invalidate_user(user_id: int = None, email: str = None) -> None:
    """Drop cached user records when the underlying doc changes."""
    if user_id is not None:
        user_by_id_cache.pop(int(user_id), None)
    if email is not None:
        user_by_email_cache.pop(email.lower().strip(), None)


def invalidate_categories() -> None:
    categories_cache.clear()


def invalidate_mock_wallet(customer_id: str = None) -> None:
    if customer_id is None:
        mock_wallet_cache.clear()
    else:
        mock_wallet_cache.pop(customer_id, None)
