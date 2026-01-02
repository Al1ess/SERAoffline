# log_analyzer.py
import os
import zipfile
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
import re

logger = logging.getLogger(__name__)

class LogEntry:
    """Класс для представления записи лога"""
    def __init__(self, timestamp: str, log_type: str, content: str, source_file: str = ""):
        self.timestamp = timestamp
        self.log_type = log_type
        self.content = content
        self.source_file = source_file
    
    def to_table_row(self) -> str:
        """Преобразование в строку таблицы"""
        return f"{self.timestamp} | {self.log_type:8} | {self.content}"
    
    def to_export_row(self) -> str:
        """Преобразование в строку для экспорта"""
        return f"[{self.timestamp}] [{self.log_type}] {self.content}"

class ReceiptOperation:
    """Класс для представления операции с чеком - УЛУЧШЕННАЯ ВЕРСИЯ 1.4.1"""
    def __init__(self, time: str, print_status: str, amount: str, fiscal_type: str, 
                 sale_number: str, operation_type: str, payment_method: str, rnm: str):
        self.time = time
        self.print_status = print_status
        self.amount = amount
        self.fiscal_type = fiscal_type
        self.sale_number = sale_number
        self.operation_type = operation_type
        self.payment_method = payment_method
        self.rnm = rnm
    
    def to_table_row(self) -> List[str]:
        """Преобразование в строку таблицы"""
        return [
            self.time, 
            self.print_status, 
            self.amount, 
            self.fiscal_type,
            self.sale_number,
            self.operation_type,
            self.payment_method,
            self.rnm
        ]
    
    def to_text_row(self) -> str:
        """Преобразование в текстовую строку для экспорта"""
        return f"{self.time} | {self.print_status:12} | {self.amount:10} | {self.fiscal_type:12} | {self.sale_number:8} | {self.operation_type:10} | {self.payment_method:15} | {self.rnm}"

