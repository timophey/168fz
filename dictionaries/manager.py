"""
Менеджер словарей - управление загрузкой и проверкой слов
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple
from .loader import DictionaryLoader


class DictionaryManager:
    """Управление словарями и проверка слов"""

    def __init__(self, dictionaries_dir: Path = None, sync_metadata: Dict = None, category_mapping_file: Path = None, user_data_dir: Path = None):
        """
        Инициализация менеджера словарей

        Args:
            dictionaries_dir: Путь к папке со словарями (официальные)
            sync_metadata: Метаданные синхронизации от DictionarySynchronizer
            category_mapping_file: Путь к файлу с маппингом словарей → категорий
            user_data_dir: Путь к папке с пользовательскими словарями
        """
        self.dictionaries_dir = dictionaries_dir or Path('dictionaries/data')
        self.user_data_dir = user_data_dir or Path('dictionaries/user_data')
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
        """Загрузка словарей из папок data и user_data"""
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
                        print(f"Загружен словарь: {dict_name} ({len(dict_data['words'])} слов) [официальный]")
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
                        print(f"Загружен пользовательский словарь: {dict_name} ({len(dict_data['words'])} слов)")
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

    def check_word(self, word: str, dictionary_names: List[str] = None) -> Dict[str, List[str]]:
        """
        Проверка слова по указанным словарям (или всем по умолчанию)

        Args:
            word: слово для проверки
            dictionary_names: список имен словарей для проверки (None = все словари)

        Returns:
            Словарь с результатами: {'dictionary_name': [matched_words]}
        """
        word_lower = word.lower().strip()
        results = {}

        # Определяем, какие словари проверять
        dictionaries_to_check = self.dictionaries
        if dictionary_names:
            # Фильтруем только указанные словари
            dictionaries_to_check = {k: v for k, v in self.dictionaries.items() if k in dictionary_names}

        for dict_name, dict_data in dictionaries_to_check.items():
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
        filepath = Path(dict_info.get('filepath', ''))
        if not filepath.exists():
            # Пытаемся найти по имени
            for f in self.user_data_dir.glob('*.json'):
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        data = json.load(fp)
                        if data.get('name') == dict_name:
                            filepath = f
                            break
                except:
                    pass
        
        # Удаляем файл
        if filepath.exists():
            filepath.unlink()
        
        # Удаляем из памяти
        del self.dictionaries[dict_name]
        
        print(f"Удален пользовательский словарь: {dict_name}")
        return True

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
