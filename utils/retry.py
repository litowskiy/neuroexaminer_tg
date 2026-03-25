import logging

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
from openai import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
    PermissionDeniedError,
    AuthenticationError,
)

logger = logging.getLogger(__name__)

# Ошибки при которых имеет смысл повторять запрос:
#   - APIConnectionError  → сеть/таймаут
#   - APITimeoutError     → таймаут
#   - RateLimitError      → превышен лимит (429)
#   - InternalServerError → ошибка на стороне OpenAI (500/503)
#
# НЕ повторяем:
#   - PermissionDeniedError → географическая блокировка (нужен прокси)
#   - AuthenticationError   → неверный API ключ
_RETRYABLE = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)


def openai_retry(func):
    """
    Декоратор: до 3 попыток, пауза 5 → 10 → 20 сек (exponential backoff).
    Перед каждой повторной попыткой пишет в лог.
    """
    return retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=20),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )(func)
