# payment_terminal_analyzer.py
"""
Анализатор платежных терминалов
"""

import os
import re
import logging
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InpasTransaction:
    """Транзакция терминала INPAS"""
    timestamp: str
    amount: str
    terminal: str
    status: str
    bank: str
    card_type: str
    auth_code: str
    rrn: str
    
    def to_table_row(self) -> List[str]:
        return [
            self.timestamp,
            self.amount,
            self.terminal,
            self.status,
            self.bank,
            self.card_type,
            self.auth_code,
            self.rrn
        ]

@dataclass
class SberbankTransaction:
    """Транзакция терминала Сбербанка"""
    timestamp: str
    amount: str
    status: str
    version: str
    card_last4: str
    guid: str
    department: str
    
    def to_table_row(self) -> List[str]:
        return [
            self.timestamp,
            self.amount,
            self.status,
            self.version,
            self.card_last4,
            self.guid,
            self.department
        ]

@dataclass
class TerminalDriverInfo:
    """Информация о драйвере терминала"""
    driver_name: str
    driver_type: str  # INPAS, SBERBANK, ARCUS2, UNKNOWN
    found: bool
    transactions_count: int
    
    def to_text(self) -> str:
        status = "✅ Найден" if self.found else "❌ Не найден"
        return f"{self.driver_name} ({self.driver_type}): {status}, транзакций: {self.transactions_count}"

