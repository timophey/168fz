#!/usr/bin/env python3
"""
CLI утилита для синхронизации официальных словарей
"""

import argparse
import sys
from pathlib import Path
from sync import DictionarySynchronizer, OFFICIAL_DICTIONARIES, save_sources_config


def main():
    parser = argparse.ArgumentParser(
        description='Синхронизация официальных словарей для проверки по закону № 168-ФЗ'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='Показать список доступных официальных словарей'
    )
    parser.add_argument(
        '--sync',
        nargs='?',
        const='all',
        metavar='DICT_NAME',
        help='Синхронизировать словарь (или all для всех)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Принудительная перезагрузка всех словарей'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Показать статус синхронизации'
    )
    parser.add_argument(
        '--config',
        action='store_true',
        help='Создать/обновить конфигурационный файл источников'
    )
    parser.add_argument(
        '--data-dir',
        default='dictionaries/data',
        help='Папка для хранения словарей (по умолчанию: dictionaries/data)'
    )

    args = parser.parse_args()

    if args.config:
        # Создание конфигурационного файла
        config_path = Path('sync/sources_config.json')
        save_sources_config(config_path)
        print(f"Конфигурация источников сохранена в: {config_path}")
        print("\nВНИМАНИЕ: URL источников являются примерными.")
        print("Перед использованием необходимо уточнить актуальные адреса у официальных институтов.")
        return 0

    if args.list:
        print("Доступные официальные словари согласно закону № 168-ФЗ:\n")
        for name, source in OFFICIAL_DICTIONARIES.items():
            print(f"  {name}:")
            print(f"    Название: {source.official_name}")
            print(f"    Институт: {source.institution}")
            print(f"    URL: {source.url}")
            print(f"    Формат: {source.format}")
            print(f"    Описание: {source.description[:100]}...")
            print()
        return 0

    if args.status:
        synchronizer = DictionarySynchronizer(data_dir=Path(args.data_dir))
        status = synchronizer.get_sync_status()
        print("Статус синхронизации словарей:\n")
        print(f"  Последняя полная синхронизация: {status.get('last_full_sync', 'Никогда')}")
        print()
        for dict_name, info in status['dictionaries'].items():
            source = OFFICIAL_DICTIONARIES.get(dict_name)
            print(f"  {dict_name}:")
            print(f"    Официальное название: {source.official_name if source else 'Неизвестно'}")
            if info.get('synced'):
                print(f"    Статус: ✓ Синхронизирован")
                print(f"    Версия: {info.get('version')}")
                print(f"    Слов: {info.get('word_count')}")
                print(f"    Последняя синхронизация: {info.get('last_sync')}")
                print(f"    Файл: {info.get('file')}")
            else:
                print(f"    Статус: ✗ Не синхронизирован")
                print(f"    Источник: {source.url if source else 'Неизвестно'}")
            print()
        return 0

    if args.sync:
        synchronizer = DictionarySynchronizer(data_dir=Path(args.data_dir))

        if args.sync == 'all':
            print("Синхронизация всех официальных словарей...\n")
            results = synchronizer.sync_all(force=args.force)
            print("\nРезультаты:")
            for dict_name, (success, message) in results.items():
                status = "✓" if success else "✗"
                print(f"  {status} {dict_name}: {message}")
        else:
            dict_name = args.sync
            if dict_name not in OFFICIAL_DICTIONARIES:
                print(f"Ошибка: Словарь '{dict_name}' не найден")
                print("Доступные словари:", ', '.join(OFFICIAL_DICTIONARIES.keys()))
                return 1
            success, message = synchronizer.sync_dictionary(dict_name, force=args.force)
            print(f"{'✓' if success else '✗'} {message}")

        return 0

    # Если нет аргументов - показываем справку
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
