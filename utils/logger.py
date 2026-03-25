import logging
import os


def get_user_logger(user_id: int) -> logging.Logger:
    logger = logging.getLogger(f"user_{user_id}")
    if logger.handlers:
        return logger

    os.makedirs("logs", exist_ok=True)
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(f"logs/user_{user_id}.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    logger.addHandler(handler)

    return logger