class SupportLogAnalyzer:
    """Анализатор логов поддержки оборудования"""
    
    def __init__(self):
        self.temp_dir = None
        self.logger = logging.getLogger(__name__)
    
    def extract_archive(self, archive_path: str) -> Optional[str]:
        """Распаковка архива логов"""
        try:
            # Создаем временную директорию
            self.temp_dir = tempfile.mkdtemp(prefix="saby_logs_")
            
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            self.logger.info(f"Архив распакован в: {self.temp_dir}")
            return self.temp_dir
        except Exception as e:
            self.logger.error(f"Ошибка распаковки архива: {e}")
            return None
    
    def find_logs_directory(self, date_str: str) -> Optional[str]:
        """Поиск директории с логами за указанную дату"""
        if not self.temp_dir:
            return None
        
        # Форматируем дату в нужный формат (YYYYMMDD)
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            log_date = date_obj.strftime("%Y%m%d")
        except ValueError:
            self.logger.error(f"Неверный формат даты: {date_str}")
            return None
        
        # Основная папка с логами
        logs_path = Path(self.temp_dir) / "logs" / "application_logs"
        
        # Проверяем основную папку
        if logs_path.exists():
            # Ищем папку с нужной датой
            for item in logs_path.iterdir():
                if item.is_dir() and log_date in item.name:
                    return str(item)
        
        # Проверяем архивную папку
        archive_path = logs_path / "archives"
        if archive_path.exists():
            for item in archive_path.iterdir():
                if item.is_dir() and log_date in item.name:
                    return str(item)
        
        self.logger.warning(f"Логов за дату {date_str} не найдено")
        return None
    
    def parse_log_line(self, line: str, source_file: str = "") -> Optional[LogEntry]:
        """Парсинг строки лога и извлечение информации"""
        try:
            line = line.strip()
            if not line:
                return None
            
            # Парсим временную метку (формат: HH:MM:SS.mmm)
            time_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
            timestamp = time_match.group(1) if time_match else "00:00:00.000"
            
            # Определяем тип лога
            log_type = "INFO"
            if 'ERROR' in line.upper():
                log_type = "ERROR"
            elif 'WARNING' in line.upper():
                log_type = "WARNING"
            
            # Извлекаем содержание (убираем временную метку)
            content = line
            if time_match:
                content = line[time_match.end():].strip()
            
            return LogEntry(timestamp, log_type, content, source_file)
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга строки лога: {e}")
            return None
    
    def read_log_entries_from_file(self, file_path: str, log_types: List[str] = None) -> List[LogEntry]:
        """Чтение записей лога из файла с фильтрацией по типам"""
        entries = []
        if log_types is None:
            log_types = ['ERROR', 'WARNING']
        
        try:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        entry = self.parse_log_line(line, filename)
                        if entry and entry.log_type in log_types:
                            entries.append(entry)
                            
                        # Ограничиваем количество для производительности
                        if len(entries) >= 1000:
                            break
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла {file_path}: {e}")
        
        return entries
    
    def find_firmware_version(self, log_dir: str) -> str:
        """Поиск версии прошивки ККТ"""
        firmware_version = "не определена"
        
        # Ищем в файлах Devices-events.log и DevicesOffline-events.log
        event_files = [
            f for f in os.listdir(log_dir) 
            if f.endswith('_Devices-events.log') or f.endswith('_DevicesOffline-events.log')
        ]
        
        for event_file in event_files:
            file_path = os.path.join(log_dir, event_file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        # Ищем FirmwareVersionUnified в строке
                        if '"FirmwareVersionUnified":' in line:
                            # Используем регулярное выражение для извлечения версии
                            match = re.search(r'"FirmwareVersionUnified":"([^"]+)"', line)
                            if match:
                                firmware_version = match.group(1)
                                self.logger.info(f"Найдена версия прошивки: {firmware_version}")
                                return firmware_version
            except Exception as e:
                self.logger.error(f"Ошибка поиска версии прошивки в {event_file}: {e}")
        
        return firmware_version
    
    def _parse_sale_number(self, line: str) -> str:
        """Извлечение номера продажи или возврата из строки лога - ОБНОВЛЕННАЯ ВЕРСИЯ"""
        try:
            # Ищем паттерн "Номер продажи" с ContentRight
            sale_match = re.search(r'"Номер продажи","ContentRight":"(\d+)"', line)
            if sale_match:
                return f"Продажа: {sale_match.group(1)}"
            
            # Ищем паттерн "Номер возврата" с ContentRight
            return_match = re.search(r'"Номер возврата","ContentRight":"(\d+)"', line)
            if return_match:
                return f"Возврат: {return_match.group(1)}"
            
            # Альтернативный поиск по SaleNumber
            sale_match_alt = re.search(r'"SaleNumber":(\d+)', line)
            if sale_match_alt:
                return f"Продажа: {sale_match_alt.group(1)}"
            
            # Альтернативный поиск по ReturnNumber
            return_match_alt = re.search(r'"ReturnNumber":(\d+)', line)
            if return_match_alt:
                return f"Возврат: {return_match_alt.group(1)}"
                
            return "не определен"
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга номера продажи/возврата: {e}")
            return "ошибка"
    
    def _parse_operation_type(self, line: str) -> str:
        """Определение типа операции - ОБНОВЛЕННАЯ ВЕРСИЯ"""
        try:
            doc_type_match = re.search(r'"DocumentType":(\d+)', line)
            if doc_type_match:
                doc_type = doc_type_match.group(1)
                if doc_type == "8":
                    return "Приход"
                elif doc_type == "9":
                    return "Возврат"
                else:
                    return f"Другое({doc_type})"
            
            # Дополнительная проверка по наличию номера возврата в тексте
            if '"Номер возврата"' in line:
                return "Возврат"
            elif '"Номер продажи"' in line:
                return "Приход"
                
            return "не определен"
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга типа операции: {e}")
            return "ошибка"
    
    def _parse_payment_method(self, line: str) -> str:
        """Определение способа оплаты"""
        try:
            # Ищем сумму по карте
            bank_card_match = re.search(r'"BankCardSum":(\d+\.?\d*)', line)
            bank_card_sum = float(bank_card_match.group(1)) if bank_card_match else 0.0
            
            # Ищем общую сумму
            total_sum_match = re.search(r'"TotalSum":(\d+\.?\d*)', line)
            total_sum = float(total_sum_match.group(1)) if total_sum_match else 0.0
            
            if total_sum == 0:
                return "Не удалось определить"
            
            if bank_card_sum == 0:
                return "Наличными"
            elif bank_card_sum == total_sum:
                return "Безналичными"
            else:
                return "Смешанная"
                
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга способа оплаты: {e}")
            return "Не удалось определить"
    
    def _parse_rnm(self, line: str) -> str:
        """Извлечение РНМ из строки лога"""
        try:
            rnm_match = re.search(r'"kkm_reg_number":"([^"]+)"', line)
            if rnm_match:
                return rnm_match.group(1)
            return "не определен"
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга РНМ: {e}")
            return "ошибка"
    
    def analyze_receipt_operations(self, log_dir: str) -> List[ReceiptOperation]:
        """Анализ операций с чеками - УЛУЧШЕННАЯ ВЕРСИЯ 1.4.1"""
        operations = []
        
        # Ищем в файлах Devices-events.log и DevicesOffline-events.log
        event_files = [
            f for f in os.listdir(log_dir) 
            if f.endswith('_Devices-events.log') or f.endswith('_DevicesOffline-events.log')
        ]
        
        for event_file in event_files:
            file_path = os.path.join(log_dir, event_file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if "Builded receipt" in line:
                            # Извлекаем время из начала строки
                            time_match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                            time_part = time_match.group(1) if time_match else "неизвестное время"
                            
                            # Ищем PrintMode
                            print_mode_match = re.search(r'"PrintMode":(\d)', line)
                            print_mode = print_mode_match.group(1) if print_mode_match else "не определен"
                            
                            # Ищем TotalSum
                            total_sum_match = re.search(r'"TotalSum":(\d+)', line)
                            if total_sum_match:
                                total_sum = int(total_sum_match.group(1))
                                sum_text = f"{total_sum} руб."
                            else:
                                sum_text = "не определена"
                            
                            # Ищем non_fiscal
                            non_fiscal_match = re.search(r'"non_fiscal":(true|false)', line, re.IGNORECASE)
                            if non_fiscal_match:
                                non_fiscal_value = non_fiscal_match.group(1).lower()
                                fiscal_text = "нефискальный" if non_fiscal_value == "true" else "фискальный"
                            else:
                                fiscal_text = "не определен"
                            
                            # Определяем статус печати
                            if print_mode in ['0', '2']:
                                status = "Печатать"
                            elif print_mode in ['4', '6']:
                                status = "Не печатать"
                            else:
                                status = f"неизвестный ({print_mode})"
                            
                            # НОВЫЕ ПОЛЯ версия 1.4.1
                            sale_number = self._parse_sale_number(line)
                            operation_type = self._parse_operation_type(line)
                            payment_method = self._parse_payment_method(line)
                            rnm = self._parse_rnm(line)
                            
                            # Создаем объект операции
                            operation = ReceiptOperation(
                                time_part, status, sum_text, fiscal_text,
                                sale_number, operation_type, payment_method, rnm
                            )
                            operations.append(operation)
            except Exception as e:
                self.logger.error(f"Ошибка анализа операций в {event_file}: {e}")
        
        return operations
    
    def general_analysis(self, log_dir: str, include_warnings: bool = False) -> Dict:
        """Общий анализ логов с расширенным поиском файлов"""
        result = {
            'firmware_version': '',
            'log_entries': [],
            'summary': {}
        }
        
        # Добавляем версию прошивки
        firmware_version = self.find_firmware_version(log_dir)
        result['firmware_version'] = firmware_version
        
        # Определяем типы логов для поиска
        log_types = ['ERROR']
        if include_warnings:
            log_types.append('WARNING')
        
        # РАСШИРЕННЫЙ ПОИСК ФАЙЛОВ - включаем все типы файлов с ошибками
        error_file_patterns = [
            '*_DevicesOffline-errors.log',
            '*_PaymentTerminalOfflineRu-errors.log', 
            '*_Devices-errors.log',
            '*_PaymentTerminalPluginRu-errors.log'
        ]
        
        event_file_patterns = [
            '*_Devices-events.log',
            '*_DevicesOffline-events.log'
        ]
        
        all_entries = []
        
        # Ищем файлы с ошибками по всем шаблонам
        for pattern in error_file_patterns:
            for file_path in Path(log_dir).glob(pattern):
                entries = self.read_log_entries_from_file(str(file_path), log_types)
                all_entries.extend(entries)
                self.logger.info(f"Найдено {len(entries)} записей в {file_path.name}")
        
        # Ищем в event файлах если включены предупреждения
        if include_warnings:
            for pattern in event_file_patterns:
                for file_path in Path(log_dir).glob(pattern):
                    entries = self.read_log_entries_from_file(str(file_path), ['WARNING'])
                    all_entries.extend(entries)
                    self.logger.info(f"Найдено {len(entries)} предупреждений в {file_path.name}")
        
        # Сортируем записи по времени
        all_entries.sort(key=lambda x: x.timestamp)
        result['log_entries'] = all_entries
        
        # Статистика
        error_count = len([e for e in all_entries if e.log_type == 'ERROR'])
        warning_count = len([e for e in all_entries if e.log_type == 'WARNING'])
        
        result['summary'] = {
            'total_entries': len(all_entries),
            'errors': error_count,
            'warnings': warning_count,
            'files_scanned': len(error_file_patterns) + (len(event_file_patterns) if include_warnings else 0)
        }
        
        return result
    
    def format_general_analysis_result(self, analysis_result: Dict) -> str:
        """Форматирование результата общего анализа"""
        result_lines = []
        
        # Заголовок и версия прошивки
        result_lines.append(f"ПО ККТ: \"{analysis_result['firmware_version']}\"")
        result_lines.append("")
        
        # Статистика
        summary = analysis_result['summary']
        result_lines.append("=== СТАТИСТИКА АНАЛИЗА ===")
        result_lines.append(f"• Всего записей: {summary['total_entries']}")
        result_lines.append(f"• Ошибок: {summary['errors']}")
        result_lines.append(f"• Предупреждений: {summary['warnings']}")
        result_lines.append(f"• Просканировано файлов: {summary['files_scanned']}")
        result_lines.append("")
        
        # Таблица логов с временем, типом и содержанием
        if analysis_result['log_entries']:
            result_lines.append("=== ТАБЛИЦА ЛОГОВ ===")
            result_lines.append("Время       | Тип     | Содержание")
            result_lines.append("-" * 80)
            
            for entry in analysis_result['log_entries'][:100]:  # Ограничиваем вывод
                result_lines.append(entry.to_table_row())
            
            if len(analysis_result['log_entries']) > 100:
                result_lines.append(f"... и еще {len(analysis_result['log_entries']) - 100} записей")
        else:
            result_lines.append("Записей логов не найдено")
        
        return "\n".join(result_lines)
    
    def export_analysis_to_txt(self, analysis_result: Dict, file_path: str) -> bool:
        """Экспорт результатов анализа в TXT файл"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Заголовок
                f.write("=" * 60 + "\n")
                f.write("АНАЛИЗ ЛОГОВ SABY HELPER v1.4.1\n")
                f.write("=" * 60 + "\n\n")
                
                # Информация о системе
                f.write(f"Версия прошивки ККТ: {analysis_result['firmware_version']}\n")
                f.write(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Статистика
                summary = analysis_result['summary']
                f.write("СТАТИСТИКА:\n")
                f.write(f"- Всего записей: {summary['total_entries']}\n")
                f.write(f"- Ошибок: {summary['errors']}\n")
                f.write(f"- Предупреждений: {summary['warnings']}\n")
                f.write(f"- Файлов просканировано: {summary['files_scanned']}\n\n")
                
                # Детальные логи
                if analysis_result['log_entries']:
                    f.write("ДЕТАЛЬНЫЕ ЛОГИ:\n")
                    f.write("=" * 80 + "\n")
                    
                    for entry in analysis_result['log_entries']:
                        f.write(entry.to_export_row() + "\n")
                else:
                    f.write("Записей логов не найдено.\n")
            
            self.logger.info(f"Результаты экспортированы в: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта в TXT: {e}")
            return False
    
    def receipt_analysis(self, log_dir: str) -> Dict:
        """Анализ операций с чеками - УЛУЧШЕННАЯ ВЕРСИЯ 1.4.1"""
        operations = self.analyze_receipt_operations(log_dir)
        
        result = {
            'operations': operations,
            'total_count': len(operations)
        }
        
        return result
    
    def format_receipt_analysis_result(self, analysis_result: Dict) -> str:
        """Форматирование результата анализа операций для текстового отображения"""
        operations = analysis_result['operations']
        
        if operations:
            result_lines = [
                "=== ОПЕРАЦИИ С ЧЕКАМИ ===",
                ""
            ]
            
            # Заголовок таблицы
            result_lines.append("Время       | Статус печати  | Сумма       | Тип чека     | № операции | Тип опер. | Способ оплаты   | РНМ")
            result_lines.append("-" * 120)
            
            # Данные операций
            for operation in operations:
                result_lines.append(operation.to_text_row())
            
            # Итоговая статистика
            sale_count = len([op for op in operations if "Продажа:" in op.sale_number])
            return_count = len([op for op in operations if "Возврат:" in op.sale_number])
            unknown_count = len([op for op in operations if "не определен" in op.sale_number])
            
            result_lines.append("")
            result_lines.append(f"Количество операций: {analysis_result['total_count']} (Продажи: {sale_count}, Возвраты: {return_count}")
            if unknown_count > 0:
                result_lines[-1] += f", Не определено: {unknown_count}"
            result_lines[-1] += ")"
            
        else:
            result_lines = ["Операций с чеками не найдено"]
        
        return "\n".join(result_lines)
    
    def cleanup(self):
        """Очистка временных файлов"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info("Временные файлы очищены")
            except Exception as e:
                self.logger.error(f"Ошибка очистки временных файлов: {e}")