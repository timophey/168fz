"""
Менеджер словарей - управление загрузкой и проверкой слов
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple
from .loader import DictionaryLoader


class DictionaryManager:
    """Управление словарями и проверка слов"""

    def __init__(self, dictionaries_dir: Path = None):
        """
        Инициализация менеджера словарей

        Args:
            dictionaries_dir: Путь к папке со словарями
        """
        self.dictionaries_dir = dictionaries_dir or Path('dictionaries/data')
        self.dictionaries: Dict[str, Dict] = {}
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

    def get_dictionary_info(self, name: str) -> Dict:
        """Получение информации о словаре"""
        return self.dictionaries.get(name, {})

    def list_dictionaries(self) -> List[Dict]:
        """Список всех загруженных словарей"""
        return [
            {
                'name': name,
                'words_count': len(data['words']),
                'version': data['version'],
                'source': data['source'],
                'loaded_at': data['loaded_at']
            }
            for name, data in self.dictionaries.items()
        ]

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

                    # Если это словарь запрещенных слов или ненормативной лексики
                    if any(key in dict_name.lower() for key in ['запрещенные', 'ненормативная', 'мат']):
                        results['problematic_words'].append({
                            'word': word,
                            'dictionary': dict_name,
                            'count': sum(1 for w in words if w.lower() == word)
                        })

        return results

    def get_word_status(self, word: str) -> List[Tuple[str, str]]:
        """
        Получение статуса слова

        Returns:
            Список кортежей (dictionary_name, category)
        """
        results = self.check_word(word)
        status = []

        for dict_name in results.keys():
            category = self._categorize_dictionary(dict_name)
            status.append((dict_name, category))

        return status

    def _categorize_dictionary(self, name: str) -> str:
        """Категоризация словаря по его названию"""
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
        else:
            return 'Другие словари'
