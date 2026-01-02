import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import QApplication
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('saby_helper_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def resource_path(relative_path):
    """Получает абсолютный путь к ресурсу для PyInstaller"""
    try:
        # PyInstaller создает временную папку в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def main():
    """Главная функция запуска приложения"""
    try:
        logger.info("=" * 50)
        logger.info("Запуск Saby Helper v1.5.3")
        logger.info(f"Python версия: {sys.version}")
        logger.info(f"Рабочая директория: {os.getcwd()}")
        logger.info(f"Платформа: {sys.platform}")
        logger.info("=" * 50)
        
        # Проверяем наличие config.txt
        possible_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.txt"),
            os.path.join(os.getcwd(), "config.txt"),
            resource_path("config.txt"),
            "config.txt"
        ]
        
        config_found = False
        for config_path in possible_paths:
            if os.path.exists(config_path):
                logger.info(f"Найден config.txt: {config_path}")
                try:
                    with open(config_path, "r", encoding='utf-8') as f:
                        content = f.read().strip()
                        logger.info(f"Содержимое config.txt: {content}")
                        config_found = True
                        break
                except Exception as e:
                    logger.error(f"Ошибка чтения {config_path}: {e}")
        
        if not config_found:
            logger.warning("config.txt не найден, создаем новый")
            try:
                with open("config.txt", "w", encoding='utf-8') as f:
                    f.write("155.212.171.112")
                logger.info("Создан config.txt с адресом по умолчанию")
            except Exception as e:
                logger.error(f"Ошибка создания config.txt: {e}")
        
        # Импортируем и запускаем приложение
        from app import SabyHelperApp
        
        app = SabyHelperApp(sys.argv)
        logger.info("Приложение SabyHelperApp успешно создано")
        
        return_code = app.exec_()
        logger.info(f"Приложение завершилось с кодом: {return_code}")
        return return_code
        
    except Exception as e:
        logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА ПРИ ЗАПУСКЕ: {e}")
        
        # Показываем ошибку в консоли если приложение не запустилось
        try:
            from PyQt5.QtWidgets import QMessageBox, QApplication
            error_app = QApplication(sys.argv)
            QMessageBox.critical(
                None, 
                "Критическая ошибка запуска", 
                f"Saby Helper не может запуститься:\n\n{str(e)}\n\n"
                f"Убедитесь что все файлы приложения находятся в одной папке."
            )
            return 1
        except:
            print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
            input("Нажмите Enter для выхода...")
            return 1

if __name__ == "__main__":
    sys.exit(main())