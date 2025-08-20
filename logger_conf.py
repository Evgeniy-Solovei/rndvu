import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime


def setup_logger(name, log_file, level=logging.DEBUG):
    """Настройка логгера с указанным именем и файлом"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, log_file)

    handler = TimedRotatingFileHandler(
        log_file_path,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )

    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s:%(lineno)d] - %(message)s'
    )
    handler.setFormatter(formatter)

    # Удаляем все старые обработчики (если есть)
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(handler)

    # Добавляем вывод в консоль с тем же форматтером
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Один логгер для всего (и инфо, и ошибки и пр.)
logger = setup_logger("gift_system", f"{datetime.now().strftime('%Y-%m-%d')}.log", logging.DEBUG)
