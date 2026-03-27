"""
Синхронизатор официальных словарей с локальной базой
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import requests

from .sources import DictionarySource, OFFICIAL_DICTIONARIES, get_dictionary_source
from .real_sources import (
    download_from_github,
    download_from_wiktionary,
    download_from_opencorpora,
    download_hunspell_dictionary,
    extract_words_from_text,
    parse_dictionary_file,
    GITHUB_RAW_URLS,
    HUNSPELL_URLS,
    OPENCORPORA_URLS
)
from dictionaries.loader import DictionaryLoader


class DictionarySynchronizer:
    """Синхронизация словарей с официальными источниками"""

    # Маппинг старых имен файлов на новые (для совместимости метаданных)
    NAME_MAPPING = {
        'ru_words_github': 'нормативный_словарь',
        'foreign_words_github': 'иностранные_слова',
        'obscene_github': 'запрещенные_слова',
        'hunspell_en': 'allowed_foreign',
        'inostrannye_slova': 'иностранные_слова',  # старый вариант
    }

    def __init__(
        self,
        data_dir: Path = Path('dictionaries/data'),
        cache_dir: Path = Path('sync/cache'),
        check_interval: int = 86400  # 24 часа в секундах
    ):
        """
        Инициализация синхронизатора

        Args:
            data_dir: Папка для хранения словарей
            cache_dir: Папка для кэша и временных файлов
            check_interval: Интервал проверки обновлений в секундах
        """
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self.check_interval = check_interval

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Файл метаданных синхронизации
        self.metadata_file = self.cache_dir / 'sync_metadata.json'
        self.metadata = self._load_metadata()
        self._migrate_metadata()

    def _load_metadata(self) -> Dict:
        """Загрузка метаданных синхронизации"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'dictionaries': {}, 'last_full_sync': None}

    def _migrate_metadata(self):
        """Миграция метаданных - обновление имен словарей после переименования"""
        if 'dictionaries' in self.metadata:
            migrated = {}
            for old_name, meta in self.metadata['dictionaries'].items():
                # Если старое имя есть в маппинге, используем новое
                new_name = self.NAME_MAPPING.get(old_name, old_name)
                migrated[new_name] = meta
            self.metadata['dictionaries'] = migrated
            self._save_metadata()

    def _save_metadata(self):
        """Сохранение метаданных синхронизации"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def needs_update(self, dict_name: str, source: DictionarySource) -> bool:
        """
        Проверка необходимости обновления словаря

        Returns:
            True, если словарь нужно обновить
        """
        # Локальные словари требуют создания метаданных при первом запуске
        if source.method == 'local':
            return dict_name not in self.metadata['dictionaries']

        # Если словарь еще не синхронизирован
        if dict_name not in self.metadata['dictionaries']:
            return True

        dict_meta = self.metadata['dictionaries'][dict_name]

        # Проверяем время последней проверки
        last_check = datetime.fromisoformat(dict_meta.get('last_check', '2000-01-01'))
        if datetime.now() - last_check > timedelta(seconds=self.check_interval):
            return True

        # Проверяем версию, если источник предоставляет update_url или download_url
        if hasattr(source, 'update_url') and source.update_url:
            local_version = dict_meta.get('version', '')
            remote_version = self._check_remote_version(source)
            return remote_version and remote_version != local_version
        elif hasattr(source, 'download_url') and source.download_url:
            # Для источников с прямым download_url проверяем по Last-Modified
            local_check = dict_meta.get('last_check', '')
            remote_check = self._check_remote_version(source)
            return remote_check and local_check != remote_check

        return False

    def _check_remote_version(self, source: DictionarySource) -> Optional[str]:
        """Проверка версии на удаленном источнике"""
        try:
            # Пробуем получить информацию о версии
            # Это зависит от конкретного источника
            if 'gramota.ru' in source.url:
                # Для Грамота.ру версия может быть в заголовках или в дате обновления
                response = requests.head(source.url, timeout=5)
                last_modified = response.headers.get('Last-Modified')
                if last_modified:
                    return last_modified
            return None
        except Exception as e:
            print(f"Ошибка проверки версии для {source.name}: {e}")
            return None

    def sync_dictionary(self, dict_name: str, force: bool = False) -> Tuple[bool, str]:
        """
        Синхронизация одного словаря

        Args:
            dict_name: Имя словаря из OFFICIAL_DICTIONARIES
            force: Принудительная синхронизация

        Returns:
            (успех, сообщение)
        """
        source = get_dictionary_source(dict_name)
        if not source:
            return False, f"Источник '{dict_name}' не найден"

        if not force and not self.needs_update(dict_name, source):
            return True, f"Словарь '{source.official_name}' актуален"

        print(f"Синхронизация словаря: {source.official_name}")
        print(f"Источник: {source.url}")
        print(f"Институт: {source.institution}")

        try:
            words = []

            # Обработка локальных словарей (method='local')
            if source.method == 'local':
                if source.fallback_file:
                    fallback_path = Path(source.fallback_file)
                    if fallback_path.exists():
                        print(f"Используем локальный файл: {fallback_path}")
                        words = self._load_fallback_dictionary(fallback_path)
                    else:
                        return False, f"Локальный файл не найден: {fallback_path}"
                else:
                    return False, "Для локального словаря не указан fallback_file"
            else:
                # Загрузка словаря в зависимости от формата
                words = self._download_dictionary(source)

                # Если не удалось загрузить с официального источника, пробуем fallback
                if not words and source.fallback_file:
                    fallback_path = Path(source.fallback_file)
                    if fallback_path.exists():
                        print(f"Используем fallback: {fallback_path}")
                        words = self._load_fallback_dictionary(fallback_path)

            if not words:
                return False, "Не удалось извлечь слова из источника (даже с fallback)"

            # Сохранение в локальную папку
            output_file = self.data_dir / f"{source.name}.json"
            self._save_dictionary(words, source, output_file)

            # Обновление метаданных
            self.metadata['dictionaries'][dict_name] = {
                'name': dict_name,
                'official_name': source.official_name,
                'version': source.version,
                'last_sync': datetime.now().isoformat(),
                'last_check': datetime.now().isoformat(),
                'file': str(output_file),
                'word_count': len(words),
                'source_url': source.url
            }
            self._save_metadata()

            return True, f"Словарь '{source.official_name}' успешно синхронизирован ({len(words)} слов)"

        except Exception as e:
            return False, f"Ошибка синхронизации: {e}"

    def _download_dictionary(self, source: DictionarySource) -> List[str]:
        """
        Загрузка словаря из источника

        Returns:
            Список слов
        """
        # Используем специализированные методы для реальных источников
        if source.parser == 'github' and source.download_url:
            return download_from_github(source.download_url)
        elif source.parser == 'hunspell' and source.download_url:
            return download_hunspell_dictionary(source.download_url)
        elif source.parser == 'opencorpora' and source.download_url:
            return download_from_opencorpora()
        elif source.parser == 'json' and source.download_url:
            # Простой JSON
            try:
                import requests
                response = requests.get(source.download_url, timeout=30)
                response.raise_for_status()
                import json
                data = json.loads(response.text)
                if isinstance(data, list):
                    return [str(w).lower() for w in data if isinstance(w, str)]
                elif isinstance(data, dict) and 'words' in data:
                    return [str(w).lower() for w in data['words'] if isinstance(w, str)]
            except:
                pass
        elif source.parser == 'txt' and source.download_url:
            try:
                import requests
                response = requests.get(source.download_url, timeout=30)
                response.raise_for_status()
                return extract_words_from_text(response.text)
            except:
                pass

        # Для legacy источников используем старые методы
        domain = urlparse(source.url).netloc if source.url else ''

        if 'gramota.ru' in domain:
            return self._download_from_gramota(source)
        elif 'iling-ran.ru' in domain:
            return self._download_from_iling(source)
        elif 'spbu.ru' in domain:
            return self._download_from_spbu(source)
        else:
            # Общий метод
            return self._download_generic(source)

    def _download_from_gramota(self, source: DictionarySource) -> List[str]:
        """Загрузка словаря с портала Грамота.ру"""
        # Грамота.ру не предоставляет прямого API для скачивания
        # Нужно использовать парсинг HTML или официальные публикации

        words = set()

        try:
            # Пробуем получить доступ к словарю через веб-интерфейс
            response = requests.get(source.url, timeout=10)
            response.raise_for_status()

            # Парсим HTML для извлечения слов
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем элементы, содержащие слова
            # Это зависит от структуры страницы Грамота.ру
            for element in soup.find_all(['span', 'div', 'td'], class_=['word', 'term', 'entry']):
                text = element.get_text(strip=True)
                if text and len(text) > 1 and text.isalpha():
                    words.add(text.lower())

            # Если не нашли через классы, ищем по паттерну
            if not words:
                import re
                # Ищем последовательности кириллических символов
                found = re.findall(r'[а-яёА-ЯЁ]{2,}', response.text)
                words.update(w.lower() for w in found if len(w) > 2)

        except Exception as e:
            print(f"Ошибка при загрузке с Грамота.ру: {e}")

        return sorted(list(words))

    def _download_from_iling(self, source: DictionarySource) -> List[str]:
        """Загрузка словаря с сайта Института лингвистических исследований РАН"""
        words = set()

        try:
            response = requests.get(source.url, timeout=10)
            response.raise_for_status()

            # Парсим HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем ссылки на файлы словарей
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(ext in href.lower() for ext in ['.txt', '.csv', '.json', '.pdf']):
                    # Пробуем скачать файл
                    file_url = href if href.startswith('http') else f"{source.url.rstrip('/')}/{href.lstrip('/')}"
                    words.update(self._download_file(file_url))

        except Exception as e:
            print(f"Ошибка при загрузке с ИЛИ РАН: {e}")

        return sorted(list(words))

    def _download_from_spbu(self, source: DictionarySource) -> List[str]:
        """Загрузка словаря с сайта СПбГУ"""
        # Аналогично, требуется парсинг конкретного сайта
        return self._download_generic(source)

    def _download_generic(self, source: DictionarySource) -> List[str]:
        """Общий метод загрузки словаря"""
        words = set()

        try:
            response = requests.get(source.url, timeout=10)
            response.raise_for_status()

            # Пробуем определить формат по содержимому
            content = response.text

            if source.format == 'json' or 'application/json' in response.headers.get('content-type', ''):
                data = json.loads(content)
                if isinstance(data, list):
                    words.update(str(w).lower() for w in data)
                elif isinstance(data, dict) and 'words' in data:
                    words.update(str(w).lower() for w in data['words'])
            else:
                # Текстовый формат - извлекаем слова
                import re
                found = re.findall(r'[а-яёА-ЯЁ]{2,}|[a-zA-Z]{2,}', content)
                words.update(w.lower() for w in found if len(w) > 2)

        except Exception as e:
            print(f"Ошибка при общей загрузке: {e}")

        return sorted(list(words))

    def _download_file(self, url: str) -> List[str]:
        """Загрузка и парсинг файла словаря"""
        words = set()

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            ext = Path(urlparse(url).path).suffix.lower()

            if ext == '.txt':
                words.update(line.strip().lower() for line in response.text.split('\n') if line.strip())
            elif ext == '.csv':
                import csv
                from io import StringIO
                reader = csv.reader(StringIO(response.text))
                for row in reader:
                    for cell in row:
                        if cell.strip():
                            words.add(cell.strip().lower())
            elif ext == '.json':
                data = json.loads(response.text)
                if isinstance(data, list):
                    words.update(str(w).lower() for w in data)
                elif isinstance(data, dict) and 'words' in data:
                    words.update(str(w).lower() for w in data['words'])

        except Exception as e:
            print(f"Ошибка загрузки файла {url}: {e}")

        return sorted(list(words))

    def _load_fallback_dictionary(self, fallback_path: Path) -> List[str]:
        """Загрузка словаря из fallback файла"""
        try:
            dict_data = DictionaryLoader.load_dictionary(fallback_path)
            if isinstance(dict_data, dict) and 'words' in dict_data:
                return list(dict_data['words'])
            return []
        except Exception as e:
            print(f"Ошибка загрузки fallback словаря: {e}")
            return []

    def _save_dictionary(self, words: List[str], source: DictionarySource, output_file: Path):
        """Сохранение словаря в формате JSON"""
        dictionary_data = {
            'name': source.name,
            'official_name': source.official_name,
            'version': source.version,
            'source': source.url,
            'institution': source.institution,
            'license': source.license,
            'generated_at': datetime.now().isoformat(),
            'word_count': len(words),
            'words': words
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dictionary_data, f, ensure_ascii=False, indent=2)

    def sync_all(self, force: bool = False) -> Dict[str, Tuple[bool, str]]:
        """
        Синхронизация всех словарей

        Returns:
            Словарь {dict_name: (успех, сообщение)}
        """
        results = {}

        for dict_name, source in OFFICIAL_DICTIONARIES.items():
            success, message = self.sync_dictionary(dict_name, force)
            results[dict_name] = (success, message)
            print(f"{'✓' if success else '✗'} {message}")

        # Обновляем общее время последней синхронизации
        if any(success for success, _ in results.values()):
            self.metadata['last_full_sync'] = datetime.now().isoformat()
            self._save_metadata()

        return results

    def get_sync_status(self) -> Dict:
        """Получение статуса синхронизации всех словарей"""
        status = {
            'last_full_sync': self.metadata.get('last_full_sync'),
            'dictionaries': {}
        }

        for dict_name, source in OFFICIAL_DICTIONARIES.items():
            if dict_name in self.metadata['dictionaries']:
                meta = self.metadata['dictionaries'][dict_name]
                status['dictionaries'][dict_name] = {
                    'synced': True,
                    'last_sync': meta.get('last_sync'),
                    'version': meta.get('version'),
                    'word_count': meta.get('word_count'),
                    'file': meta.get('file')
                }
            else:
                status['dictionaries'][dict_name] = {
                    'synced': False,
                    'source_url': source.url,
                    'official_name': source.official_name
                }

        return status


def sync_official_dictionaries(force: bool = False) -> Dict[str, Tuple[bool, str]]:
    """
    Быстрая синхронизация всех официальных словарей

    Args:
        force: Принудительная перезагрузка всех словарей

    Returns:
        Результаты синхронизации
    """
    synchronizer = DictionarySynchronizer()
    return synchronizer.sync_all(force=force)
