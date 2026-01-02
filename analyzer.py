# analyzer.py
import pandas as pd
import logging
from typing import Dict, Tuple, List, Any
import sys

logger = logging.getLogger(__name__)

class ErrorAnalyzer:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Загрузка данных из Excel файла с обработкой ошибок"""
        try:
            # Пробуем загрузить с разными движками
            try:
                self.df = pd.read_excel(self.file_path, sheet_name='Лист1', engine='openpyxl')
            except:
                self.df = pd.read_excel(self.file_path, sheet_name='Лист1', engine='xlrd')
            
            logger.info(f"Файл успешно загружен. Строк: {len(self.df)}")
            
            # Проверяем необходимые колонки
            required_columns = ['Статус', 'Серьезность', 'Активный этап', 'Сектор', 'Участок', 'Дней в работе']
            missing_columns = [col for col in required_columns if col not in self.df.columns]
            
            if missing_columns:
                raise ValueError(f"Отсутствуют обязательные колонки: {missing_columns}")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {str(e)}")
            raise
    
    def clean_data(self):
        """Очистка и подготовка данных"""
        if self.df is None:
            return
        
        # Заполнение пустых значений
        fill_values = {
            'Серьезность': 'Не указана',
            'Статус': 'Не указан',
            'Активный этап': 'Не указан',
            'Сектор': 'Не указан',
            'Участок': 'Не указан',
            'Дней в работе': 0
        }
        
        for col, default_value in fill_values.items():
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna(default_value)
        
        # Стандартизация текстовых полей
        text_columns = ['Статус', 'Активный этап', 'Сектор', 'Участок', 'Серьезность']
        for col in text_columns:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.strip()
        
        # Обработка числовых полей
        if 'Дней в работе' in self.df.columns:
            # Преобразуем в числовой формат, заменяем ошибки на 0
            self.df['Дней в работе'] = pd.to_numeric(self.df['Дней в работе'], errors='coerce').fillna(0)
    
    def analyze_errors(self) -> Dict[str, Any]:
        """Основной анализ данных"""
        self.clean_data()
        
        analysis = {
            'total_errors': len(self.df),
            'successfully_closed': self._get_successfully_closed(),
            'clarification_required': self._get_clarification_required(),
            'closed_with_problems': self._get_closed_with_problems(),
            'in_progress': self._get_in_progress(),
            'seriousness_breakdown': self._get_seriousness_breakdown(),
            'sector_top10': self._get_sector_top10(),
            'area_top10': self._get_area_top10(),
            'status_distribution': self._get_status_distribution(),
            'deadline_violations_significant': self._get_deadline_violations_by_seriousness('Значительная'),
            'deadline_violations_critical': self._get_deadline_violations_by_seriousness('Критическая')
        }
        
        return analysis
    
    def _get_successfully_closed(self) -> int:
        """Количество успешно закрытых ошибок"""
        successful_statuses = ['Выполнение завершено успешно', 'Выполнение завершено успешно ']
        return len(self.df[self.df['Статус'].isin(successful_statuses)])
    
    def _get_clarification_required(self) -> int:
        """Количество ошибок на уточнении"""
        clarification_stages = ['Уточнение', 'Уточнение ']
        return len(self.df[self.df['Активный этап'].isin(clarification_stages)])
    
    def _get_closed_with_problems(self) -> int:
        """Количество ошибок закрытых с проблемами (исключая уточнение)"""
        problem_statuses = ['Выполнение завершено с проблемами', 'Выполнение завершено с проблемами ']
        clarification_stages = ['Уточнение', 'Уточнение ']
        
        mask = (self.df['Статус'].isin(problem_statuses)) & \
               (~self.df['Активный этап'].isin(clarification_stages))
        return len(self.df[mask])
    
    def _get_in_progress(self) -> int:
        """Количество ошибок в работе"""
        in_progress_statuses = ['ВОбработке', 'ВОбработке ']
        return len(self.df[self.df['Статус'].isin(in_progress_statuses)])
    
    def _get_seriousness_breakdown(self) -> Dict[str, int]:
        """Распределение серьезности для успешно закрытых"""
        successful_statuses = ['Выполнение завершено успешно', 'Выполнение завершено успешно ']
        successful = self.df[self.df['Статус'].isin(successful_statuses)]
        
        if 'Серьезность' in successful.columns:
            return successful['Серьезность'].value_counts().to_dict()
        return {}
    
    def _get_sector_top10(self) -> Dict[str, Dict[str, int]]:
        """ТОП-10 секторов с разбивкой по статусам"""
        sector_stats = {}
        
        if 'Сектор' not in self.df.columns:
            return sector_stats
            
        top_sectors = self.df['Сектор'].value_counts().head(10).index
        
        for sector in top_sectors:
            sector_data = self.df[self.df['Сектор'] == sector]
            
            sector_stats[sector] = {
                'total': len(sector_data),
                'successful': len(sector_data[sector_data['Статус'].isin(['Выполнение завершено успешно', 'Выполнение завершено успешно '])]),
                'with_problems': len(sector_data[sector_data['Статус'].isin(['Выполнение завершено с проблемами', 'Выполнение завершено с проблемами '])]),
                'in_progress': len(sector_data[sector_data['Статус'].isin(['ВОбработке', 'ВОбработке '])])
            }
        
        return sector_stats
    
    def _get_area_top10(self) -> Dict[str, Dict[str, int]]:
        """ТОП-10 участков с разбивка по статусам"""
        area_stats = {}
        
        if 'Участок' not in self.df.columns:
            return area_stats
            
        top_areas = self.df['Участок'].value_counts().head(10).index
        
        for area in top_areas:
            area_data = self.df[self.df['Участок'] == area]
            
            area_stats[area] = {
                'total': len(area_data),
                'successful': len(area_data[area_data['Статус'].isin(['Выполнение завершено успешно', 'Выполнение завершено успешно '])]),
                'with_problems': len(area_data[area_data['Статус'].isin(['Выполнение завершено с проблемами', 'Выполнение завершено с проблемами '])]),
                'in_progress': len(area_data[area_data['Статус'].isin(['ВОбработке', 'ВОбработке '])])
            }
        
        return area_stats
    
    def _get_status_distribution(self) -> Dict[str, int]:
        """Общее распределение по статусам"""
        if 'Статус' in self.df.columns:
            return self.df['Статус'].value_counts().to_dict()
        return {}
    
    def _get_deadline_violations_by_seriousness(self, seriousness: str) -> Dict[str, int]:
        """Статистика нарушений сроков по серьезности"""
        if 'Дней в работе' not in self.df.columns or 'Серьезность' not in self.df.columns:
            return {'total': 0, 'violations': 0}
        
        # Определяем лимит дней в зависимости от серьезности
        if seriousness == 'Значительная':
            deadline_days = 14
        elif seriousness == 'Критическая':
            deadline_days = 1
        else:
            return {'total': 0, 'violations': 0}
        
        # Фильтруем ошибки по серьезности
        seriousness_data = self.df[self.df['Серьезность'] == seriousness]
        
        if len(seriousness_data) == 0:
            return {'total': 0, 'violations': 0}
        
        # Считаем нарушения сроков (дней в работе > лимита)
        violations = len(seriousness_data[seriousness_data['Дней в работе'] > deadline_days])
        
        return {
            'total': len(seriousness_data),
            'violations': violations
        }