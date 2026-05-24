"""llm_retry – Retry helper for Mistral API calls.

Wraps any callable that can raise a rate-limit (429) error and retries it
with exponential back-off + jitter.

Usage
-----
    from backend.tasks.llm_retry import call_with_retry

    response = call_with_retry(
        lambda: client.chat.complete(model=..., messages=...),
        max_retries=4,
        base_delay=2.0,
    )
"""

from __future__ import annotations

import random
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# Strings that identify a rate-limit response from Mistral
_RATE_LIMIT_MARKERS = ("429", "rate limit", "rate_limited", "1300")


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _RATE_LIMIT_MARKERS)


def call_with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int = 4,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> T:
    """Call *fn* and retry on 429 rate-limit errors with exponential back-off.

    Parameters
    ----------
    fn:
        A zero-argument callable that performs the LLM API call.
    max_retries:
        Maximum number of retry attempts (not counting the first call).
    base_delay:
        Initial wait time in seconds before the first retry.
    max_delay:
        Cap on the wait time between retries.
    jitter:
        Add ±25 % random jitter to each delay to spread load.
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if not _is_rate_limit(exc):
                # Non-rate-limit error → re-raise immediately
                raise

            if attempt == max_retries:
                break

            delay = min(base_delay * (2 ** attempt), max_delay)
            if jitter:
                delay *= random.uniform(0.75, 1.25)

            print(
                f"[llm_retry] ⚠️  Rate limit (429) — attente {delay:.1f}s "
                f"avant retry {attempt + 1}/{max_retries}..."
            )
            time.sleep(delay)

    print(f"[llm_retry] ❌ Toutes les tentatives épuisées ({max_retries} retries).")
    raise last_exc  # type: ignore[misc]
