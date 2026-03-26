"""
Модуль генерации отчетов о проверке текста
"""

import json
import csv
from datetime import datetime
from typing import Dict, List
from pathlib import Path


class ReportGenerator:
    """Генератор отчетов в различных форматах"""

    def __init__(self, results: Dict, source: str = None):
        """
        Инициализация генератора

        Args:
            results: Результаты проверки от LanguageChecker
            source: Источник, из которого был взят текст
        """
        self.results = results
        self.source = source or 'неизвестный источник'
        self.generated_at = datetime.now()

    def generate(self, format: str = 'table') -> str:
        """
        Генерация отчета

        Args:
            format: Формат отчета ('table', 'csv', 'json')

        Returns:
            Строка с отчетом
        """
        generators = {
            'table': self._generate_table,
            'csv': self._generate_csv,
            'json': self._generate_json,
        }

        if format not in generators:
            raise ValueError(f"Неподдерживаемый формат: {format}")

        return generators[format]()

    def save(self, filepath: str, format: str = None):
        """
        Сохранение отчета в файл

        Args:
            filepath: Путь для сохранения
            format: Формат (определяется по расширению файла, если не указан)
        """
        path = Path(filepath)

        if format is None:
            format = self._detect_format(path)

        report = self.generate(format)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"Отчет сохранен: {filepath} ({format})")

    def _detect_format(self, path: Path) -> str:
        """Определение формата по расширению файла"""
        ext = path.suffix.lower()
        mapping = {
            '.csv': 'csv',
            '.json': 'json',
            '.txt': 'table',
        }
        return mapping.get(ext, 'table')

    def _generate_table(self) -> str:
        """Генерация отчета в виде таблицы (ASCII)"""
        lines = []
        line = '=' * 80
        lines.append(line)
        lines.append(f"ОТЧЕТ О ПРОВЕРКЕ ТЕКСТА НА СООТВЕТСТВИЕ ЗАКОНУ № 168-ФЗ")
        lines.append(line)
        lines.append(f"Источник: {self.source}")
        lines.append(f"Дата проверки: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(line)

        # Статистика
        lines.append("\n📊 СТАТИСТИКА:")
        stats = self.results.get('statistics', {})
        lines.append(f"  Всего символов: {stats.get('total_chars', 0)}")
        lines.append(f"  Всего слов: {stats.get('total_words', 0)}")
        lines.append(f"  Уникальных слов: {stats.get('unique_words', 0)}")

        # Загруженные словари
        lines.append("\n📚 ИСПОЛЬЗОВАННЫЕ СЛОВАРИ:")
        for dict_info in self.results.get('dictionaries_used', []):
            lines.append(f"  • {dict_info['name']} ({dict_info['words_count']} слов, версия {dict_info['version']})")

        # Запрещенные слова
        prohibited = self.results.get('checks', {}).get('prohibited_words', [])
        if prohibited:
            lines.append("\n⚠️  ЗАПРЕЩЕННЫЕ СЛОВА (требуют немедленного удаления):")
            lines.append(self._format_table(['Слово', 'Кол-во', 'Словарь', 'Статья закона'],
                                          [[p['word'], str(p['count']), p['dictionary'], p.get('law_article', '-')]
                                           for p in prohibited]))
        else:
            lines.append("\n✅ Запрещенные слова не обнаружены")

        # Иностранные слова
        foreign = self.results.get('checks', {}).get('foreign_words', [])
        if foreign:
            lines.append("\n🌐 ИНОСТРАННЫЕ СЛОВА (рекомендуется заменить):")
            lines.append(self._format_table(['Слово', 'Кол-во', 'Рекомендация'],
                                          [[f['word'], str(f['count']), f.get('recommendation', '-')]
                                           for f in foreign[:20]]))  # Ограничиваем вывод
            if len(foreign) > 20:
                lines.append(f"  ... и еще {len(foreign) - 20} слов")
        else:
            lines.append("\n✅ Иностранные слова не обнаружены")

        # Нарушения норм
        violations = self.results.get('checks', {}).get('normative_violations', [])
        if violations:
            lines.append("\n📚 НАРУШЕНИЯ НОРМ РУССКОГО ЯЗЫКА:")
            lines.append(self._format_table(['Слово', 'Кол-во', 'Проблема'],
                                          [[v['word'], str(v['count']), v.get('issue', '-')]
                                           for v in violations[:20]]))
            if len(violations) > 20:
                lines.append(f"  ... и еще {len(violations) - 20} слов")
        else:
            lines.append("\n✅ Нарушений норм не обнаружено")

        # Рекомендации
        lines.append("\n💡 РЕКОМЕНДАЦИИ:")
        for rec in self.results.get('checks', {}).get('recommendations', []):
            lines.append(f"  {rec}")

        # Сводка
        summary = self.results.get('summary', {})
        lines.append(f"\n🎯 СВОДКА:")
        lines.append(f"  Уровень риска: {self._format_risk_level(summary.get('risk_level', 'low'))}")
        lines.append(f"  Количество нарушений: {summary.get('violation_count', 0)}")

        lines.append(line)
        lines.append(f"Отчет сгенерирован: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(line)

        return '\n'.join(lines)

    def _format_table(self, headers: List[str], rows: List[List[str]]) -> str:
        """Форматирование таблицы"""
        if not rows:
            return "  Нет данных"

        # Определяем ширину колонок
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Формируем строки
        lines = []
        header_line = '  ' + ' | '.join(h.ljust(w) for h, w in zip(headers, col_widths))
        lines.append(header_line)
        lines.append('  ' + '-+-'.join('-' * w for w in col_widths))

        for row in rows:
            row_line = '  ' + ' | '.join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
            lines.append(row_line)

        return '\n'.join(lines)

    def _format_risk_level(self, level: str) -> str:
        """Форматирование уровня риска"""
        levels = {
            'low': '🟢 Низкий',
            'medium': '🟡 Средний',
            'high': '🔴 Высокий',
        }
        return levels.get(level, level)

    def _generate_csv(self) -> str:
        """Генерация отчета в формате CSV"""
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output, delimiter=';')

        # Заголовок
        writer.writerow(['Отчет о проверке текста на соответствие закону № 168-ФЗ'])
        writer.writerow(['Источник', self.source])
        writer.writerow(['Дата проверки', self.generated_at.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])

        # Статистика
        writer.writerow(['СТАТИСТИКА'])
        stats = self.results.get('statistics', {})
        writer.writerow(['Всего символов', stats.get('total_chars', 0)])
        writer.writerow(['Всего слов', stats.get('total_words', 0)])
        writer.writerow(['Уникальных слов', stats.get('unique_words', 0)])
        writer.writerow([])

        # Запрещенные слова
        writer.writerow(['ЗАПРЕЩЕННЫЕ СЛОВА'])
        writer.writerow(['Слово', 'Количество', 'Словарь', 'Статья закона'])
        for p in self.results.get('checks', {}).get('prohibited_words', []):
            writer.writerow([p['word'], p['count'], p['dictionary'], p.get('law_article', '-')])

        writer.writerow([])

        # Иностранные слова
        writer.writerow(['ИНОСТРАННЫЕ СЛОВА'])
        writer.writerow(['Слово', 'Количество', 'Рекомендация'])
        for f in self.results.get('checks', {}).get('foreign_words', []):
            writer.writerow([f['word'], f['count'], f.get('recommendation', '-')])

        writer.writerow([])

        # Сводка
        writer.writerow(['СВОДКА'])
        summary = self.results.get('summary', {})
        writer.writerow(['Уровень риска', summary.get('risk_level', 'low')])
        writer.writerow(['Количество нарушений', summary.get('violation_count', 0)])

        return output.getvalue()

    def _generate_json(self) -> str:
        """Генерация отчета в формате JSON"""
        report = {
            'report_type': 'language_compliance_check',
            'law': '№ 168-ФЗ "О защите русского языка"',
            'source': self.source,
            'generated_at': self.generated_at.isoformat(),
            'results': self.results
        }
        return json.dumps(report, ensure_ascii=False, indent=2)
