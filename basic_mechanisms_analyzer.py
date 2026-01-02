# basic_mechanisms_analyzer.py
"""
Анализатор базовых механизмов (журналы ОС Windows) - УЛУЧШЕННАЯ ВЕРСИЯ
"""

import os
import re
import logging
import tempfile
import zipfile
import struct
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import xml.etree.ElementTree as ET
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OSEvent:
    """Событие ОС Windows"""
    timestamp: str
    level: str  # Ошибка, Критическое, Предупреждение, Информация
    event_code: str
    source: str
    description: str
    log_type: str  # Application или System
    
    def to_table_row(self) -> List[str]:
        """Преобразование в строку таблицы"""
        return [
            self.timestamp,
            self.level,
            self.event_code,
            self.source,
            self.log_type
        ]

class BasicMechanismsAnalyzer:
    """Анализатор базовых механизмов (журналы ОС Windows)"""
    
    def __init__(self):
        self.temp_dir = None
        self.logger = logging.getLogger(__name__)
        
        # Коды событий по умолчанию
        self.default_patterns = ["41", "55", "98", "7031", "7001", "7000"]
        self.custom_patterns = []
        self.use_custom_patterns = False
        
        # Попробуем импортировать evtx если установлен
        self.has_evtx = False
        try:
            import Evtx.Evtx as evtx
            self.has_evtx = True
            self.logger.info("Библиотека evtx доступна для парсинга бинарных EVTX")
        except ImportError:
            self.logger.warning("Библиотека evtx не установлена, будет использован упрощенный парсинг")
    
    def set_custom_patterns(self, patterns_str: str):
        """Установка пользовательских шаблонов"""
        patterns = [p.strip() for p in patterns_str.split(',')]
        self.custom_patterns = patterns
        self.logger.info(f"Установлены пользовательские шаблоны: {patterns}")
    
    def set_use_custom_patterns(self, use_custom: bool):
        """Использовать ли пользовательские шаблоны"""
        self.use_custom_patterns = use_custom
        self.logger.info(f"Использование пользовательских шаблонов: {use_custom}")
    
    def extract_archive(self, archive_path: str) -> Optional[str]:
        """Распаковка архива логов"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="basic_mech_logs_")
            
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            self.logger.info(f"Архив распакован в: {self.temp_dir}")
            return self.temp_dir
        except Exception as e:
            self.logger.error(f"Ошибка распаковки архива: {e}")
            return None
    
    def find_system_info_directory(self) -> Optional[str]:
        """Поиск директории system_info"""
        if not self.temp_dir:
            return None
        
        system_info_path = Path(self.temp_dir) / "system_info"
        
        if system_info_path.exists() and system_info_path.is_dir():
            self.logger.info(f"Найдена директория system_info: {system_info_path}")
            return str(system_info_path)
        
        # Также проверим возможные другие пути
        possible_paths = [
            Path(self.temp_dir) / "logs" / "system_info",
            Path(self.temp_dir) / "diagnostics" / "system_info",
            Path(self.temp_dir) / "diagnostic_info" / "system_info",
            Path(self.temp_dir) / "system" / "info",
            Path(self.temp_dir)  # Также проверим корень
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                # Ищем файлы журналов в этой директории
                evtx_files = list(path.rglob("*.evtx"))
                if evtx_files:
                    self.logger.info(f"Найдена директория с EVTX файлами: {path}")
                    return str(path)
        
        self.logger.warning("Директория system_info не найдена или не содержит EVTX файлов")
        return None
    
    def parse_evtx_file(self, file_path: str, log_type: str) -> List[OSEvent]:
        """Парсинг EVTX файла журнала Windows"""
        events = []
        
        try:
            # Сначала пробуем определить тип файла
            with open(file_path, 'rb') as f:
                header = f.read(8)
                
            # Проверяем сигнатуру EVTX файла
            if header == b'ElfFile\x00':
                # Бинарный EVTX файл
                if self.has_evtx:
                    events = self._parse_binary_evtx(file_path, log_type)
                else:
                    self.logger.warning(f"Бинарный EVTX файл обнаружен, но библиотека evtx не установлена")
                    events = self._parse_evtx_as_text(file_path, log_type)
            else:
                # Возможно, это XML или текстовый файл
                events = self._parse_text_evtx(file_path, log_type)
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга файла {file_path}: {e}")
            # Пробуем текстовый парсинг как запасной вариант
            events = self._parse_evtx_as_text(file_path, log_type)
            
        return events
    
    def _parse_binary_evtx(self, file_path: str, log_type: str) -> List[OSEvent]:
        """Парсинг бинарного EVTX файла с помощью библиотеки evtx"""
        events = []
        
        try:
            from Evtx.Evtx import Evtx
            from Evtx.Views import evtx_file_xml_view
            
            with Evtx(file_path) as evtx_file:
                for record in evtx_file.records():
                    try:
                        xml_record = evtx_file_xml_view(record)
                        event = self._parse_xml_event(xml_record, log_type)
                        if event:
                            events.append(event)
                    except Exception as e:
                        self.logger.debug(f"Ошибка парсинга записи EVTX: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Ошибка парсинга бинарного EVTX: {e}")
            
        return events
    
    def _parse_xml_event(self, xml_content: str, log_type: str) -> Optional[OSEvent]:
        """Парсинг XML события"""
        try:
            # Парсим XML
            root = ET.fromstring(xml_content)
            
            # Находим пространства имен
            ns = {'ns': 'http://schemas.microsoft.com/win/2004/08/events/event'}
            
            # Извлекаем данные
            system = root.find('.//ns:System', ns)
            if system is None:
                return None
            
            # EventID
            event_id_elem = system.find('ns:EventID', ns)
            event_code = event_id_elem.text if event_id_elem is not None else "0"
            
            # Level
            level_elem = system.find('ns:Level', ns)
            level_num = int(level_elem.text) if level_elem is not None and level_elem.text else 0
            level_text = self._convert_event_level(level_num)
            
            # TimeCreated
            time_created = system.find('ns:TimeCreated', ns)
            timestamp = time_created.get('SystemTime') if time_created is not None else ""
            
            # Provider
            provider = system.find('ns:Provider', ns)
            source = provider.get('Name') if provider is not None else "Неизвестно"
            
            # EventData/Data
            event_data = root.find('.//ns:EventData', ns)
            description = ""
            if event_data is not None:
                data_items = event_data.findall('ns:Data', ns)
                if data_items:
                    descriptions = []
                    for data in data_items:
                        if data.text:
                            descriptions.append(data.text.strip())
                    description = " | ".join(descriptions)
            
            # Фильтруем по шаблонам если нужно
            if self.use_custom_patterns and self.custom_patterns:
                if event_code not in self.custom_patterns:
                    return None
            elif not self.use_custom_patterns and event_code not in self.default_patterns:
                return None
            
            # Форматируем timestamp
            formatted_time = self._format_timestamp(timestamp)
            
            return OSEvent(
                timestamp=formatted_time,
                level=level_text,
                event_code=event_code,
                source=source,
                description=description,
                log_type=log_type
            )
            
        except Exception as e:
            self.logger.debug(f"Ошибка парсинга XML события: {e}")
            return None
    
    def _parse_text_evtx(self, file_path: str, log_type: str) -> List[OSEvent]:
        """Парсинг текстового представления EVTX"""
        events = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Если это XML
            if '<Event' in content and '<System>' in content:
                events = self._parse_xml_events(content, log_type)
            else:
                # Пробуем парсить как текстовый лог
                events = self._parse_plain_text_events(content, log_type)
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга текстового EVTX: {e}")
            
        return events
    
    def _parse_xml_events(self, xml_content: str, log_type: str) -> List[OSEvent]:
        """Парсинг XML событий"""
        events = []
        
        try:
            # Разделяем на отдельные события
            event_start = '<Event'
            event_end = '</Event>'
            
            start_pos = 0
            while True:
                start_idx = xml_content.find(event_start, start_pos)
                if start_idx == -1:
                    break
                
                end_idx = xml_content.find(event_end, start_idx)
                if end_idx == -1:
                    break
                
                event_xml = xml_content[start_idx:end_idx + len(event_end)]
                event = self._parse_xml_event(event_xml, log_type)
                if event:
                    events.append(event)
                
                start_pos = end_idx + len(event_end)
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга XML событий: {e}")
        
        return events
    
    def _parse_plain_text_events(self, text_content: str, log_type: str) -> List[OSEvent]:
        """Парсинг простого текстового лога"""
        events = []
        
        try:
            lines = text_content.split('\n')
            
            current_event = {}
            in_event = False
            
            for line in lines:
                line = line.strip()
                
                # Ищем начало события
                if 'Event Code:' in line or 'Код события:' in line:
                    # Если у нас уже есть собранное событие, сохраняем его
                    if in_event and 'code' in current_event:
                        event = self._create_os_event_from_dict(current_event, log_type)
                        if event:
                            events.append(event)
                    
                    current_event = {}
                    in_event = True
                    
                    # Извлекаем код события
                    code_match = re.search(r'(\d+)', line)
                    if code_match:
                        current_event['code'] = code_match.group(1)
                
                elif 'Event Time:' in line or 'Время события:' in line:
                    time_match = re.search(r':\s*(.+)', line)
                    if time_match:
                        current_event['time'] = time_match.group(1).strip()
                
                elif 'Event Type:' in line or 'Тип события:' in line or 'Level:' in line or 'Уровень:' in line:
                    level_match = re.search(r':\s*(.+)', line)
                    if level_match:
                        level_text = level_match.group(1).strip()
                        current_event['level'] = self._convert_level_text(level_text)
                
                elif 'Source:' in line or 'Источник:' in line:
                    source_match = re.search(r':\s*(.+)', line)
                    if source_match:
                        current_event['source'] = source_match.group(1).strip()
                
                elif 'Description:' in line or 'Описание:' in line:
                    desc_match = re.search(r':\s*(.+)', line)
                    if desc_match:
                        current_event['description'] = desc_match.group(1).strip()
                        in_event = False  # Завершаем сбор события
            
            # Не забываем последнее событие
            if in_event and 'code' in current_event:
                event = self._create_os_event_from_dict(current_event, log_type)
                if event:
                    events.append(event)
                    
        except Exception as e:
            self.logger.error(f"Ошибка парсинга текстовых событий: {e}")
        
        return events
    
    def _parse_evtx_as_text(self, file_path: str, log_type: str) -> List[OSEvent]:
        """Парсинг EVTX как текста (резервный метод)"""
        events = []
        
        try:
            with open(file_path, 'rb') as f:
                # Читаем как текст с разными кодировками
                try:
                    content = f.read().decode('utf-8', errors='ignore')
                except:
                    f.seek(0)
                    content = f.read().decode('cp1251', errors='ignore')
            
            # Ищем события по паттернам
            event_patterns = [
                r'Event Code:\s*(\d+)',
                r'Код события:\s*(\d+)',
                r'Event ID:\s*(\d+)',
                r'Идентификатор события:\s*(\d+)'
            ]
            
            for match in re.finditer('|'.join(event_patterns), content):
                event_code = match.group(1)
                
                # Фильтруем по шаблонам
                if self.use_custom_patterns and self.custom_patterns:
                    if event_code not in self.custom_patterns:
                        continue
                elif not self.use_custom_patterns and event_code not in self.default_patterns:
                    continue
                
                # Извлекаем контекст вокруг события
                start = max(0, match.start() - 500)
                end = min(len(content), match.end() + 500)
                context = content[start:end]
                
                # Извлекаем время
                time_match = re.search(r'Event Time:\s*(.+)', context)
                timestamp = time_match.group(1).strip() if time_match else "Неизвестно"
                
                # Извлекаем уровень
                level_match = re.search(r'Level:\s*(.+)', context)
                level_text = self._convert_level_text(level_match.group(1).strip()) if level_match else "Информация"
                
                # Извлекаем источник
                source_match = re.search(r'Source:\s*(.+)', context)
                source = source_match.group(1).strip() if source_match else "Неизвестно"
                
                # Извлекаем описание
                desc_match = re.search(r'Description:\s*(.+)', context)
                description = desc_match.group(1).strip() if desc_match else ""
                
                event = OSEvent(
                    timestamp=timestamp,
                    level=level_text,
                    event_code=event_code,
                    source=source,
                    description=description,
                    log_type=log_type
                )
                events.append(event)
                
        except Exception as e:
            self.logger.error(f"Ошибка резервного парсинга EVTX: {e}")
        
        return events
    
    def _create_os_event_from_dict(self, event_dict: Dict, log_type: str) -> Optional[OSEvent]:
        """Создание OSEvent из словаря"""
        try:
            event_code = event_dict.get('code', '0')
            
            # Фильтруем по шаблонам
            if self.use_custom_patterns and self.custom_patterns:
                if event_code not in self.custom_patterns:
                    return None
            elif not self.use_custom_patterns and event_code not in self.default_patterns:
                return None
            
            return OSEvent(
                timestamp=event_dict.get('time', 'Неизвестно'),
                level=event_dict.get('level', 'Информация'),
                event_code=event_code,
                source=event_dict.get('source', 'Неизвестно'),
                description=event_dict.get('description', ''),
                log_type=log_type
            )
        except Exception as e:
            self.logger.debug(f"Ошибка создания OSEvent: {e}")
            return None
    
    def _convert_event_level(self, level_num: int) -> str:
        """Конвертация числового уровня события в текст"""
        level_map = {
            1: "Критическое",
            2: "Ошибка",
            3: "Предупреждение",
            4: "Информация",
            5: "Подробно"
        }
        return level_map.get(level_num, f"Уровень {level_num}")
    
    def _convert_level_text(self, level_text: str) -> str:
        """Конвертация текстового уровня события"""
        text_lower = level_text.lower()
        
        if 'error' in text_lower or 'ошибка' in text_lower:
            return "Ошибка"
        elif 'critical' in text_lower or 'критическое' in text_lower or 'критично' in text_lower:
            return "Критическое"
        elif 'warning' in text_lower or 'предупреждение' in text_lower:
            return "Предупреждение"
        elif 'information' in text_lower or 'информация' in text_lower:
            return "Информация"
        else:
            return level_text
    
    def _format_timestamp(self, timestamp: str) -> str:
        """Форматирование timestamp в читаемый формат"""
        if not timestamp:
            return "Неизвестно"
        
        try:
            # Формат: 2024-01-15T10:30:45.123456Z
            if 'T' in timestamp and 'Z' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            elif 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return timestamp
        except:
            return timestamp
    
    def analyze_os_logs(self, log_dir: str) -> Tuple[List[OSEvent], List[OSEvent]]:
        """Анализ журналов ОС"""
        application_events = []
        system_events = []
        
        # Ищем файлы журналов
        app_log_path = None
        system_log_path = None
        
        log_dir_path = Path(log_dir)
        
        # Ищем файлы с разными именами
        evtx_files = list(log_dir_path.rglob("*.evtx"))
        evt_files = list(log_dir_path.rglob("*.evt"))
        all_log_files = evtx_files + evt_files
        
        # Сортируем по размеру (обычно системные журналы больше)
        all_log_files.sort(key=lambda x: x.stat().st_size if x.exists() else 0, reverse=True)
        
        # Пытаемся определить какие файлы какие
        for log_file in all_log_files:
            filename = log_file.name.lower()
            
            if 'application' in filename or 'app' in filename or 'приложение' in filename:
                if not app_log_path:
                    app_log_path = log_file
                    self.logger.info(f"Найден журнал приложений: {log_file}")
            elif 'system' in filename or 'sys' in filename or 'система' in filename:
                if not system_log_path:
                    system_log_path = log_file
                    self.logger.info(f"Найден журнал системы: {log_file}")
            elif 'security' in filename or 'безопасность' in filename:
                # Журнал безопасности пропускаем
                continue
            elif not app_log_path:  # Первый несистемный файл считаем журналом приложений
                app_log_path = log_file
                self.logger.info(f"Предполагаемый журнал приложений: {log_file}")
            elif not system_log_path:  # Второй файл считаем системным
                system_log_path = log_file
                self.logger.info(f"Предполагаемый журнал системы: {log_file}")
        
        # Парсим журнал приложений
        if app_log_path and app_log_path.exists():
            application_events = self.parse_evtx_file(str(app_log_path), "Журнал приложения")
            self.logger.info(f"Спарсено событий из журнала приложений: {len(application_events)}")
        else:
            self.logger.warning(f"Журнал приложений не найден")
        
        # Парсим журнал системы
        if system_log_path and system_log_path.exists():
            system_events = self.parse_evtx_file(str(system_log_path), "Журнал системы")
            self.logger.info(f"Спарсено событий из журнала системы: {len(system_events)}")
        else:
            self.logger.warning(f"Журнал системы не найден")
        
        return application_events, system_events
    
    def format_os_logs_result(self, app_events: List[OSEvent], sys_events: List[OSEvent]) -> str:
        """Форматирование результатов анализа журналов ОС"""
        total_events = len(app_events) + len(sys_events)
        
        output = f"=== АНАЛИЗ ЖУРНАЛОВ ОС WINDOWS ===\n\n"
        output += f"Всего событий найдено: {total_events}\n"
        output += f"• Журнал приложения: {len(app_events)} событий\n"
        output += f"• Журнал системы: {len(sys_events)} событий\n\n"
        
        if self.use_custom_patterns:
            patterns = self.custom_patterns if self.custom_patterns else self.default_patterns
            output += f"Использованные коды событий: {', '.join(patterns)}\n\n"
        
        if total_events == 0:
            output += "Событий не найдено.\nВозможные причины:\n"
            output += "1. Файлы журналов отсутствуют в архиве\n"
            output += "2. Журналы не содержат событий с выбранными кодами\n"
            output += "3. Формат файлов журналов не поддерживается\n"
            return output
        
        output += "=== ЖУРНАЛ ПРИЛОЖЕНИЯ ===\n\n"
        if app_events:
            output += "Дата и время           | Уровень       | Код события | Источник\n"
            output += "-" * 80 + "\n"
            for event in app_events[:50]:  # Ограничиваем вывод
                output += f"{event.timestamp:20} | {event.level:13} | {event.event_code:11} | {event.source}\n"
            if len(app_events) > 50:
                output += f"... и еще {len(app_events) - 50} событий\n"
        else:
            output += "Событий не найдено\n"
        
        output += "\n\n=== ЖУРНАЛ СИСТЕМЫ ===\n\n"
        if sys_events:
            output += "Дата и время           | Уровень       | Код события | Источник\n"
            output += "-" * 80 + "\n"
            for event in sys_events[:50]:  # Ограничиваем вывод
                output += f"{event.timestamp:20} | {event.level:13} | {event.event_code:11} | {event.source}\n"
            if len(sys_events) > 50:
                output += f"... и еще {len(sys_events) - 50} событий\n"
        else:
            output += "Событий не найдено\n"
        
        # Статистика по уровням
        if total_events > 0:
            all_events = app_events + sys_events
            level_stats = {}
            for event in all_events:
                level_stats[event.level] = level_stats.get(event.level, 0) + 1
            
            output += "\n=== СТАТИСТИКА ПО УРОВНЯМ ===\n\n"
            for level, count in sorted(level_stats.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_events) * 100
                output += f"• {level}: {count} ({percentage:.1f}%)\n"
        
        return output
    
    def cleanup(self):
        """Очистка временных файлов"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info("Временные файлы анализа базовых механизмов очищены")
            except Exception as e:
                self.logger.error(f"Ошибка очистки временных файлов: {e}")