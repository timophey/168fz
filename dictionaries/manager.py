"""
Менеджер словарей - управление загрузкой и проверкой слов
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from .loader import DictionaryLoader


class DictionaryManager:
    """Управление словарями и проверка слов"""

    def __init__(self, dictionaries_dir: Path = None, sync_metadata: Dict = None, category_mapping_file: Path = None):
        """
        Инициализация менеджера словарей

        Args:
            dictionaries_dir: Путь к папке со словарями
            sync_metadata: Метаданные синхронизации от DictionarySynchronizer
            category_mapping_file: Путь к файлу с маппингом словарей → категорий
        """
        self.dictionaries_dir = dictionaries_dir or Path('dictionaries/data')
        self.dictionaries: Dict[str, Dict] = {}
        self.sync_metadata = sync_metadata or {}
        self.category_mapping: Dict[str, str] = {}

        # Загружаем маппинг категорий из файла
        mapping_path = category_mapping_file if category_mapping_file else Path('dictionaries/category_mapping.json')
        if mapping_path.exists():
            with open(mapping_path, 'r', encoding='utf-8') as f:
                self.category_mapping = json.load(f)
                print(f"Загружен маппинг категорий: {len(self.category_mapping)} записей")

        self._load_default_dictionaries()

    def _load_default_dictionaries(self):
        """Загрузка словарей из папки по умолчанию"""
        if self.dictionaries_dir.exists():
            for filepath in self.dictionaries_dir.glob('*.*'):
                if filepath.suffix.lower() in ['.json', '.csv', '.txt']:
                    try:
                        dict_data = DictionaryLoader.load_dictionary(filepath)
                        dict_name = dict_data['name']
                        self.dictionaries[dict_name] = dict_data
                        print(f"Загружен словарь: {dict_name} ({len(dict_data['words'])} слов)")
                    except Exception as e:
                        print(f"Ошибка загрузки словаря {filepath}: {e}")

    def load_dictionary(self, filepath: Path, name: str = None):
        """Загрузка дополнительного словаря"""
        dict_data = DictionaryLoader.load_dictionary(filepath)
        if name:
            dict_data['name'] = name
        self.dictionaries[dict_data['name']] = dict_data
        return dict_data['name']

    def reload_dictionaries(self):
        """Перезагрузка словарей из директории"""
        self.dictionaries.clear()
        self._load_default_dictionaries()

    def get_dictionary_info(self, name: str) -> Dict:
        """Получение информации о словаре"""
        return self.dictionaries.get(name, {})

    def list_dictionaries(self) -> List[Dict]:
        """Список всех загруженных словарей с статусом и категорией"""
        result = []
        for name, data in self.dictionaries.items():
            status = self._get_dictionary_status(name)
            category = self.get_dictionary_category(name)
            info = {
                'name': name,
                'words_count': len(data['words']),
                'version': data.get('version', '1.0'),
                'source': data.get('source', 'local'),
                'loaded_at': data.get('loaded_at'),
                'status': status,
                'category': category
            }
            result.append(info)
        return result

    def get_dictionary_info(self, name: str) -> Dict:
        """Получение информации о словаре с статусом и категорией"""
        info = self.dictionaries.get(name, {})
        if info:
            return {
                'name': name,
                'words_count': len(info['words']),
                'version': info.get('version', '1.0'),
                'source': info.get('source', 'local'),
                'loaded_at': info.get('loaded_at'),
                'status': self._get_dictionary_status(name),
                'category': self.get_dictionary_category(name),
                'description': info.get('description', '')
            }
        return {}

    def _get_dictionary_status(self, name: str) -> str:
        """
        Определение статуса словаря
        
        Returns:
            - 'synced': словарь был синхронизирован через синхронизатор
            - 'local': словарь загружен из локального файла (демо/ручная загрузка)
        """
        # Проверяем, был ли словарь синхронизирован (есть в метаданных)
        if self.sync_metadata and 'dictionaries' in self.sync_metadata:
            if name in self.sync_metadata['dictionaries']:
                return 'synced'
        # Если нет в метаданных, но файл существует - локальный
        return 'local'

    def get_dictionary_category(self, name: str) -> str:
        """
        Получение категории словаря
        
        Returns:
            Категория словаря (из метаданных, маппинга или автоматическая классификация)
        """
        if name not in self.dictionaries:
            return 'Неизвестный словарь'

        dict_data = self.dictionaries[name]

        # 1. Проверяем поле category в метаданных словаря
        if 'category' in dict_data:
            return dict_data['category']

        # 2. Проверяем конфиг-маппинг
        if name in self.category_mapping:
            return self.category_mapping[name]

        # 3. Используем автоматическую классификацию по названию
        return self._categorize_dictionary(name)

    def check_word(self, word: str) -> Dict[str, List[str]]:
        """
        Проверка слова по всем словарям

        Returns:
            Словарь с результатами: {'dictionary_name': [matched_words]}
        """
        word_lower = word.lower().strip()
        results = {}

        for dict_name, dict_data in self.dictionaries.items():
            if word_lower in dict_data['words']:
                results[dict_name] = [word]

        return results

    def check_text(self, text: str) -> Dict:
        """
        Проверка текста по всем словарям

        Returns:
            Словарь с результатами проверки
        """
        import re

        # Извлекаем слова (только кириллица, дефисы и апострофы)
        words = re.findall(r'[а-яё\-А-ЯЁ\']+', text)
        unique_words = set(w.lower() for w in words)

        results = {
            'total_words': len(words),
            'unique_words': len(unique_words),
            'dictionaries': {},
            'categories': {},
            'problematic_words': []
        }

        # Проверяем каждое слово
        for word in unique_words:
            word_results = self.check_word(word)

            if word_results:
                # Слово найдено в каком-то словаре
                for dict_name, matched in word_results.items():
                    if dict_name not in results['dictionaries']:
                        results['dictionaries'][dict_name] = []
                    results['dictionaries'][dict_name].append({
                        'word': word,
                        'count': sum(1 for w in words if w.lower() == word)
                    })

                    # Получаем категорию словаря
                    category = self.get_dictionary_category(dict_name)

                    # Добавляем в категорию
                    if category not in results['categories']:
                        results['categories'][category] = []
                    results['categories'][category].append({
                        'word': word,
                        'dictionary': dict_name,
                        'count': sum(1 for w in words if w.lower() == word)
                    })

                    # Если это словарь запрещенных слов или ненормативной лексики
                    if any(key in dict_name.lower() for key in ['запрещенные', 'ненормативная', 'мат']):
                        results['problematic_words'].append({
                            'word': word,
                            'dictionary': dict_name,
                            'category': category,
                            'count': sum(1 for w in words if w.lower() == word)
                        })

        return results

    def get_word_status(self, word: str) -> List[Tuple[str, str, str]]:
        """
        Получение статуса слова

        Returns:
            Список кортежей (dictionary_name, category, status)
        """
        results = self.check_word(word)
        status = []

        for dict_name in results.keys():
            category = self.get_dictionary_category(dict_name)
            dict_status = self._get_dictionary_status(dict_name)
            status.append((dict_name, category, dict_status))

        return status

    def _categorize_dictionary(self, name: str) -> str:
        """Категоризация словаря по его названию (fallback)"""
        name_lower = name.lower()

        if any(k in name_lower for k in ['запрещенные', 'ненормативная', 'обсценная', 'нецензурная']):
            return 'Запрещенные слова'
        elif any(k in name_lower for k in ['иностранные', 'заимствования']):
            return 'Иностранные слова'
        elif 'allowed_foreign' in name_lower:
            return 'Разрешенные иностранные термины'
        elif any(k in name_lower for k in ['нормативный', 'допустимые']):
            return 'Нормативные слова'
        elif any(k in name_lower for k in ['термины', 'профессионализмы']):
            return 'Термины'
        elif 'сокращения' in name_lower or 'аббревиатуры' in name_lower:
            return 'Аббревиатуры'
        elif 'топонимы' in name_lower:
            return 'Топонимы'
        elif 'жаргон' in name_lower or 'профессионализмы' in name_lower:
            return 'Профессионализмы и жаргон'
        else:
            return 'Другие словари'
