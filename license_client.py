# license_client.py
import requests
import logging
import hashlib
import platform
from datetime import datetime
from PyQt5.QtCore import QSettings

class LicenseClient:
    """Клиент для работы с системой лицензирования"""
    
    def __init__(self, server_url="http://155.212.171.112:5000"):
        self.server_url = server_url
        self.settings = QSettings("SabyHelper", "License")
        self.logger = logging.getLogger(__name__)
        
        # Получаем/генерируем hardware_id
        self.hardware_id = self._get_hardware_id()
        
        # Отключаем прокси для наших запросов
        self.session = requests.Session()
        self.session.trust_env = False
        
        self.logger.info(f"LicenseClient инициализирован")
        self.logger.info(f"Server URL: {self.server_url}")
        self.logger.info(f"Hardware ID: {self.hardware_id}")
    
    def _get_hardware_id(self):
        """Генерация уникального ID оборудования"""
        hardware_id = self.settings.value("hardware_id")
        if not hardware_id:
            system_info = f"{platform.node()}{platform.processor()}{platform.system()}"
            hardware_id = hashlib.sha256(system_info.encode()).hexdigest()[:32]
            self.settings.setValue("hardware_id", hardware_id)
            self.logger.info(f"Сгенерирован hardware_id: {hardware_id}")
        
        return hardware_id
    
    def _get_machine_name(self):
        """Получение имени компьютера"""
        return platform.node()
    
    def _get_ip_address(self):
        """Получение IP адреса"""
        try:
            response = self.session.get('https://api.ipify.org', timeout=5)
            return response.text
        except:
            return "Не удалось определить"
    
    def _format_expires_date(self, expires_at):
        """Форматирование даты истечения срока лицензии - ОБНОВЛЕННАЯ ВЕРСИЯ"""
        if not expires_at or expires_at == "N/A":
            return "Не указан"
        
        try:
            # Проверяем, является ли лицензия бессрочной (> 5 лет)
            expires_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            today = datetime.now()
            
            # Если разница больше 5 лет (1825 дней), считаем бессрочной
            if (expires_date - today).days > 1825:
                return "♾️ Бессрочная"
            else:
                return expires_date.strftime("%d.%m.%Y")
        except:
            return expires_at[:10] if expires_at else "Не указан"
    
    def activate_license(self, license_key, client_name, saby_profile_url=""):
        """Активация лицензии"""
        self.logger.info(f"Попытка активации лицензии: {license_key} для пользователя: {client_name}")
        
        try:
            ip_address = self._get_ip_address()
            machine_name = self._get_machine_name()
            
            request_data = {
                'license_key': license_key,
                'hardware_id': self.hardware_id,
                'client_name': client_name,
                'machine_name': machine_name,
                'saby_profile_url': saby_profile_url
            }
            
            self.logger.info(f"Данные активации: {request_data}")
            
            response = self.session.post(
                f"{self.server_url}/api/activate", 
                json=request_data,
                timeout=30
            )
            
            self.logger.info(f"Ответ сервера: HTTP {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Результат активации: {result}")
                
                if result.get('success'):
                    self.settings.setValue("license_key", license_key)
                    self.settings.setValue("license_activated", True)
                    self.settings.setValue("client_name", client_name)
                    self.logger.info(f"Лицензия активирована: {license_key} для {client_name}")
                    
                    # Логируем успешную активацию
                    self._send_log("INFO", f"Лицензия активирована для пользователя: {client_name}")
                else:
                    self.logger.error(f"Ошибка активации: {result.get('error')}")
                    self._send_log("ERROR", f"Ошибка активации: {result.get('error')}")
                
                return result
            else:
                error_msg = f"HTTP ошибка: {response.status_code}"
                self.logger.error(error_msg)
                self._send_log("ERROR", error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Ошибка сети: {str(e)}"
            self.logger.error(error_msg)
            self._send_log("ERROR", error_msg)
            return {"success": False, "error": error_msg}
    
    def validate_license(self):
        """Проверка текущей лицензии"""
        license_key = self.settings.value("license_key")
        self.logger.info(f"Проверка лицензии: {license_key}")
        
        if not license_key:
            self.logger.warning("Лицензия не активирована")
            self._send_log("WARNING", "Попытка проверки неактивированной лицензии")
            return {"valid": False, "error": "Лицензия не активирована"}
        
        try:
            request_data = {
                'license_key': license_key,
                'hardware_id': self.hardware_id
            }
            
            response = self.session.post(
                f"{self.server_url}/api/validate", 
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Результат проверки: {result}")
                
                if result.get('valid'):
                    self._send_log("INFO", "Проверка лицензии: успешно")
                else:
                    self._send_log("WARNING", f"Проблема с лицензией: {result.get('error')}")
                
                return result
            else:
                error_msg = f"HTTP ошибка при проверке: {response.status_code}"
                self.logger.error(error_msg)
                self._send_log("ERROR", error_msg)
                return {"valid": False, "error": "Ошибка проверки лицензии"}
                
        except Exception as e:
            error_msg = f"Ошибка сети при проверке: {e}"
            self.logger.error(error_msg)
            self._send_log("ERROR", error_msg)
            return {"valid": False, "error": "Не удалось подключиться к серверу лицензий"}
    
    def get_license_info(self):
        """Получение информации о текущей лицензии"""
        license_key = self.settings.value("license_key")
        self.logger.info(f"Запрос информации о лицензии: {license_key}")
        
        if not license_key:
            return None
        
        try:
            response = self.session.post(
                f"{self.server_url}/api/info", 
                json={'license_key': license_key},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info("Получена информация о лицензии")
                
                # Форматируем дату истечения с УЛУЧШЕННОЙ логикой бессрочности
                if 'expires_at' in result:
                    result['formatted_expires_at'] = self._format_expires_date(result['expires_at'])
                
                return result
            else:
                self.logger.warning(f"Не удалось получить информацию: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка получения информации: {e}")
            return None
    
    def get_license_display_info(self):
        """Получение информации о лицензии для отображения в интерфейсе - ОБНОВЛЕННАЯ ВЕРСИЯ"""
        info = self.get_license_info()
        if not info:
            return {
                'status': '❌ Не активирована',
                'status_color': '#ff5555',
                'client_name': 'Не активирована',
                'expires_at': 'Не указан',
                'is_permanent': False
            }
        
        # Определяем статус
        if info.get('is_blocked'):
            status = '🚫 Заблокирована'
            status_color = '#ff5555'
        elif info.get('is_active'):
            status = '✅ Активна'
            status_color = '#50fa7b'
        else:
            status = '❌ Не активна'
            status_color = '#ff5555'
        
        # Форматируем имя клиента
        client_name = info.get('client_name', 'Не указан')
        display_name = client_name.replace("Клиент", "Пользователь").replace("клиент", "пользователь")
        
        # Форматируем дату истечения с учетом бессрочности
        expires_at = info.get('formatted_expires_at', self._format_expires_date(info.get('expires_at')))
        
        return {
            'status': status,
            'status_color': status_color,
            'client_name': display_name,
            'expires_at': expires_at,
            'is_permanent': info.get('is_permanent', False),
            'license_key': info.get('license_key', 'N/A')
        }
    
    def is_license_active(self):
        """Проверка активирована ли лицензия"""
        is_active = self.settings.value("license_activated", False, type=bool)
        self.logger.info(f"Проверка активности лицензии: {is_active}")
        return is_active
    
    def deactivate_license(self):
        """Деактивация лицензии (локально)"""
        self.logger.info("Деактивация лицензии")
        self.settings.remove("license_key")
        self.settings.remove("license_activated")
        self.settings.remove("client_name")
        self._send_log("INFO", "Лицензия деактивирована локально")
        self.logger.info("Лицензия деактивирована локально")
        return True
    
    def _send_log(self, level, message):
        """Отправка лога на сервер"""
        try:
            license_key = self.settings.value("license_key")
            log_data = {
                'license_key': license_key,
                'hardware_id': self.hardware_id,
                'machine_name': self._get_machine_name(),
                'log_level': level,
                'message': message
            }
            
            self.session.post(
                f"{self.server_url}/api/log",
                json=log_data,
                timeout=5
            )
        except Exception as e:
            self.logger.warning(f"Не удалось отправить лог на сервер: {e}")