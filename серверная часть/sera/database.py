import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from pathlib import Path

class LicenseDatabase:
    """База данных для управления лицензиями"""
    
    def __init__(self, db_path: str = "licenses.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица лицензий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS licenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT UNIQUE NOT NULL,
                    hardware_id TEXT,
                    client_name TEXT,
                    email TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    activated_at DATETIME,
                    expires_at DATETIME,
                    is_active BOOLEAN DEFAULT 0,
                    is_blocked BOOLEAN DEFAULT 0,
                    max_activations INTEGER DEFAULT 1,
                    current_activations INTEGER DEFAULT 0,
                    notes TEXT
                )
            ''')
            
            # Таблица активаций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT NOT NULL,
                    hardware_id TEXT NOT NULL,
                    ip_address TEXT,
                    machine_name TEXT,
                    activated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_check DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (license_key) REFERENCES licenses (license_key)
                )
            ''')
            
            # Таблица администраторов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            conn.commit()
        
        self.logger.info("База данных лицензий инициализирована")
    
    def create_license(self, license_key: str, days_valid: int = 365, 
                      max_activations: int = 1, client_name: str = "", 
                      email: str = "", notes: str = "") -> bool:
        """Создание новой лицензии"""
        try:
            expires_at = datetime.now() + timedelta(days=days_valid)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO licenses 
                    (license_key, client_name, email, expires_at, max_activations, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (license_key, client_name, email, expires_at, max_activations, notes))
                conn.commit()
            
            self.logger.info(f"Создана лицензия: {license_key}")
            return True
            
        except sqlite3.IntegrityError:
            self.logger.warning(f"Лицензия уже существует: {license_key}")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка создания лицензии: {e}")
            return False
    
    def activate_license(self, license_key: str, hardware_id: str, 
                        ip_address: str = "", machine_name: str = "") -> Dict:
        """Активация лицензии"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем лицензию
                cursor.execute('''
                    SELECT is_active, is_blocked, expires_at, max_activations, current_activations
                    FROM licenses WHERE license_key = ?
                ''', (license_key,))
                
                result = cursor.fetchone()
                if not result:
                    return {"success": False, "error": "Лицензия не найдена"}
                
                is_active, is_blocked, expires_at, max_activations, current_activations = result
                
                # Проверки
                if is_blocked:
                    return {"success": False, "error": "Лицензия заблокирована"}
                
                if not is_active:
                    return {"success": False, "error": "Лицензия не активна"}
                
                if expires_at and datetime.now() > datetime.fromisoformat(expires_at):
                    return {"success": False, "error": "Срок действия лицензии истек"}
                
                if current_activations >= max_activations:
                    return {"success": False, "error": "Достигнут лимит активаций"}
                
                # Проверяем, не активирована ли уже на этом устройстве
                cursor.execute('''
                    SELECT id FROM activations 
                    WHERE license_key = ? AND hardware_id = ? AND is_active = 1
                ''', (license_key, hardware_id))
                
                if cursor.fetchone():
                    return {"success": False, "error": "Лицензия уже активирована на этом устройстве"}
                
                # Активируем
                cursor.execute('''
                    INSERT INTO activations 
                    (license_key, hardware_id, ip_address, machine_name)
                    VALUES (?, ?, ?, ?)
                ''', (license_key, hardware_id, ip_address, machine_name))
                
                # Обновляем счетчик активаций
                cursor.execute('''
                    UPDATE licenses 
                    SET current_activations = current_activations + 1,
                        activated_at = CURRENT_TIMESTAMP
                    WHERE license_key = ?
                ''', (license_key,))
                
                conn.commit()
                
                self.logger.info(f"Лицензия активирована: {license_key} для {hardware_id}")
                return {"success": True, "message": "Лицензия успешно активирована"}
                
        except Exception as e:
            self.logger.error(f"Ошибка активации лицензии: {e}")
            return {"success": False, "error": f"Ошибка активации: {str(e)}"}
    
    def validate_license(self, license_key: str, hardware_id: str) -> Dict:
        """Проверка валидности лицензии"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем лицензию и активацию
                cursor.execute('''
                    SELECT l.is_active, l.is_blocked, l.expires_at, 
                           a.is_active as activation_active
                    FROM licenses l
                    LEFT JOIN activations a ON l.license_key = a.license_key 
                                           AND a.hardware_id = ?
                    WHERE l.license_key = ?
                ''', (hardware_id, license_key))
                
                result = cursor.fetchone()
                if not result:
                    return {"valid": False, "error": "Лицензия не найдена"}
                
                is_active, is_blocked, expires_at, activation_active = result
                
                # Проверки
                if is_blocked:
                    return {"valid": False, "error": "Лицензия заблокирована"}
                
                if not is_active:
                    return {"valid": False, "error": "Лицензия не активна"}
                
                if expires_at and datetime.now() > datetime.fromisoformat(expires_at):
                    return {"valid": False, "error": "Срок действия лицензии истек"}
                
                if not activation_active:
                    return {"valid": False, "error": "Лицензия не активирована на этом устройстве"}
                
                # Обновляем время последней проверки
                cursor.execute('''
                    UPDATE activations 
                    SET last_check = CURRENT_TIMESTAMP 
                    WHERE license_key = ? AND hardware_id = ?
                ''', (license_key, hardware_id))
                
                conn.commit()
                
                return {"valid": True, "message": "Лицензия действительна"}
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки лицензии: {e}")
            return {"valid": False, "error": f"Ошибка проверки: {str(e)}"}
    
    def get_license_info(self, license_key: str) -> Optional[Dict]:
        """Получение информации о лицензии"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM licenses WHERE license_key = ?
                ''', (license_key,))
                
                license_data = cursor.fetchone()
                if not license_data:
                    return None
                
                # Получаем активации
                cursor.execute('''
                    SELECT * FROM activations 
                    WHERE license_key = ? ORDER BY activated_at DESC
                ''', (license_key,))
                
                activations = [dict(row) for row in cursor.fetchall()]
                
                result = dict(license_data)
                result['activations'] = activations
                
                return result
                
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о лицензии: {e}")
            return None
    
    def get_all_licenses(self) -> List[Dict]:
        """Получение всех лицензий"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT l.*, COUNT(a.id) as activation_count
                    FROM licenses l
                    LEFT JOIN activations a ON l.license_key = a.license_key
                    GROUP BY l.id
                    ORDER BY l.created_at DESC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Ошибка получения списка лицензий: {e}")
            return []
    
    def update_license(self, license_key: str, **kwargs) -> bool:
        """Обновление лицензии"""
        try:
            allowed_fields = ['is_active', 'is_blocked', 'expires_at', 
                            'max_activations', 'client_name', 'email', 'notes']
            
            update_fields = []
            update_values = []
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if not update_fields:
                return False
            
            update_values.append(license_key)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE licenses 
                    SET {', '.join(update_fields)}
                    WHERE license_key = ?
                ''', update_values)
                
                conn.commit()
            
            self.logger.info(f"Лицензия обновлена: {license_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления лицензии: {e}")
            return False
    
    def deactivate_license(self, license_key: str, hardware_id: str = None) -> bool:
        """Деактивация лицензии"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if hardware_id:
                    # Деактивация конкретного устройства
                    cursor.execute('''
                        UPDATE activations 
                        SET is_active = 0 
                        WHERE license_key = ? AND hardware_id = ?
                    ''', (license_key, hardware_id))
                    
                    # Уменьшаем счетчик активаций
                    cursor.execute('''
                        UPDATE licenses 
                        SET current_activations = GREATEST(0, current_activations - 1)
                        WHERE license_key = ?
                    ''', (license_key,))
                else:
                    # Деактивация всех активаций лицензии
                    cursor.execute('''
                        UPDATE activations 
                        SET is_active = 0 
                        WHERE license_key = ?
                    ''', (license_key,))
                    
                    # Сбрасываем счетчик активаций
                    cursor.execute('''
                        UPDATE licenses 
                        SET current_activations = 0
                        WHERE license_key = ?
                    ''', (license_key,))
                
                conn.commit()
            
            self.logger.info(f"Лицензия деактивирована: {license_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка деактивации лицензии: {e}")
            return False