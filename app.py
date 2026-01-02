"""
Основной класс приложения Saby Helper - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""

import sys
import os
import logging
import traceback
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QPainter, QIcon

# Импорт конфигурации
from config import APP_NAME, APP_VERSION, APP_AUTHOR, CONTACT_INFO

logger = logging.getLogger(__name__)

class SabyHelperApp(QApplication):
    """Главный класс приложения Saby Helper - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        try:
            # Настройка приложения
            self.setApplicationName(APP_NAME)
            self.setApplicationVersion(APP_VERSION)
            self.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            self.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
            
            logger.info(f"Инициализация {APP_NAME} v{APP_VERSION}")
            
            # Устанавливаем иконку приложения
            self._set_application_icon()
            
            # Настройка стиля
            self.setStyle('Fusion')
            self._setup_modern_style()
            
            # Показываем простой сплэш-скрин
            splash_shown = self._show_simple_splash_screen()
            
            if splash_shown:
                # Запускаем создание главного окна с задержкой
                QTimer.singleShot(1500, self._create_main_window)
            else:
                # Если сплэш не показался, сразу создаем окно
                self._create_main_window()
            
            logger.info("Приложение Saby Helper успешно инициализировано")
            
        except Exception as e:
            logger.error(f"Критическая ошибка инициализации: {e}")
            logger.error(traceback.format_exc())
            self._show_critical_error("Ошибка инициализации", str(e))
            sys.exit(1)
    
    def _set_application_icon(self):
        """Установка иконки приложения"""
        try:
            # Ищем иконку
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                app_icon = QIcon(str(icon_path))
                self.setWindowIcon(app_icon)
                logger.info(f"Иконка приложения установлена: {icon_path}")
            else:
                logger.warning(f"Файл иконки не найден: {icon_path}")
                # Создаем простую иконку
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor(98, 114, 164))
                
                painter = QPainter(pixmap)
                painter.setPen(QColor(248, 248, 242))
                painter.setFont(QFont("Arial", 16))
                painter.drawText(pixmap.rect(), Qt.AlignCenter, "SH")
                painter.end()
                
                app_icon = QIcon(pixmap)
                self.setWindowIcon(app_icon)
                logger.info("Создана простая иконка приложения")
                
        except Exception as e:
            logger.error(f"Ошибка установки иконки приложения: {e}")
    
    def _show_simple_splash_screen(self):
        """Показ простого загрузочного экрана"""
        try:
            # Создаем сплэш с текстом
            splash_pixmap = QPixmap(400, 200)
            splash_pixmap.fill(QColor(42, 44, 54))
            
            painter = QPainter(splash_pixmap)
            painter.setPen(QColor(248, 248, 242))
            painter.setFont(QFont("Segoe UI", 14, QFont.Bold))
            painter.drawText(splash_pixmap.rect(), Qt.AlignCenter, f"{APP_NAME}\nv{APP_VERSION}\n\nЗагрузка...")
            painter.end()
            
            self.splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
            self.splash.show()
            
            # Обновляем интерфейс
            self.processEvents()
            
            logger.info("Сплэш-скрин показан")
            return True
            
        except Exception as e:
            logger.warning(f"Не удалось показать сплэш-скрин: {e}")
            return False
    
    def _setup_modern_style(self):
        """Настройка современного стиля приложения"""
        try:
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(42, 44, 54))
            palette.setColor(QPalette.WindowText, QColor(248, 248, 242))
            palette.setColor(QPalette.Base, QColor(30, 31, 41))
            palette.setColor(QPalette.AlternateBase, QColor(45, 47, 58))
            palette.setColor(QPalette.ToolTipBase, QColor(248, 248, 242))
            palette.setColor(QPalette.ToolTipText, QColor(30, 31, 41))
            palette.setColor(QPalette.Text, QColor(248, 248, 242))
            palette.setColor(QPalette.Button, QColor(68, 71, 90))
            palette.setColor(QPalette.ButtonText, QColor(248, 248, 242))
            palette.setColor(QPalette.BrightText, QColor(255, 85, 85))
            palette.setColor(QPalette.Highlight, QColor(98, 114, 164))
            palette.setColor(QPalette.HighlightedText, QColor(248, 248, 242))
            
            self.setPalette(palette)
            
            font = QFont("Segoe UI", 10)
            self.setFont(font)
            
            logger.info("Стиль приложения настроен")
            
        except Exception as e:
            logger.error(f"Ошибка настройки стиля: {e}")
    
    def _create_main_window(self):
        """Создание главного окна"""
        try:
            logger.info("Попытка создания главного окна...")
            
            # Закрываем сплэш если он есть
            if hasattr(self, 'splash'):
                self.splash.close()
            
            # Импортируем MainWindow
            from main_window import MainWindow
            
            logger.info("Создание экземпляра MainWindow...")
            self.main_window = MainWindow()
            
            logger.info("Показ главного окна...")
            self.main_window.show()
            
            logger.info("Главное окно успешно создано и показано")
            
        except ImportError as e:
            logger.error(f"Ошибка импорта MainWindow: {e}")
            self._show_critical_error(
                "Ошибка загрузки", 
                f"Не удалось загрузить главное окно:\n{str(e)}\n\n"
                f"Убедитесь, что файл main_window.py находится в папке приложения."
            )
        except Exception as e:
            logger.error(f"Ошибка создания главного окна: {e}")
            logger.error(traceback.format_exc())
            self._show_critical_error(
                "Ошибка запуска", 
                f"Не удалось запустить приложение:\n{str(e)}\n\n"
                f"Для помощи обратитесь к администратору:\n{CONTACT_INFO}"
            )
    
    def _show_critical_error(self, title, message):
        """Показать критическую ошибку"""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
        except:
            # Если даже QMessageBox не работает, просто выводим в консоль
            print(f"КРИТИЧЕСКАЯ ОШИБКА: {title}")
            print(message)