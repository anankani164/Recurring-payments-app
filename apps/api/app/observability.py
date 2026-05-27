import json
import logging
from datetime import datetime, timezone


logger = logging.getLogger("recurring_payments")


def configure_logging(json_logs: bool = True) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not json_logs:
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))


def log_event(level: str, event: str, **fields) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        **fields,
    }
    message = json.dumps(payload, default=str)
    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)
