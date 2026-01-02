# modules/log_downloader.py
"""
Модуль для выгрузки диагностических логов
"""

import logging
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

class LogDownloader:
    """Класс для загрузки диагностических логов"""
    
    @staticmethod
    def download_logs(incident_number: str, parent=None) -> bool:
        """
        Открытие ссылки для скачивания логов по номеру инцидента
        
        Args:
            incident_number: Номер диагностической карты
            parent: Родительское окно для показа сообщений
        
        Returns:
            bool: True если операция выполнена успешно
        """
        try:
            # Проверяем что номер состоит только из цифр
            if not incident_number.isdigit():
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Ошибка",
                        "Номер диагностической карты должен содержать только цифры!"
                    )
                return False
            
            # Формируем URL
            base_url = "https://cloud.sbis.ru/logreceiver-internal/service/incident"
            download_url = f"{base_url}/{incident_number}/download"
            
            logger.info(f"Открытие ссылки для скачивания логов: {download_url}")
            
            # Открываем в браузере по умолчанию
            QDesktopServices.openUrl(QUrl(download_url))
            
            # Показываем сообщение с инструкцией
            if parent:
                QMessageBox.information(
                    parent,
                    "Ссылка открыта",
                    f"Ссылка для скачивания логов открыта в браузере.\n\n"
                    f"URL: {download_url}\n\n"
                    f"⚠️ Для успешной загрузки убедитесь, что:\n"
                    f"1. Рабочий VPN включен\n"
                    f"2. Вы авторизованы в Cloud в браузере по умолчанию\n"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при открытии ссылки для скачивания логов: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Ошибка",
                    f"Не удалось открыть ссылку для скачивания:\n{str(e)}"
                )
            return False