# pdf_generator.py
import logging
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

class PDFReportGenerator:
    def __init__(self, analysis_data: Dict[str, Any], month: str, year: int, department: str = "Отдел"):
        self.analysis = analysis_data
        self.month = month
        self.year = year
        self.department = department
        self.styles = getSampleStyleSheet()
        
        # Регистрируем русские шрифты
        self._register_russian_fonts()
        
        # Создаем кастомные стили
        self._create_custom_styles()
    
    def _register_russian_fonts(self):
        """Регистрация русских шрифтов"""
        try:
            # Используем DejaVu Sans который поддерживает кириллицу
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            ]
            
            regular_font_registered = False
            bold_font_registered = False
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        if 'Bold' in font_path and not bold_font_registered:
                            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_path))
                            bold_font_registered = True
                            logger.info(f"Зарегистрирован жирный шрифт: {font_path}")
                        elif 'Bold' not in font_path and not regular_font_registered:
                            pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                            regular_font_registered = True
                            logger.info(f"Зарегистрирован обычный шрифт: {font_path}")
                    except Exception as e:
                        logger.warning(f"Не удалось зарегистрировать шрифт {font_path}: {e}")
                        continue
            
            if regular_font_registered and bold_font_registered:
                self.font_name = 'DejaVuSans'
                self.bold_font_name = 'DejaVuSans-Bold'
                logger.info("Успешно зарегистрированы русские шрифты")
            else:
                # Используем стандартные шрифты как запасной вариант
                self.font_name = 'Helvetica'
                self.bold_font_name = 'Helvetica-Bold'
                logger.warning("Русские шрифты не найдены, используется Helvetica")
                
        except Exception as e:
            logger.error(f"Ошибка регистрации шрифтов: {e}")
            self.font_name = 'Helvetica'
            self.bold_font_name = 'Helvetica-Bold'
    
    def _create_custom_styles(self):
        """Создание кастомных стилей для документа"""
        # Стиль для заголовка
        self.styles.add(ParagraphStyle(
            name='TitleStyle',
            parent=self.styles['Heading1'],
            fontName=self.bold_font_name,
            fontSize=16,
            spaceAfter=30,
            alignment=1,  # center
            textColor=colors.darkblue
        ))
        
        # Стиль для подзаголовков
        self.styles.add(ParagraphStyle(
            name='HeadingStyle',
            parent=self.styles['Heading2'],
            fontName=self.bold_font_name,
            fontSize=12,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue
        ))
        
        # Стиль для основного текста
        self.styles.add(ParagraphStyle(
            name='BodyStyle',
            parent=self.styles['Normal'],
            fontName=self.font_name,
            fontSize=10,
            spaceAfter=6
        ))
    
    def _calculate_percentage(self, count: int) -> str:
        """Вычисление процента от общего количества ошибок"""
        if self.analysis['total_errors'] == 0:
            return "0%"
        percentage = (count / self.analysis['total_errors']) * 100
        return f"{percentage:.1f}%"
    
    def _create_main_statistics_table(self):
        """Создание таблицы основной статистики"""
        data = [
            ['Показатель', 'Количество', '%']
        ]
        
        stats = [
            ('Всего ошибок', self.analysis['total_errors'], '100%'),
            ('Успешно закрыто', self.analysis['successfully_closed'], 
             self._calculate_percentage(self.analysis['successfully_closed'])),
            ('На уточнении', self.analysis['clarification_required'], 
             self._calculate_percentage(self.analysis['clarification_required'])),
            ('Закрыто с проблемами', self.analysis['closed_with_problems'], 
             self._calculate_percentage(self.analysis['closed_with_problems'])),
            ('На выполнении', self.analysis['in_progress'], 
             self._calculate_percentage(self.analysis['in_progress']))
        ]
        
        for stat in stats:
            data.append(stat)
        
        table = Table(data, colWidths=[100*mm, 40*mm, 40*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        return table
    
    def _create_deadline_violations_table(self):
        """Создание таблицы нарушений сроков"""
        data = [
            ['Серьезность ошибок', 'Всего', 'Нарушения срока', '%']
        ]
        
        significant_stats = self.analysis['deadline_violations_significant']
        critical_stats = self.analysis['deadline_violations_critical']
        
        if significant_stats['total'] > 0:
            significant_percentage = (significant_stats['violations'] / significant_stats['total']) * 100
            data.append([
                'Значительные (>14 дней)',
                significant_stats['total'],
                significant_stats['violations'],
                f"{significant_percentage:.1f}%"
            ])
        
        if critical_stats['total'] > 0:
            critical_percentage = (critical_stats['violations'] / critical_stats['total']) * 100
            data.append([
                'Критические (>1 дня)',
                critical_stats['total'],
                critical_stats['violations'],
                f"{critical_percentage:.1f}%"
            ])
        
        if len(data) > 1:  # Если есть данные кроме заголовка
            table = Table(data, colWidths=[80*mm, 30*mm, 40*mm, 30*mm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.mistyrose),
                ('FONTNAME', (0, 1), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            return table
        return None
    
    def _create_sector_top_table(self):
        """Создание таблицы ТОП секторов"""
        if not self.analysis['sector_top10']:
            return None
        
        data = [
            ['Сектор', 'Всего', 'Успешно', 'С проблемами', 'В работе', '%']
        ]
        
        for sector, stats in self.analysis['sector_top10'].items():
            percentage = (stats['total'] / self.analysis['total_errors']) * 100
            data.append([
                sector,
                stats['total'],
                stats['successful'],
                stats['with_problems'],
                stats['in_progress'],
                f"{percentage:.1f}%"
            ])
        
        table = Table(data, colWidths=[50*mm, 20*mm, 20*mm, 25*mm, 20*mm, 25*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.honeydew),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.honeydew])
        ]))
        
        return table
    
    def _create_area_top_table(self):
        """Создание таблицы ТОП участков"""
        if not self.analysis['area_top10']:
            return None
        
        data = [
            ['Участок', 'Всего', 'Успешно', 'С проблемами', 'В работе', '%']
        ]
        
        for area, stats in self.analysis['area_top10'].items():
            percentage = (stats['total'] / self.analysis['total_errors']) * 100
            data.append([
                area[:30] + '...' if len(area) > 30 else area,  # Обрезаем длинные названия
                stats['total'],
                stats['successful'],
                stats['with_problems'],
                stats['in_progress'],
                f"{percentage:.1f}%"
            ])
        
        table = Table(data, colWidths=[50*mm, 20*mm, 20*mm, 25*mm, 20*mm, 25*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkorange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lemonchiffon),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lemonchiffon])
        ]))
        
        return table
    
    def generate_pdf(self, parent_window=None):
        """Генерация PDF документа с выбором папки"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            from datetime import datetime
            
            # Предлагаем выбрать папку и имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"отчет_ошибок_{timestamp}.pdf"
            
            file_path, _ = QFileDialog.getSaveFileName(
                parent_window,
                "Сохранить отчет как PDF",
                default_name,
                "PDF Files (*.pdf);;All Files (*)"
            )
            
            if not file_path:
                return ""  # Пользователь отменил
            
            # Добавляем расширение .pdf если его нет
            if not file_path.lower().endswith('.pdf'):
                file_path += '.pdf'
            
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            story = []
            
            # Заголовок документа
            title = Paragraph(f"ОТЧЕТ ПО ОШИБКАМ ЗА {self.month.upper()} {self.year}г.", self.styles['TitleStyle'])
            story.append(title)
            
            # Информация об отделе и дате
            department_info = Paragraph(f"Отдел: {self.department}", self.styles['BodyStyle'])
            date_info = Paragraph(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}", self.styles['BodyStyle'])
            story.append(department_info)
            story.append(date_info)
            story.append(Spacer(1, 15))
            
            # Основная статистика
            story.append(Paragraph("1. ОСНОВНАЯ СТАТИСТИКА", self.styles['HeadingStyle']))
            story.append(self._create_main_statistics_table())
            story.append(Spacer(1, 15))
            
            # Нарушения сроков
            deadline_table = self._create_deadline_violations_table()
            if deadline_table:
                story.append(Paragraph("2. НАРУШЕНИЯ СРОКОВ ИСПРАВЛЕНИЯ", self.styles['HeadingStyle']))
                story.append(deadline_table)
                story.append(Spacer(1, 15))
            
            # ТОП секторов
            sector_table = self._create_sector_top_table()
            if sector_table:
                story.append(Paragraph("3. ТОП-10 СЕКТОРОВ ПО КОЛИЧЕСТВУ ОШИБОК", self.styles['HeadingStyle']))
                story.append(sector_table)
                story.append(Spacer(1, 15))
            
            # ТОП участков
            area_table = self._create_area_top_table()
            if area_table:
                story.append(Paragraph("4. ТОП-10 УЧАСТКОВ ПО КОЛИЧЕСТВУ ОШИБОК", self.styles['HeadingStyle']))
                story.append(area_table)
            
            # Футер с автором
            story.append(Spacer(1, 20))
            footer = Paragraph(f"by Aleksey Pankratov", self.styles['BodyStyle'])
            story.append(footer)
            
            # Создаем документ
            doc.build(story)
            logger.info(f"PDF документ успешно создан: {file_path}")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании PDF: {str(e)}")
            raise