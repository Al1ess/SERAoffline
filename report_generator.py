# report_generator.py
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, analysis_data: Dict[str, Any], month: str, year: int):
        self.analysis = analysis_data
        self.month = month
        self.year = year
    
    def _calculate_percentage(self, count: int) -> str:
        """Вычисление процента от общего количества ошибок"""
        if self.analysis['total_errors'] == 0:
            return "0%"
        percentage = (count / self.analysis['total_errors']) * 100
        return f"{percentage:.1f}%"
    
    def generate_text_report(self) -> str:
        """Генерация текстового отчета"""
        report = []
        
        # Заголовок отчета
        report.append(f"📊 ОТЧЕТ ПО ОШИБКАМ ЗА {self.month.upper()} {self.year}")
        report.append("=" * 50)
        report.append("")
        
        # Основная статистика
        report.append("📈 ОСНОВНАЯ СТАТИСТИКА:")
        report.append(f"• Всего ошибок: {self.analysis['total_errors']}")
        report.append(f"• Успешно закрыто: {self.analysis['successfully_closed']} ({self._calculate_percentage(self.analysis['successfully_closed'])})")
        report.append(f"• На уточнении: {self.analysis['clarification_required']} ({self._calculate_percentage(self.analysis['clarification_required'])})")
        report.append(f"• Закрыто с проблемами: {self.analysis['closed_with_problems']} ({self._calculate_percentage(self.analysis['closed_with_problems'])})")
        report.append(f"• На выполнении: {self.analysis['in_progress']} ({self._calculate_percentage(self.analysis['in_progress'])})")
        
        # Проверка суммы (для отладки)
        total_listed = (self.analysis['successfully_closed'] + 
                       self.analysis['clarification_required'] + 
                       self.analysis['closed_with_problems'] + 
                       self.analysis['in_progress'])
        other_errors = self.analysis['total_errors'] - total_listed
        
        if other_errors > 0:
            report.append(f"• Прочие статусы: {other_errors} ({self._calculate_percentage(other_errors)})")
        
        report.append("")
        
        # Статистика нарушений сроков
        report.append("🚨 НАРУШЕНИЯ СРОКОВ ИСПРАВЛЕНИЯ:")
        
        significant_stats = self.analysis['deadline_violations_significant']
        critical_stats = self.analysis['deadline_violations_critical']
        
        if significant_stats['total'] > 0:
            significant_percentage = (significant_stats['violations'] / significant_stats['total']) * 100
            report.append(f"• Значительные ошибки:")
            report.append(f"  Всего: {significant_stats['total']}")
            report.append(f"  Нарушения (>14 дней): {significant_stats['violations']} ({significant_percentage:.1f}%)")
        else:
            report.append(f"• Значительные ошибки: нет данных")
        
        if critical_stats['total'] > 0:
            critical_percentage = (critical_stats['violations'] / critical_stats['total']) * 100
            report.append(f"• Критические ошибки:")
            report.append(f"  Всего: {critical_stats['total']}")
            report.append(f"  Нарушения (>1 дня): {critical_stats['violations']} ({critical_percentage:.1f}%)")
        else:
            report.append(f"• Критические ошибки: нет данных")
        
        report.append("")
        
        # Распределение по серьезности (успешные)
        if self.analysis['seriousness_breakdown']:
            report.append("🎯 РАСПРЕДЕЛЕНИЕ УСПЕШНО ЗАКРЫТЫХ ПО СЕРЬЕЗНОСТИ:")
            for seriousness, count in self.analysis['seriousness_breakdown'].items():
                report.append(f"• {seriousness}: {count}")
            report.append("")
        else:
            report.append("🎯 Нет данных по распределению серьезности для успешно закрытых ошибок")
            report.append("")
        
        # ТОП-10 секторов
        if self.analysis['sector_top10']:
            report.append("🏆 ТОП-10 СЕКТОРОВ ПО КОЛИЧЕСТВУ ОШИБОК:")
            for i, (sector, stats) in enumerate(self.analysis['sector_top10'].items(), 1):
                total_percentage = (stats['total'] / self.analysis['total_errors']) * 100
                report.append(f"{i}. {sector}:")
                report.append(f"   Всего: {stats['total']} ({total_percentage:.1f}%)")
                report.append(f"   ✅ Успешно: {stats['successful']} | ⚠️ С проблемами: {stats['with_problems']} | 🔄 В работе: {stats['in_progress']}")
            report.append("")
        else:
            report.append("🏆 Нет данных по секторам")
            report.append("")
        
        # ТОП-10 участков
        if self.analysis['area_top10']:
            report.append("🎯 ТОП-10 УЧАСТКОВ ПО КОЛИЧЕСТВУ ОШИБОК:")
            for i, (area, stats) in enumerate(self.analysis['area_top10'].items(), 1):
                total_percentage = (stats['total'] / self.analysis['total_errors']) * 100
                report.append(f"{i}. {area}:")
                report.append(f"   Всего: {stats['total']} ({total_percentage:.1f}%)")
                report.append(f"   ✅ Успешно: {stats['successful']} | ⚠️ С проблемами: {stats['with_problems']} | 🔄 В работе: {stats['in_progress']}")
            report.append("")
        else:
            report.append("🎯 Нет данных по участкам")
            report.append("")
        
        # Общее распределение статусов
        if self.analysis['status_distribution']:
            report.append("📊 ОБЩЕЕ РАСПРЕДЕЛЕНИЕ ПО СТАТУСАМ:")
            for status, count in self.analysis['status_distribution'].items():
                percentage = (count / self.analysis['total_errors']) * 100
                report.append(f"• {status}: {count} ({percentage:.1f}%)")
            report.append("")
        else:
            report.append("📊 Нет данных по распределению статусов")
            report.append("")
        
        report.append(f"📅 Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        return "\n".join(report)
    
    def generate_detailed_report_file(self) -> str:
        """Генерация детального отчета в файле (если текст слишком длинный)"""
        return self.generate_text_report()