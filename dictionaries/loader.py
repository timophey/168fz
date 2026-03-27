"""
Загрузчик словарей из файлов
"""

import json
import csv
from pathlib import Path
from typing import Set, Dict, List
from datetime import datetime


class DictionaryLoader:
    """Загрузчик словарей различных форматов"""

    @staticmethod
    def load_from_json(filepath: Path) -> Set[str]:
        """Загрузка словаря из JSON файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Если это список слов
            if isinstance(data, list):
                return set(word.lower() for word in data if isinstance(word, str))
            # Если это словарь с полем 'words'
            elif isinstance(data, dict):
                if 'words' in data and isinstance(data['words'], list):
                    return set(word.lower() for word in data['words'] if isinstance(word, str))
                # Если это просто словарь слов {слово: значение}
                return set(k.lower() for k in data.keys() if isinstance(k, str))
            return set()

    @staticmethod
    def load_from_csv(filepath: Path, column: str = 'word') -> Set[str]:
        """Загрузка словаря из CSV файла"""
        words = set()
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if column in row:
                    words.add(row[column].strip().lower())
        return words

    @staticmethod
    def load_from_txt(filepath: Path) -> Set[str]:
        """Загрузка словаря из текстового файла (по одному слову на строку)"""
        words = set()
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip().lower()
                if word:
                    words.add(word)
        return words

    @staticmethod
    def load_dictionary(filepath: Path) -> Dict:
        """
        Загрузка словаря с метаданными
        Возвращает словарь с полями: words, name, version, source, loaded_at
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Файл словаря не найден: {filepath}")

        ext = filepath.suffix.lower()

        loaders = {
            '.json': DictionaryLoader.load_from_json,
            '.csv': DictionaryLoader.load_from_csv,
            '.txt': DictionaryLoader.load_from_txt,
        }

        if ext not in loaders:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}")

        words = loaders[ext](filepath)

        # Пытаемся извлечь метаданные из имени файла или соседних файлов
        name = filepath.stem
        version = "1.0"
        source = "local"
        category = None

        # Проверяем наличие файла с метаданными
        meta_file = filepath.with_suffix('.meta.json')
        if meta_file.exists():
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                name = meta.get('name', name)
                version = meta.get('version', version)
                source = meta.get('source', source)
                category = meta.get('category')

        # Если это JSON файл, пытаемся извлечь category из его содержимого
        if ext == '.json' and not category:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'category' in data:
                        category = data['category']
            except:
                pass

        result = {
            'words': words,
            'name': name,
            'version': version,
            'source': source,
            'loaded_at': datetime.now().isoformat(),
            'filepath': str(filepath)
        }

        if category:
            result['category'] = category

        return result
