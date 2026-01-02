# modules/settings_manager.py
"""
Модуль для управления настройками приложения
"""

import logging
from PyQt5.QtCore import QSettings

logger = logging.getLogger(__name__)

class SettingsManager:
    """Менеджер настроек приложения"""
    
    def __init__(self):
        self.settings = QSettings("SabyHelper", "Settings")
        logger.info("Менеджер настроек инициализирован")
    
    def get_auto_update_enabled(self) -> bool:
        """Получить настройку автоматического обновления"""
        return self.settings.value("auto_update_enabled", True, type=bool)
    
    def set_auto_update_enabled(self, enabled: bool):
        """Установить настройку автоматического обновления"""
        self.settings.setValue("auto_update_enabled", enabled)
        logger.info(f"Настройка 'auto_update_enabled' установлена: {enabled}")
    
    def get_last_update_check(self) -> str:
        """Получить дату последней проверки обновлений"""
        return self.settings.value("last_update_check", "")
    
    def set_last_update_check(self, date_str: str):
        """Установить дату последней проверки обновлений"""
        self.settings.setValue("last_update_check", date_str)
    
    def get_update_check_frequency(self) -> int:
        """Получить частоту проверки обновлений (в днях)"""
        return self.settings.value("update_check_frequency", 1, type=int)
    
    def set_update_check_frequency(self, days: int):
        """Установить частоту проверки обновлений"""
        self.settings.setValue("update_check_frequency", days)