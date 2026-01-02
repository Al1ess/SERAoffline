# utils/logger.py
"""
Утилиты для логирования приложения
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from config import LOG_FILE, LOG_FORMAT

class LogFormatter(logging.Formatter):
    """Кастомный форматтер для логов"""
    
    def format(self, record):
        # Добавляем время выполнения в лог
        if not hasattr(record, 'relative_created_ms'):
            record.relative_created_ms = record.relativeCreated
        
        # Форматируем время
        record.relative_created_fmt = f"{record.relative_created_ms:.0f}ms"
        
        # Добавляем информацию о потоке
        if record.threadName:
            record.thread_info = f"[{record.threadName}]"
        else:
            record.thread_info = ""
        
        return super().format(record)

def setup_logging():
    """Настройка системы логирования"""
    
    # Создаем корневой логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Удаляем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Создаем форматтер
    formatter = LogFormatter(LOG_FORMAT)
    
    # Файловый обработчик
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Не удалось создать файловый логгер: {e}")
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Логируем запуск
    logger.info("=" * 60)
    logger.info(f"Saby Helper v{__import__('config').APP_VERSION} запущен")
    logger.info(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Путь к лог-файлу: {LOG_FILE}")
    logger.info("=" * 60)
    
    return logger

def log_function_call(logger):
    """Декоратор для логирования вызовов функций"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.info(f"Вызов функции: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"Функция {func.__name__} выполнена успешно")
                return result
            except Exception as e:
                logger.error(f"Ошибка в функции {func.__name__}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator