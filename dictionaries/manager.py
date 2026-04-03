"""
Менеджер словарей - управление загрузкой и проверкой слов
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import OrderedDict
from .loader import DictionaryLoader
from .morph_analyzer import MorphAnalyzer, MORPH_AVAILABLE
from .bloom_filter import BloomFilter


class LRUCache:
    """
    Simple LRU cache implementation with bounded size.
    Uses OrderedDict for O(1) get/set operations.
    """
    
    def __init__(self, maxsize: int = 100000):
        self.maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()
    
    def get(self, key, default=None):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return default
    
    def put(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)
    
    def __contains__(self, key):
        return key in self._cache
    
    def __len__(self):
        return len(self._cache)
    
    def clear(self):
        self._cache.clear()


class DictionaryManager:
    """Управление словарями и проверка слов"""

    # Maximum size for word check cache (100K unique word+dict combinations)
    MAX_WORD_CHECK_CACHE = 100000

    def __init__(self, dictionaries_dir: Path = None, sync_metadata: Dict = None, category_mapping_file: Path = None, user_data_dir: Path = None, use_morph_analysis: bool = True):
        """
        Инициализация менеджера словарей

        Args:
            dictionaries_dir: Путь к папке со словарями (официальные)
            sync_metadata: Метаданные синхронизации от DictionarySynchronizer
            category_mapping_file: Путь к файлу с маппингом словарей → категорий
            user_data_dir: Путь к папке с пользовательскими словарями
            use_morph_analysis: Использовать морфологический анализ для поиска базовых форм
        """
        self.dictionaries_dir = dictionaries_dir or Path('dictionaries/data')
        self.user_data_dir = user_data_dir or Path('dictionaries/user_data')
        self.dictionaries: Dict[str, Dict] = {}
        self.sync_metadata = sync_metadata or {}
        self.category_mapping: Dict[str, str] = {}
        self.use_morph_analysis = use_morph_analysis and MORPH_AVAILABLE
        
        # Bounded LRU cache for word analysis results to speed up repeated checks
        self._word_check_cache = LRUCache(self.MAX_WORD_CHECK_CACHE)
        
        # Bloom filters for large dictionaries (memory-efficient negative checks)
        # Threshold: use bloom filter for dictionaries with more than 100K words
        self._bloom_filters: Dict[str, BloomFilter] = {}
        self._bloom_filter_threshold = int(os.getenv('BLOOM_FILTER_THRESHOLD', '100000'))

        # Инициализируем морфологический анализатор если доступен
        self.morph_analyzer: Optional[MorphAnalyzer] = None
        if self.use_morph_analysis:
            try:
                self.morph_analyzer = MorphAnalyzer()
            except Exception as e:
                print(f"Морфологический анализ недоступ: {e}")
                self.use_morph_analysis = False

        # Загружаем маппинг категорий из файла
        mapping_path = category_mapping_file if category_mapping_file else Path('dictionaries/category_mapping.json')
        if mapping_path.exists():
            with open(mapping_path, 'r', encoding='utf-8') as f:
                self.category_mapping = json.load(f)
                print(f"Загружен маппинг категорий: {len(self.category_mapping)} записей")

        self._load_default_dictionaries()

    def _load_default_dictionaries(self):
        """Загрузка словарей из папок data и user_data"""
        # Clear existing bloom filters
        self._bloom_filters.clear()
        
        # Загружаем официальные словари
        if self.dictionaries_dir.exists():
            for filepath in self.dictionaries_dir.glob('*.*'):
                if filepath.suffix.lower() in ['.json', '.csv', '.txt']:
                    try:
                        dict_data = DictionaryLoader.load_dictionary(filepath)
                        dict_name = dict_data['name']
                        # Официальные словари имеют source='official' или из метаданных
                        if 'source' not in dict_data:
                            dict_data['source'] = 'official'
                        self.dictionaries[dict_name] = dict_data
                        
                        # Create bloom filter for large dictionaries
                        word_count = len(dict_data['words'])
                        if word_count > self._bloom_filter_threshold:
                            print(f"Создание bloom filter для словаря {dict_name} ({word_count} слов)...")
                            bloom = BloomFilter(word_count, false_positive_rate=0.001)
                            bloom.populate_from_set(dict_data['words'])
                            self._bloom_filters[dict_name] = bloom
                            stats = bloom.get_stats()
                            print(f"  Bloom filter: {stats['size_mb']:.2f} MB, {stats['hash_count']} hash functions")
                        
                        print(f"Загружен словарь: {dict_name} ({word_count} слов) [официальный]")
                    except Exception as e:
                        print(f"Ошибка загрузки словаря {filepath}: {e}")
        
        # Загружаем пользовательские словари
        if self.user_data_dir.exists():
            for filepath in self.user_data_dir.glob('*.*'):
                if filepath.suffix.lower() in ['.json', '.csv', '.txt']:
                    try:
                        dict_data = DictionaryLoader.load_dictionary(filepath)
                        dict_name = dict_data['name']
                        # Пользовательские словари имеют source='user'
                        dict_data['source'] = 'user'
                        # Добавляем префикс если нет
                        if not dict_name.startswith('user_'):
                            dict_name = f'user_{dict_name}'
                            dict_data['name'] = dict_name
                        # Если словарь с таким именем уже существует, добавляем timestamp
                        original_name = dict_name
                        counter = 1
                        while dict_name in self.dictionaries:
                            stem = filepath.stem
                            dict_name = f'user_{stem}_{counter}'
                            dict_data['name'] = dict_name
                            counter += 1
                        if original_name != dict_name:
                            print(f"Переименовано: {original_name} -> {dict_name}")
                        
                        self.dictionaries[dict_name] = dict_data
                        
                        # Create bloom filter for large user dictionaries
                        word_count = len(dict_data['words'])
                        if word_count > self._bloom_filter_threshold:
                            print(f"Создание bloom filter для словаря {dict_name} ({word_count} слов)...")
                            bloom = BloomFilter(word_count, false_positive_rate=0.001)
                            bloom.populate_from_set(dict_data['words'])
                            self._bloom_filters[dict_name] = bloom
                        
                        print(f"Загружен пользовательский словарь: {dict_name} ({word_count} слов)")
                    except Exception as e:
                        print(f"Ошибка загрузки пользовательского словаря {filepath}: {e}")

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
        self._word_check_cache.clear()
        self._bloom_filters.clear()  # Clear bloom filters when dictionaries change
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
            category_code = self.get_category_code(category)
            info = {
                'name': name,
                'words_count': len(data['words']),
                'version': data.get('version', '1.0'),
                'source': data.get('source', 'local'),
                'loaded_at': data.get('loaded_at'),
                'status': status,
                'category': category,
                'category_code': category_code
            }
            result.append(info)
        return result

    def get_dictionary_info(self, name: str) -> Dict:
        """Получение информации о словаре с статусом и категорией"""
        info = self.dictionaries.get(name, {})
        if info:
            category = self.get_dictionary_category(name)
            category_code = self.get_category_code(category)
            return {
                'name': name,
                'words_count': len(info['words']),
                'version': info.get('version', '1.0'),
                'source': info.get('source', 'local'),
                'loaded_at': info.get('loaded_at'),
                'status': self._get_dictionary_status(name),
                'category': category,
                'category_code': category_code,
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

    def get_category_code(self, category_name: str) -> str:
        """
        Получение кода категории по её русскому названию
        
        Args:
            category_name: русское название категории (например, "Нормативные слова")
            
        Returns:
            Код категории на латинице (например, "normative") или slug от названия если код не задан
        """
        # Проверяем, есть ли код в маппинге категорий
        if 'categories' in self.category_mapping:
            cat_info = self.category_mapping['categories'].get(category_name, {})
            if 'code' in cat_info:
                return cat_info['code']
        
        # Fallback: создаем slug из названия
        slug = category_name.lower().replace(' ', '_').replace('и', '').replace('(', '').replace(')', '').replace(',', '').replace('.', '').replace('!', '').replace('?', '')
        return slug

    def check_word(self, word: str, dictionary_names: List[str] = None) -> Dict:
        """
        Проверка слова по указанным словарям (или всем по умолчанию)

        Args:
            word: слово для проверки
            dictionary_names: список имен словарей для проверки (None = все словари)

        Returns:
            Словарь с результатами: {
                'dictionaries': {'dictionary_name': [matched_words]},
                'found_via_morph': bool,  # Найдено через морфологический анализ
                'original_word': str,      # Оригинальное слово
                'found_word': str          # Найденное слово (может отличаться от оригинала)
            }
        """
        word_lower = word.lower().strip()
        
        # Create cache key that includes which dictionaries to check
        # Use frozenset of dictionary_names to make it hashable
        dict_key = frozenset(dictionary_names) if dictionary_names else None
        cache_key = (word_lower, dict_key)
        
        # Check cache first
        cached = self._word_check_cache.get(cache_key)
        if cached is not None:
            return cached
        
        results = {
            'dictionaries': {},
            'found_via_morph': False,
            'original_word': word,
            'found_word': word_lower
        }

        # Определяем, какие словари проверять
        dictionaries_to_check = self.dictionaries
        if dictionary_names:
            # Фильтруем только указанные словари
            dictionaries_to_check = {k: v for k, v in self.dictionaries.items() if k in dictionary_names}

        # 1. Сначала проверяем точное совпадение
        # For large dictionaries with bloom filters, use bloom filter for fast negative check
        for dict_name, dict_data in dictionaries_to_check.items():
            # Check bloom filter first for large dictionaries
            if dict_name in self._bloom_filters:
                bloom = self._bloom_filters[dict_name]
                if not bloom.contains(word_lower):
                    # Word is DEFINITELY NOT in this dictionary - skip expensive set lookup
                    continue
            
            # Either no bloom filter or bloom says "maybe" - do actual lookup
            if word_lower in dict_data['words']:
                results['dictionaries'][dict_name] = [word]
                results['found_word'] = word_lower

        # Если нашли точное совпадение - возвращаем
        if results['dictionaries']:
            self._word_check_cache.put(cache_key, results)
            return results

        # 2. Если точного совпадения нет и включен морфоанализ - ищем базовую форму
        if self.use_morph_analysis and self.morph_analyzer:
            # Собираем все слова из словарей для быстрого поиска
            all_dict_words: Set[str] = set()
            for dict_data in dictionaries_to_check.values():
                all_dict_words.update(dict_data['words'])

            # Ищем слово через морфологический анализ
            found_word = self.morph_analyzer.find_in_dictionary(word_lower, all_dict_words)
            
            if found_word:
                results['found_via_morph'] = True
                results['found_word'] = found_word
                # Нашли базовую форму - определяем в каком словаре она находится
                for dict_name, dict_data in dictionaries_to_check.items():
                    if found_word in dict_data['words']:
                        results['dictionaries'][dict_name] = [found_word]

        self._word_check_cache.put(cache_key, results)
        return results

    def check_text(self, text: str) -> Dict:
        """
        Проверка текста по всем словарям

        Returns:
            Словарь с результатами проверки
        """
        import re

        # Извлекаем слова, состоящие из букв. Дефисы и апострофы допускаются только внутри слова.
        pattern = r'\b[a-zA-Zа-яёА-ЯЁ]+(?:[\'-][a-zA-Zа-яёА-ЯЁ]+)*\b'
        words = re.findall(pattern, text)
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

            if word_results['dictionaries']:
                # Слово найдено в каком-то словаре
                for dict_name, matched in word_results['dictionaries'].items():
                    if dict_name not in results['dictionaries']:
                        results['dictionaries'][dict_name] = []
                    results['dictionaries'][dict_name].append({
                        'word': word,
                        'count': sum(1 for w in words if w.lower() == word),
                        'found_via_morph': word_results['found_via_morph'],
                        'found_word': word_results['found_word']
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

        for dict_name in results['dictionaries'].keys():
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

    def save_user_dictionary(self, name: str, words: Set[str], mappings: Dict = None, 
                           category: str = None, description: str = None, 
                           overwrite: bool = False) -> str:
        """
        Сохранение пользовательского словаря в user_data
        
        Args:
            name: имя словаря (без префикса)
            words: множество слов
            mappings: словарь соответствий {слово: аналог}
            category: категория
            description: описание
            overwrite: перезаписывать если существует
            
        Returns:
            Имя сохраненного словаря (с префиксом user_ при необходимости)
        """
        # Подготавливаем имя файла
        safe_name = name.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
        filepath = self.user_data_dir / f"{safe_name}.json"
        
        # Если файл существует и не разрешено перезаписывать, добавляем счетчик
        original_filepath = filepath
        counter = 1
        while filepath.exists() and not overwrite:
            safe_name = f"{safe_name}_{counter}"
            filepath = self.user_data_dir / f"{safe_name}.json"
            counter += 1
        
        # Формируем имя словаря
        dict_name = safe_name
        if not dict_name.startswith('user_'):
            dict_name = f'user_{dict_name}'
        
        # Формируем метаданные
        dict_data = {
            'name': dict_name,
            'version': '1.0',
            'source': 'user',
            'generated_at': datetime.now().isoformat(),
            'words': sorted(list(words)),
            'mappings': mappings or {}
        }
        
        if category:
            dict_data['category'] = category
        if description:
            dict_data['description'] = description
        
        # Сохраняем JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dict_data, f, ensure_ascii=False, indent=2)
        
        # Добавляем в память
        self.dictionaries[dict_name] = dict_data
        
        print(f"Сохранен пользовательский словарь: {dict_name} ({len(words)} слов) в {filepath}")
        return dict_name

    def delete_user_dictionary(self, dict_name: str) -> bool:
        """
        Удаление пользовательского словаря
        
        Returns:
            True если удален, False если не найден или не пользовательский
        """
        if dict_name not in self.dictionaries:
            return False
        
        dict_info = self.dictionaries[dict_name]
        if dict_info.get('source') != 'user':
            return False
        
        # Находим файл
        filepath = None
        if 'filepath' in dict_info and dict_info['filepath']:
            filepath = Path(dict_info['filepath'])
        
        if not filepath or not filepath.exists():
            # Пытаемся найти по имени в пользовательской директории
            # Имя словаря в файле может храниться как dict_name или с префиксом user_
            possible_names = [dict_name, f"{dict_name}.json"]
            # Если dict_name начинается с user_, также ищем без префикса
            if dict_name.startswith('user_'):
                possible_names.append(dict_name[5:])
                possible_names.append(f"{dict_name[5:]}.json")
            
            for f in self.user_data_dir.glob('*.json'):
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        data = json.load(fp)
                        if data.get('name') == dict_name:
                            filepath = f
                            break
                except Exception:
                    continue
        
        # Если не нашли файл, всё равно удаляем из памяти
        if filepath and filepath.exists():
            try:
                filepath.unlink()
            except IsADirectoryError:
                # Если по какой-то причине получили директорию - пропускаем
                pass
        
        # Удаляем из памяти
        if dict_name in self.dictionaries:
            del self.dictionaries[dict_name]
            print(f"Удален пользовательский словарь: {dict_name}")
            return True
        
        return False

    def export_dictionary_to_xlsx(self, dict_name: str, filepath: Path) -> None:
        """
        Экспорт словаря в XLSX файл
        
        Args:
            dict_name: имя словаря
            filepath: путь для сохранения XLSX
        """
        if dict_name not in self.dictionaries:
            raise ValueError(f"Словарь '{dict_name}' не найден")
        
        dict_data = self.dictionaries[dict_name]
        
        # Используем DictionaryLoader.save_to_xlsx
        DictionaryLoader.save_to_xlsx(dict_data, filepath)
        
        print(f"Экспортирован словарь {dict_name} в {filepath}")

    def import_dictionary_from_xlsx(self, filepath: Path, name: str = None, 
                                   category: str = None, description: str = None,
                                   overwrite: bool = False) -> str:
        """
        Импорт словаря из XLSX файла
        
        Args:
            filepath: путь к XLSX файлу
            name: имя словаря (если None - из имени файла)
            category: категория (если None - из файла)
            description: описание (если None - из файла)
            overwrite: перезаписывать существующий
            
        Returns:
            Имя импортированного словаря
        """
        # Загружаем данные из XLSX
        xlsx_data = DictionaryLoader.load_from_xlsx(filepath)
        
        # Определяем имя
        if name:
            dict_name = name
        else:
            dict_name = filepath.stem
        
        # Берем category из XLSX если не передан
        if not category and 'category' in xlsx_data:
            category = xlsx_data['category']
        
        # Берем description из XLSX если не передан
        if not description and 'description' in xlsx_data:
            description = xlsx_data['description']
        
        # Сохраняем как пользовательский словарь
        return self.save_user_dictionary(
            name=dict_name,
            words=xlsx_data['words'],
            mappings=xlsx_data.get('mappings', {}),
            category=category,
            description=description,
            overwrite=overwrite
        )
    
    def get_cache_stats(self) -> dict:
        """
        Get cache and bloom filter statistics for monitoring.
        
        Returns:
            Dictionary with cache and bloom filter stats
        """
        # Calculate total bloom filter memory usage
        total_bloom_memory_mb = 0
        bloom_filter_details = {}
        for dict_name, bloom in self._bloom_filters.items():
            stats = bloom.get_stats()
            bloom_filter_details[dict_name] = stats
            total_bloom_memory_mb += stats['size_mb']
        
        return {
            'word_check_cache_size': len(self._word_check_cache),
            'word_check_cache_max': self.MAX_WORD_CHECK_CACHE,
            'morph_analyzer_stats': self.morph_analyzer.get_cache_stats() if self.morph_analyzer else {},
            'bloom_filters': {
                'count': len(self._bloom_filters),
                'total_memory_mb': round(total_bloom_memory_mb, 2),
                'dictionaries': bloom_filter_details
            }
        }
    
    def clear_caches(self):
        """Clear all caches."""
        self._word_check_cache.clear()
        if self.morph_analyzer:
            self.morph_analyzer.clear_caches()
