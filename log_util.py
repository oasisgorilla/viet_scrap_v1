### log_util.py ###
# logging라이브러리 관련 설정을 다룹니다.

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

# 한국시간 정의(UTC+9)
KST = timezone(timedelta(hours=9))

# 커스텀 포멧
class KSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=KST)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()


def setup_logger(name: str, log_file: str, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        logger.handlers.clear()

    log_dir = Path(log_file).parent
    os.makedirs(log_dir, exist_ok=True)

    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    handler.setLevel(logging.ERROR)
    formatter = KSTFormatter('[%(asctime)s] [%(levelname)s] %(message)s', "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.addHandler(console_handler)

    return logger