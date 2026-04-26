# api/utils.py
from datetime import datetime, date
from typing import Any


def jsonable(x: Any):
    if isinstance(x, (datetime, date)):
        return x.isoformat()

    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}

    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]

    return x