# debug_app.py
"""
Диагностический скрипт для отладки запуска приложения
"""

import sys
import os
import traceback
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def debug_main():
    """Основная функция отладки"""
    logger.info("=" * 60)
    logger.info("ЗАПУСК ДИАГНОСТИКИ SABY HELPER")
    logger.info(f"Python версия: {sys.version}")
    logger.info(f"Рабочая директория: {os.getcwd()}")
    logger.info(f"Путь Python: {sys.path}")
    logger.info("=" * 60)
    
    try:
        # Проверяем наличие основных файлов
        required_files = [
            'main.py', 'app.py', 'main_window.py', 'config.py',
            'analyzer.py', 'log_analyzer.py', 'marking_analyzer.py',
            'basic_mechanisms_analyzer.py', 'payment_terminal_analyzer.py'
        ]
        
        for file in required_files:
            if Path(file).exists():
                logger.info(f"✅ Файл {file} существует")
            else:
                logger.error(f"❌ Файл {file} не найден!")
        
        # Проверяем наличие модулей
        required_modules = ['modules', 'utils', 'ui_components']
        for module in required_modules:
            module_path = Path(module)
            if module_path.exists():
                logger.info(f"✅ Папка {module} существует")
                # Проверяем важные файлы внутри
                for item in module_path.iterdir():
                    if item.suffix == '.py':
                        logger.info(f"  - Файл: {item.name}")
            else:
                logger.error(f"❌ Папка {module} не найдена!")
        
        # Пробуем импортировать основные модули
        logger.info("\nПроверка импорта модулей...")
        
        modules_to_check = [
            ('app', 'SabyHelperApp'),
            ('main_window', 'MainWindow'),
            ('config', 'APP_VERSION'),
            ('basic_mechanisms_analyzer', 'BasicMechanismsAnalyzer'),
            ('payment_terminal_analyzer', 'PaymentTerminalAnalyzer')
        ]
        
        for module_name, item_name in modules_to_check:
            try:
                module = __import__(module_name)
                logger.info(f"✅ Модуль {module_name} успешно импортирован")
                if hasattr(module, item_name):
                    logger.info(f"  - Атрибут {item_name} найден")
                else:
                    logger.warning(f"  - Атрибут {item_name} не найден")
            except Exception as e:
                logger.error(f"❌ Ошибка импорта {module_name}: {e}")
                logger.debug(traceback.format_exc())
        
        # Пробуем запустить приложение
        logger.info("\nПопытка запуска приложения...")
        try:
            from app import SabyHelperApp
            
            logger.info("Создание экземпляра приложения...")
            app = SabyHelperApp(sys.argv)
            logger.info("Запуск главного цикла...")
            return app.exec_()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска приложения: {e}")
            logger.error(traceback.format_exc())
            return 1
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в диагностике: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(debug_main())