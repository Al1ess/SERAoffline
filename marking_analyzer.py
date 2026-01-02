# marking_analyzer.py
"""
Анализатор логов маркировки - ИСПРАВЛЕННАЯ ВЕРСИЯ БЕЗ ТЕКСТОВЫХ РЕЗУЛЬТАТОВ
"""

import os
import re
import json
import base64
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MarkingScanResult:
    """Результат сканирования КМ"""
    def __init__(self, timestamp: str, result: str, source_file: str = ""):
        self.timestamp = timestamp
        self.result = result
        self.source_file = source_file
    
    def to_table_row(self) -> List[str]:
        return [self.timestamp, self.result]

class MarkingInfoResult:
    """Информация о КМ"""
    def __init__(self, timestamp: str, cis: str, realizable: bool, sold: bool, 
                 sold_unit_count: Optional[int], inner_unit_count: Optional[int],
                 expire_date: Optional[str], is_owner: bool, is_tracking: bool,
                 source_file: str = ""):
        self.timestamp = timestamp
        self.cis = cis
        self.realizable = realizable
        self.sold = sold
        self.sold_unit_count = sold_unit_count
        self.inner_unit_count = inner_unit_count
        self.expire_date = expire_date
        self.is_owner = is_owner
        self.is_tracking = is_tracking
        self.source_file = source_file
    
    def to_table_row(self) -> List[str]:
        return [
            self.timestamp,
            self.cis,
            "Выведен" if not self.realizable else "В обороте",
            "Продан" if self.sold else "Не продан",
            str(self.sold_unit_count) if self.sold_unit_count else "Н/Д",
            str(self.inner_unit_count) if self.inner_unit_count else "Н/Д",
            self.expire_date.split('T')[0] if self.expire_date else "Н/Д",
            "Да" if self.is_owner else "Нет",
            "Да" if self.is_tracking else "Нет"
        ]

class ConnectionIssueResult:
    """Проблемы подключения ЛМ ЧЗ"""
    def __init__(self, timestamp: str, message: str, source_file: str = ""):
        self.timestamp = timestamp
        self.message = message
        self.source_file = source_file
    
    def to_table_row(self) -> List[str]:
        return [self.timestamp, self.message]

class LoginPasswordResult:
    """Логин и пароль ЛМ ЧЗ"""
    def __init__(self, timestamp: str, encoded_auth: str, decoded_auth: str, source_file: str = ""):
        self.timestamp = timestamp
        self.encoded_auth = encoded_auth
        self.decoded_auth = decoded_auth
        self.source_file = source_file
    
    def to_text_row(self) -> str:
        return f"{self.timestamp} | Закодировано: {self.encoded_auth} | Раскодировано: {self.decoded_auth}"

class OpeningCheckResult:
    """Результат проверки вскрытия"""
    def __init__(self, timestamp: str, cis: str, quantity: float, 
                 expiration_date: Optional[str], connection_date: str, source_file: str = ""):
        self.timestamp = timestamp
        self.cis = cis
        self.quantity = quantity
        self.expiration_date = expiration_date
        self.connection_date = connection_date
        self.source_file = source_file
    
    def to_table_row(self) -> List[str]:
        return [
            self.timestamp,
            self.cis,
            f"{self.quantity} л",
            self.expiration_date.split(' ')[0] if self.expiration_date else "Не получен",
            self.connection_date.split(' ')[0] if self.connection_date else "Н/Д"
        ]

class MarkingLogAnalyzer:
    """Анализатор логов маркировки"""
    
    def __init__(self):
        self.temp_dir = None
        self.logger = logging.getLogger(__name__)
    
    def extract_archive(self, archive_path: str) -> Optional[str]:
        """Распаковка архива логов"""
        try:
            import zipfile
            import tempfile
            
            self.temp_dir = tempfile.mkdtemp(prefix="marking_logs_")
            
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            self.logger.info(f"Архив маркировки распакован в: {self.temp_dir}")
            return self.temp_dir
        except Exception as e:
            self.logger.error(f"Ошибка распаковки архива маркировки: {e}")
            return None
    
    def find_logs_directory(self, date_str: str) -> Optional[str]:
        """Поиск директории с логами за указанную дату"""
        if not self.temp_dir:
            return None
        
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            log_date = date_obj.strftime("%Y%m%d")
        except ValueError:
            self.logger.error(f"Неверный формат даты: {date_str}")
            return None
        
        logs_path = Path(self.temp_dir) / "logs" / "application_logs"
        
        if logs_path.exists():
            for item in logs_path.iterdir():
                if item.is_dir() and log_date in item.name:
                    return str(item)
        
        archive_path = logs_path / "archives"
        if archive_path.exists():
            for item in archive_path.iterdir():
                if item.is_dir() and log_date in item.name:
                    return str(item)
        
        self.logger.warning(f"Логов маркировки за дату {date_str} не найдено")
        return None
    
    def analyze_all_scans_devices(self, log_dir: str) -> List[MarkingScanResult]:
        """Анализ всех сканирований - принцип Devices"""
        results = []
        
        event_files = [
            f for f in os.listdir(log_dir) 
            if f.endswith('_Devices-events.log') or f.endswith('_DevicesOffline-events.log')
        ]
        
        for event_file in event_files:
            file_path = os.path.join(log_dir, event_file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if "From the scanner the code is read:" in line:
                            time_match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                            timestamp = time_match.group(1) if time_match else "неизвестное время"
                            
                            code_match = re.search(r'From the scanner the code is read:\s*([^\s]+)', line)
                            if code_match:
                                result = code_match.group(1).strip()
                                if result and result != ":":
                                    scan_result = MarkingScanResult(timestamp, result, event_file)
                                    results.append(scan_result)
            except Exception as e:
                self.logger.error(f"Ошибка анализа сканирований в {event_file}: {e}")
        
        return results
    
    def analyze_all_scans_console(self, log_dir: str) -> List[MarkingScanResult]:
        """Анализ всех сканирований - принцип Console"""
        results = []
        
        console_files = [f for f in os.listdir(log_dir) if f.endswith('_UI-console.log')]
        
        for console_file in console_files:
            file_path = os.path.join(log_dir, console_file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if "Событие от сканера -" in line:
                            time_match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                            timestamp = time_match.group(1) if time_match else "неизвестное время"
                            
                            code_match = re.search(r'Событие от сканера -\s*([^\s]+)', line)
                            if code_match:
                                result = code_match.group(1).strip()
                                if result and result != "-":
                                    scan_result = MarkingScanResult(timestamp, result, console_file)
                                    results.append(scan_result)
            except Exception as e:
                self.logger.error(f"Ошибка анализа сканирований в {console_file}: {e}")
        
        return results
    
    def analyze_marking_info(self, log_dir: str) -> List[MarkingInfoResult]:
        """Анализ информации по КМ"""
        results = []
        
        event_files = [
            f for f in os.listdir(log_dir) 
            if f.endswith('_Devices-events.log') or f.endswith('_DevicesOffline-events.log')
        ]
        
        for event_file in event_files:
            file_path = os.path.join(log_dir, event_file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if '[PCC|OnlineModule] Result native: Http code: 200' in line:
                            time_match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                            timestamp = time_match.group(1) if time_match else "неизвестное время"
                            
                            try:
                                # Ищем JSON в Response
                                json_match = re.search(r'Response:\s*({.*?})$', line)
                                if json_match:
                                    json_str = json_match.group(1)
                                    data = json.loads(json_str)
                                    
                                    # Извлекаем данные из codes[0]
                                    if 'codes' in data and data['codes'] and len(data['codes']) > 0:
                                        code_data = data['codes'][0]
                                        
                                        cis = code_data.get('cis', '')
                                        realizable = code_data.get('realizable', False)
                                        sold = code_data.get('sold', False)
                                        sold_unit_count = code_data.get('soldUnitCount')
                                        inner_unit_count = code_data.get('innerUnitCount')
                                        expire_date = code_data.get('expireDate')
                                        is_owner = code_data.get('isOwner', False)
                                        is_tracking = code_data.get('isTracking', False)
                                        
                                        if cis:
                                            info_result = MarkingInfoResult(
                                                timestamp, cis, realizable, sold, sold_unit_count,
                                                inner_unit_count, expire_date, is_owner, is_tracking,
                                                event_file
                                            )
                                            results.append(info_result)
                                            self.logger.info(f"Найдена информация по КМ: {cis}")
                            except (json.JSONDecodeError, KeyError, IndexError) as e:
                                self.logger.warning(f"Ошибка парсинга JSON в строке: {e}")
                                continue
            except Exception as e:
                self.logger.error(f"Ошибка анализа информации КМ в {event_file}: {e}")
        
        return results
    
    def analyze_connection_issues(self, log_dir: str) -> List[ConnectionIssueResult]:
        """Анализ проблем подключения ЛМ ЧЗ"""
        results = []
        
        event_files = [
            f for f in os.listdir(log_dir) 
            if f.endswith('_Devices-events.log') or f.endswith('_DevicesOffline-events.log')
        ]
        
        for event_file in event_files:
            file_path = os.path.join(log_dir, event_file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if "Нет подключения к локальному модулю" in line:
                            time_match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                            timestamp = time_match.group(1) if time_match else "неизвестное время"
                            
                            connection_result = ConnectionIssueResult(timestamp, "Нет подключения к локальному модулю", event_file)
                            results.append(connection_result)
            except Exception as e:
                self.logger.error(f"Ошибка анализа подключений в {event_file}: {e}")
        
        return results
    
    def analyze_login_password(self, log_dir: str) -> List[LoginPasswordResult]:
        """Анализ логина и пароля ЛМ ЧЗ"""
        results = []
        seen_auths = set()
        
        event_files = [
            f for f in os.listdir(log_dir) 
            if f.endswith('_Devices-events.log') or f.endswith('_DevicesOffline-events.log')
        ]
        
        for event_file in event_files:
            file_path = os.path.join(log_dir, event_file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        auth_match = re.search(r'AUTHORIZATION:\s*Basic\s*([a-zA-Z0-9+/=]+)', line)
                        if auth_match:
                            time_match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                            timestamp = time_match.group(1) if time_match else "неизвестное время"
                            
                            encoded_auth = auth_match.group(1)
                            
                            try:
                                decoded_bytes = base64.b64decode(encoded_auth)
                                decoded_auth = decoded_bytes.decode('utf-8')
                            except Exception as e:
                                decoded_auth = f"Ошибка декодирования: {e}"
                            
                            if encoded_auth not in seen_auths:
                                seen_auths.add(encoded_auth)
                                login_result = LoginPasswordResult(timestamp, encoded_auth, decoded_auth, event_file)
                                results.append(login_result)
            except Exception as e:
                self.logger.error(f"Ошибка анализа логинов в {event_file}: {e}")
        
        return results
    
    def analyze_opening_check(self, log_dir: str) -> List[OpeningCheckResult]:
        """Анализ проверки вскрытия"""
        results = []
        
        service_files = [f for f in os.listdir(log_dir) if f.startswith('202') and '_MainService-events' in f]
        
        for service_file in service_files:
            file_path = os.path.join(log_dir, service_file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if 'RetailOpeningBuffer.Insert/1(' in line and 'SerialNumber' in line:
                            time_match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                            timestamp = time_match.group(1) if time_match else "неизвестное время"
                            
                            try:
                                json_match = re.search(r'RetailOpeningBuffer\.Insert/1\(({.*?})\);\)', line)
                                if json_match:
                                    json_str = json_match.group(1)
                                    data = json.loads(json_str)
                                    
                                    d_data = data.get('d', [])
                                    if len(d_data) >= 9:
                                        cis = d_data[3] if len(d_data) > 3 else ""
                                        quantity = d_data[4] if len(d_data) > 4 else 0.0
                                        expiration_date = d_data[7] if len(d_data) > 7 else None
                                        connection_date = d_data[8] if len(d_data) > 8 else ""
                                        
                                        if cis and cis != "null":
                                            opening_result = OpeningCheckResult(
                                                timestamp, cis, quantity, expiration_date, connection_date, service_file
                                            )
                                            results.append(opening_result)
                            except (json.JSONDecodeError, KeyError, IndexError) as e:
                                self.logger.warning(f"Ошибка парсинга данных вскрытия: {e}")
                                continue
            except Exception as e:
                self.logger.error(f"Ошибка анализа вскрытия в {service_file}: {e}")
        
        return results
    
    def get_original_logs(self, log_dir: str) -> Dict[str, str]:
        """Получение оригинальных логов"""
        original_logs = {}
        
        log_files = [
            f for f in os.listdir(log_dir) 
            if any(f.endswith(ext) for ext in [
                '_Devices-events.log', '_DevicesOffline-events.log', 
                '_MainService-events.log', '_UI-console.log'
            ])
        ]
        
        for log_file in log_files:
            file_path = os.path.join(log_dir, log_file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    original_logs[log_file] = content
            except Exception as e:
                self.logger.error(f"Ошибка чтения оригинального лога {log_file}: {e}")
                original_logs[log_file] = f"Ошибка чтения файла: {e}"
        
        return original_logs
    
    def format_scans_result(self, results: List[MarkingScanResult]) -> str:
        """Форматирование результатов сканирований - ТОЛЬКО ДЛЯ ЭКСПОРТА"""
        if not results:
            return "Сканирований не найдено"
        
        output = f"Найдено сканирований: {len(results)}\n\n"
        output += "Время       | Результат\n"
        output += "-" * 50 + "\n"
        
        for result in results[:100]:
            output += f"{result.timestamp} | {result.result}\n"
        
        if len(results) > 100:
            output += f"\n... и еще {len(results) - 100} записей"
        
        return output
    
    def format_marking_info_result(self, results: List[MarkingInfoResult]) -> str:
        """Форматирование информации по КМ - ТОЛЬКО ДЛЯ ЭКСПОРТА"""
        if not results:
            return "Информации по КМ не найдено"
        
        output = f"Найдено записей информации по КМ: {len(results)}\n\n"
        output += "Время       | КМ | Статус | Продажа | Продано | Всего | Срок годности | Владелец | Прослеживаемость\n"
        output += "-" * 120 + "\n"
        
        for result in results[:50]:
            output += f"{result.timestamp} | {result.cis[:15]}... | {'Выведен' if not result.realizable else 'В обороте'} | "
            output += f"{'Продан' if result.sold else 'Не продан'} | "
            output += f"{result.sold_unit_count or 'Н/Д'} | {result.inner_unit_count or 'Н/Д'} | "
            output += f"{(result.expire_date or 'Н/Д')[:10]} | {'Да' if result.is_owner else 'Нет'} | {'Да' if result.is_tracking else 'Нет'}\n"
        
        if len(results) > 50:
            output += f"\n... и еще {len(results) - 50} записей"
        
        return output
    
    def format_connection_issues_result(self, results: List[ConnectionIssueResult]) -> str:
        """Форматирование проблем подключения - ТОЛЬКО ДЛЯ ЭКСПОРТА"""
        if not results:
            return "Проблем подключения не найдено"
        
        output = f"Найдено проблем подключения: {len(results)}\n\n"
        output += "Время       | Сообщение\n"
        output += "-" * 80 + "\n"
        
        for result in results[:100]:
            output += f"{result.timestamp} | {result.message}\n"
        
        if len(results) > 100:
            output += f"\n... и еще {len(results) - 100} записей"
        
        return output
    
    def format_login_password_result(self, results: List[LoginPasswordResult]) -> str:
        """Форматирование логинов и паролей"""
        if not results:
            return "Данных авторизации не найдено"
        
        output = f"Найдено уникальных авторизаций: {len(results)}\n\n"
        output += "Время       | Закодированные данные | Раскодированные данные\n"
        output += "-" * 100 + "\n"
        
        for result in results:
            output += f"{result.timestamp} | {result.encoded_auth} | {result.decoded_auth}\n"
        
        return output
    
    def format_opening_check_result(self, results: List[OpeningCheckResult]) -> str:
        """Форматирование проверки вскрытия - ТОЛЬКО ДЛЯ ЭКСПОРТА"""
        if not results:
            return "Данных вскрытия не найдено"
        
        output = f"Найдено записей вскрытия: {len(results)}\n\n"
        output += "Время       | КМ | Литраж | Срок годности | Дата вскрытия\n"
        output += "-" * 80 + "\n"
        
        for result in results[:100]:
            output += f"{result.timestamp} | {result.cis[:20]}... | {result.quantity} л | "
            output += f"{(result.expiration_date or 'Не получен')[:10]} | {(result.connection_date or 'Н/Д')[:10]}\n"
        
        if len(results) > 100:
            output += f"\n... и еще {len(results) - 100} записей"
        
        return output
    
    def cleanup(self):
        """Очистка временных файлов"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info("Временные файлы маркировки очищены")
            except Exception as e:
                self.logger.error(f"Ошибка очистки временных файлов маркировки: {e}")