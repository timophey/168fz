#!/usr/bin/env python3
"""
Приложение для проверки соответствия текста закону № 168-ФЗ "О защите русского языка"
"""

import sys
import argparse
from pathlib import Path
from typing import Union, List

from extractors import TextExtractor
from checker import LanguageChecker
from reporter import ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description='Проверка текста на соответствие закону № 168-ФЗ "О защите русского языка"'
    )
    parser.add_argument(
        'input',
        help='Слово, путь к файлу или URL страницы для проверки'
    )
    parser.add_argument(
        '-o', '--output',
        help='Путь для сохранения отчета (CSV/JSON)',
        default=None
    )
    parser.add_argument(
        '--format',
        choices=['table', 'csv', 'json'],
        default='table',
        help='Формат вывода отчета'
    )

    args = parser.parse_args()

    try:
        # Извлечение текста из источника
        print(f"Извлечение текста из: {args.input}")
        extractor = TextExtractor(args.input)
        text = extractor.get_text()

        if not text.strip():
            print("Ошибка: Не удалось извлечь текст из источника")
            return 1

        print(f"Извлечено {len(text)} символов, {len(text.split())} слов")

        # Проверка текста
        print("Проверка текста...")
        checker = LanguageChecker()
        results = checker.check_text(text)

        # Генерация отчета
        print("Генерация отчета...")
        reporter = ReportGenerator(results, args.input)
        report = reporter.generate(format=args.format)

        # Вывод или сохранение отчета
        if args.output:
            reporter.save(args.output, format=args.format)
            print(f"Отчет сохранен в: {args.output}")
        else:
            print("\n" + report)

        return 0

    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