class PaymentTerminalAnalyzer:
    """Анализатор платежных терминалов"""
    
    def __init__(self):
        self.temp_dir = None
        self.logger = logging.getLogger(__name__)
    
    def extract_archive(self, archive_path: str) -> Optional[str]:
        """Распаковка архива логов"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="payment_terminal_logs_")
            
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            self.logger.info(f"Архив распакован в: {self.temp_dir}")
            return self.temp_dir
        except Exception as e:
            self.logger.error(f"Ошибка распаковки архива: {e}")
            return None
    
    def find_pts_vendor_directory(self) -> Optional[str]:
        """Поиск директории pts_vendor"""
        if not self.temp_dir:
            return None
        
        pts_path = Path(self.temp_dir) / "pts_vendor"
        
        if pts_path.exists() and pts_path.is_dir():
            self.logger.info(f"Найдена директория pts_vendor: {pts_path}")
            return str(pts_path)
        
        # Также проверим другие возможные пути
        possible_paths = [
            Path(self.temp_dir) / "logs" / "pts_vendor",
            Path(self.temp_dir) / "diagnostics" / "pts_vendor",
            Path(self.temp_dir) / "payment" / "pts_vendor"
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                self.logger.info(f"Найдена директория pts_vendor: {path}")
                return str(path)
        
        self.logger.warning("Директория pts_vendor не найдена")
        return None
    
    def detect_drivers(self, pts_dir: str) -> List[TerminalDriverInfo]:
        """Обнаружение установленных драйверов терминалов"""
        drivers = []
        
        try:
            pts_path = Path(pts_dir)
            
            if not pts_path.exists():
                return [TerminalDriverInfo("pts_vendor", "NOT_FOUND", False, 0)]
            
            # Сканируем поддиректории
            for item in pts_path.iterdir():
                if item.is_dir():
                    driver_name = item.name
                    driver_type = self._classify_driver(driver_name)
                    
                    # Проверяем наличие логов
                    log_count = self._count_logs_in_driver(str(item))
                    
                    driver_info = TerminalDriverInfo(
                        driver_name=driver_name,
                        driver_type=driver_type,
                        found=True,
                        transactions_count=log_count
                    )
                    drivers.append(driver_info)
            
            if not drivers:
                drivers.append(TerminalDriverInfo("Драйверы не найдены", "UNKNOWN", False, 0))
                
        except Exception as e:
            self.logger.error(f"Ошибка обнаружения драйверов: {e}")
            drivers.append(TerminalDriverInfo("Ошибка", "ERROR", False, 0))
        
        return drivers
    
    def _classify_driver(self, driver_name: str) -> str:
        """Классификация драйвера по имени"""
        driver_lower = driver_name.lower()
        
        if 'inpas' in driver_lower:
            return "INPAS"
        elif 'sberbank' in driver_lower or 'sber' in driver_lower:
            return "SBERBANK"
        elif 'sc552' in driver_lower:
            return "SC552"  # Также Сбербанк
        elif 'arcus' in driver_lower:
            return "ARCUS2"
        else:
            return "UNKNOWN"
    
    def _count_logs_in_driver(self, driver_dir: str) -> int:
        """Подсчет лог-файлов в директории драйвера"""
        try:
            count = 0
            driver_path = Path(driver_dir)
            
            for item in driver_path.rglob("*.log"):
                if item.is_file():
                    count += 1
            
            return count
        except:
            return 0
    
    def analyze_inpas_driver(self, driver_dir: str, target_date: str) -> List[InpasTransaction]:
        """Анализ драйвера INPAS"""
        transactions = []
        
        try:
            # Ищем файлы логов INPAS
            log_patterns = [
                f"DualConnector{target_date.replace('-', '')}.log",
                f"DualConnector{target_date[2:].replace('-', '')}.log",  # Без 20 в году
                "DualConnector*.log"
            ]
            
            driver_path = Path(driver_dir)
            log_files = []
            
            for pattern in log_patterns:
                found_files = list(driver_path.rglob(pattern))
                if found_files:
                    log_files.extend(found_files)
                    break
            
            if not log_files:
                # Ищем любые log файлы в директории
                log_files = list(driver_path.rglob("*.log"))
            
            for log_file in log_files:
                self.logger.info(f"Анализ файла INPAS: {log_file}")
                transactions.extend(self._parse_inpas_log(str(log_file), target_date))
                
        except Exception as e:
            self.logger.error(f"Ошибка анализа драйвера INPAS: {e}")
        
        return transactions
    
    def _parse_inpas_log(self, log_path: str, target_date: str) -> List[InpasTransaction]:
        """Парсинг лог-файла INPAS"""
        transactions = []
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Ищем начало транзакции (банковское название)
                if 'ПАО' in line or 'АО' in line or 'БАНК' in line:
                    transaction_data = {}
                    
                    # Собираем данные транзакции
                    transaction_data['bank'] = line.strip()
                    
                    # Следующие строки могут содержать информацию о магазине и т.д.
                    # Пропускаем несколько строк до "ОПЛАТА ПОКУПКИ"
                    for j in range(i, min(i + 15, len(lines))):
                        if 'ОПЛАТА ПОКУПКИ' in lines[j]:
                            # Нашли транзакцию
                            transaction_data['payment_type'] = 'ОПЛАТА ПОКУПКИ'
                            
                            # Ищем статус (обычно на следующей строке)
                            if j + 1 < len(lines):
                                status_line = lines[j + 1].strip()
                                transaction_data['status'] = status_line
                            
                            # Ищем дату и время
                            for k in range(j, min(j + 10, len(lines))):
                                if target_date[:2] in lines[k]:  # Ищем день месяца
                                    date_time_match = re.search(r'(\d{2}\.\d{2}\.\d{2})\s+(\d{2}:\d{2}:\d{2})', lines[k])
                                    if date_time_match:
                                        transaction_data['date'] = date_time_match.group(1)
                                        transaction_data['time'] = date_time_match.group(2)
                                
                                if 'ТЕРМИНАЛ:' in lines[k]:
                                    terminal_match = re.search(r'ТЕРМИНАЛ:\s*(\d+)', lines[k])
                                    if terminal_match:
                                        transaction_data['terminal'] = terminal_match.group(1)
                                
                                if 'КАРТА' in lines[k]:
                                    card_match = re.search(r'КАРТА\s+([A-Za-z ]+)', lines[k])
                                    if card_match:
                                        transaction_data['card_type'] = card_match.group(1).strip()
                                
                                if '**** **** **** ****' in lines[k]:
                                    card_number_match = re.search(r'\*\*\*\*\s+\*\*\*\*\s+\*\*\*\*\s+\*\*\*\*\s+(\d{4})', lines[k])
                                    if card_number_match:
                                        transaction_data['card_last4'] = card_number_match.group(1)
                                
                                if 'СУММА (RUB)' in lines[k]:
                                    amount_match = re.search(r'СУММА \(RUB\)\s+([\d\.]+)', lines[k])
                                    if amount_match:
                                        transaction_data['amount'] = amount_match.group(1)
                                
                                if 'КОД АВТОРИЗАЦИИ:' in lines[k]:
                                    auth_match = re.search(r'КОД АВТОРИЗАЦИИ:\s+(\d+)', lines[k])
                                    if auth_match:
                                        transaction_data['auth_code'] = auth_match.group(1)
                                
                                if '№ ССЫЛКИ:' in lines[k]:
                                    rrn_match = re.search(r'№ ССЫЛКИ:\s+(\d+)', lines[k])
                                    if rrn_match:
                                        transaction_data['rrn'] = rrn_match.group(1)
                            
                            # Если собрали все необходимые данные, создаем транзакцию
                            if all(k in transaction_data for k in ['date', 'time', 'amount', 'terminal', 'status', 'bank']):
                                transaction = InpasTransaction(
                                    timestamp=f"{transaction_data['date']} {transaction_data['time']}",
                                    amount=transaction_data['amount'],
                                    terminal=transaction_data['terminal'],
                                    status=transaction_data['status'],
                                    bank=transaction_data['bank'],
                                    card_type=transaction_data.get('card_type', ''),
                                    auth_code=transaction_data.get('auth_code', ''),
                                    rrn=transaction_data.get('rrn', '')
                                )
                                transactions.append(transaction)
                            
                            break  # Выходим из внутреннего цикла
                    
                    i = j + 10  # Пропускаем обработанные строки
                else:
                    i += 1
                    
        except Exception as e:
            self.logger.error(f"Ошибка парсинга лога INPAS: {e}")
        
        return transactions
    
    def analyze_sberbank_driver(self, driver_dir: str, target_date: str) -> List[SberbankTransaction]:
        """Анализ драйвера Сбербанка (SberbankPilot или SC552)"""
        transactions = []
        
        try:
            driver_path = Path(driver_dir)
            
            # Ищем папки с цифрами (1, 2, 3, 4)
            subdirs = []
            for item in driver_path.iterdir():
                if item.is_dir() and item.name.isdigit():
                    subdirs.append(item)
            
            # Если нет подпапок, используем саму директорию
            if not subdirs:
                subdirs = [driver_path]
            
            for subdir in subdirs:
                # Ищем файлы логов Сбербанка
                log_patterns = [
                    f"sbkernel{target_date[5:7]}{target_date[8:10]}.log",  # MMDD
                    f"sbkernel{target_date[2:4]}{target_date[5:7]}.log",   # YYMM
                    "sbkernel*.log"
                ]
                
                log_files = []
                for pattern in log_patterns:
                    found_files = list(subdir.rglob(pattern))
                    if found_files:
                        log_files.extend(found_files)
                        break
                
                if not log_files:
                    # Ищем любые log файлы
                    log_files = list(subdir.rglob("*.log"))
                
                for log_file in log_files:
                    self.logger.info(f"Анализ файла Сбербанка: {log_file}")
                    transactions.extend(self._parse_sberbank_log(str(log_file), target_date))
                    
        except Exception as e:
            self.logger.error(f"Ошибка анализа драйвера Сбербанка: {e}")
        
        return transactions
    
    def _parse_sberbank_log(self, log_path: str, target_date: str) -> List[SberbankTransaction]:
        """Парсинг лог-файла Сбербанка"""
        transactions = []
        
        try:
            # Конвертируем целевую дату в формат лога (DD.MM)
            target_day_month = f"{target_date[8:10]}.{target_date[5:7]}"
            
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Ищем строку с командой оплаты
                if 'SBKRNL:' in line and 'Command = 4000' in line and target_day_month in line:
                    transaction_data = {}
                    
                    # Извлекаем дату и время
                    time_match = re.search(r'(\d{2}\.\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                    if time_match:
                        transaction_data['date'] = time_match.group(1)
                        transaction_data['time'] = time_match.group(2)
                    
                    # Извлекаем сумму
                    amount_match = re.search(r'Amount\s*=\s*([\d\.]+)', line)
                    if amount_match:
                        transaction_data['amount'] = amount_match.group(1)
                    
                    # Извлекаем отдел
                    dept_match = re.search(r'Department\s*=\s*(\d+)', line)
                    if dept_match:
                        transaction_data['department'] = dept_match.group(1)
                    
                    # Ищем следующие строки для получения дополнительной информации
                    for j in range(i + 1, min(i + 20, len(lines))):
                        next_line = lines[j]
                        
                        # Ищем версию
                        if 'Version:' in next_line and 'MSBuild' not in next_line:
                            version_match = re.search(r'Version:([\d\.]+)', next_line)
                            if version_match:
                                transaction_data['version'] = version_match.group(1)
                        
                        # Ищем результат транзакции
                        if 'Result' in next_line and 'GUID' in next_line:
                            result_match = re.search(r'Result\s*=\s*(\d+)', next_line)
                            if result_match:
                                transaction_data['result_code'] = result_match.group(1)
                                transaction_data['status'] = self._convert_sberbank_result(result_match.group(1))
                            
                            guid_match = re.search(r'GUID=([A-F0-9]+)', next_line)
                            if guid_match:
                                transaction_data['guid'] = guid_match.group(1)
                            
                            card_match = re.search(r'\*\*\*\*\*\*\*\*\*\*\*\*(\d{4})', next_line)
                            if card_match:
                                transaction_data['card_last4'] = card_match.group(1)
                    
                    # Если собрали необходимые данные, создаем транзакцию
                    if all(k in transaction_data for k in ['date', 'time', 'amount', 'status']):
                        transaction = SberbankTransaction(
                            timestamp=f"{transaction_data['date']} {transaction_data['time']}",
                            amount=transaction_data['amount'],
                            status=transaction_data['status'],
                            version=transaction_data.get('version', ''),
                            card_last4=transaction_data.get('card_last4', ''),
                            guid=transaction_data.get('guid', ''),
                            department=transaction_data.get('department', '')
                        )
                        transactions.append(transaction)
                    
                    i = j  # Пропускаем обработанные строки
                else:
                    i += 1
                    
        except Exception as e:
            self.logger.error(f"Ошибка парсинга лога Сбербанка: {e}")
        
        return transactions
    
    def _convert_sberbank_result(self, result_code: str) -> str:
        """Конвертация кода результата Сбербанка в текст"""
        result_map = {
            '0': 'Успешно',
            '99': 'Потеряна связь',
            '2000': 'Отменено пользователем',
            '2001': 'Таймаут',
            '2002': 'Ошибка карты',
            '2003': 'Отказ банка'
        }
        return result_map.get(result_code, f"Код {result_code}")
    
    def format_drivers_result(self, drivers: List[TerminalDriverInfo]) -> str:
        """Форматирование информации о драйверах"""
        if not drivers:
            return "Драйверы терминалов не найдены"
        
        output = "=== ОБНАРУЖЕННЫЕ ДРАЙВЕРЫ ТЕРМИНАЛОВ ===\n\n"
        
        for driver in drivers:
            output += f"• {driver.to_text()}\n"
        
        return output
    
    def format_inpas_result(self, transactions: List[InpasTransaction]) -> str:
        """Форматирование результатов INPAS"""
        if not transactions:
            return "Транзакции INPAS не найдены"
        
        output = f"=== ТРАНЗАКЦИИ INPAS ({len(transactions)}) ===\n\n"
        output += "Дата и время        | Сумма    | Терминал  | Статус    | Банк                 | Тип карты      | Код авторизации | RRN\n"
        output += "-" * 120 + "\n"
        
        for txn in transactions[:100]:  # Ограничиваем вывод
            bank_short = txn.bank[:20] if len(txn.bank) > 20 else txn.bank
            output += f"{txn.timestamp:19} | {txn.amount:8} | {txn.terminal:9} | {txn.status:9} | {bank_short:20} | {txn.card_type:14} | {txn.auth_code:15} | {txn.rrn}\n"
        
        if len(transactions) > 100:
            output += f"\n... и еще {len(transactions) - 100} транзакций\n"
        
        return output
    
    def format_sberbank_result(self, transactions: List[SberbankTransaction]) -> str:
        """Форматирование результатов Сбербанка"""
        if not transactions:
            return "Транзакции Сбербанка не найдены"
        
        output = f"=== ТРАНЗАКЦИИ СБЕРБАНКА ({len(transactions)}) ===\n\n"
        output += "Дата и время        | Сумма    | Статус              | Версия   | Карта | GUID       | Отдел\n"
        output += "-" * 100 + "\n"
        
        for txn in transactions[:100]:  # Ограничиваем вывод
            output += f"{txn.timestamp:19} | {txn.amount:8} | {txn.status:19} | {txn.version:8} | {txn.card_last4:5} | {txn.guid:10} | {txn.department}\n"
        
        if len(transactions) > 100:
            output += f"\n... и еще {len(transactions) - 100} транзакций\n"
        
        return output
    
    def cleanup(self):
        """Очистка временных файлов"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info("Временные файлы анализа платежных терминалов очищены")
            except Exception as e:
                self.logger.error(f"Ошибка очистки временных файлов: {e}")