"""
Реальные источники русских словарей, доступные для скачивания

Исследование источников:

1. Wiktionary (Викисловарь) - открытый, можно парсить через API
2. OpenCorpora - открытый корпус русского языка
3. GitHub репозитории с выгрузками
4. Официальные дампы (если доступны)
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from pathlib import Path


@dataclass
class RealDictionarySource:
    """Конфигурация реального источника словаря"""
    name: str
    description: str
    url: str
    format: str  # json, csv, txt, xml, sqlite
    method: str  # api, download, parse
    license: str
    institution: str = ""
    fallback_file: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'url': self.url,
            'format': self.format,
            'method': self.method,
            'license': self.license,
            'institution': self.institution,
            'fallback_file': self.fallback_file
        }


# Реальные источники, которые можно использовать

REAL_SOURCES: Dict[str, RealDictionarySource] = {
    # 1. Wiktionary (Викисловарь) - через API
    'wiktionary_ru': RealDictionarySource(
        name='wiktionary_ru',
        description='Викисловарь - открытый словарь русского языка. Можно парсить через MediaWiki API или использовать дампы.',
        url='https://ru.wiktionary.org/wiki/Служебная:Все_страницы',
        format='html/json',
        method='api',
        license='CC BY-SA 3.0',
        institution='Фонд Викимедиа',
        fallback_file='dictionaries/data/нормативный_словарь.json'
    ),

    # 2. OpenCorpora - открытый корпус русского языка
    'opencorpora': RealDictionarySource(
        name='opencorpora',
        description='OpenCorpora - открытый размеченный корпус русского языка с лемматизацией и словарями.',
        url='https://opencorpora.org/dict.php',
        format='xml',
        method='download',
        license='CC BY-SA 3.0',
        institution='OpenCorpora',
        fallback_file='dictionaries/data/нормативный_словарь.json'
    ),

    # 3. Russian National Corpus (РНК) - Национальный корпус русского языка
    'ruscorpora': RealDictionarySource(
        name='ruscorpora',
        description='Национальный корпус русского языка. Содержит лексические ресурсы.',
        url='https://ruscorpora.ru/',
        format='xml/json',
        method='api',
        license='Требуется регистрация',
        institution='Институт русского языка им. В. В. Виноградова РАН',
        fallback_file='dictionaries/data/нормативный_словарь.json'
    ),

    # 4. GitHub - выгрузки словарей
    'github_ru_wordlist': RealDictionarySource(
        name='github_ru_wordlist',
        description='Списки русских слов из открытых репозиториев GitHub.',
        url='https://github.com/danakt/russian-words',
        format='txt',
        method='download',
        license='MIT/Apache 2.0 (зависит от репозитория)',
        institution='Сообщество',
        fallback_file='dictionaries/data/нормативный_словарь.json'
    ),

    # 5. Hunspell словари (используются в LibreOffice, Firefox)
    'hunspell_ru': RealDictionarySource(
        name='hunspell_ru',
        description='Словари Hunspell для русского языка (орфография).',
        url='https://github.com/LibreOffice/dictionaries',
        format='aff/dic',
        method='download',
        license='MPL/LGPL',
        institution='Сообщество LibreOffice',
        fallback_file='dictionaries/data/нормативный_словарь.json'
    ),

    # 6. Аспирант - словари на основе корпуса
    'aspirant': RealDictionarySource(
        name='aspirant',
        description='Словари на основе корпуса "Аспирант" (открытый корпус).',
        url='https://github.com/aspirantus/aspirant-corpus',
        format='json/csv',
        method='download',
        license='CC BY-SA 4.0',
        institution='Сообщество',
        fallback_file='dictionaries/data/нормативный_словарь.json'
    ),

    # 7. Тезаурус русского языка (открытые версии)
    'thesaurus_ru': RealDictionarySource(
        name='thesaurus_ru',
        description='Тезаурус русского языка, синонимы, антонимы.',
        url='https://github.com/akutuzov/ru_thesaurus',
        format='json',
        method='download',
        license='CC BY-SA 4.0',
        institution='Сообщество',
        fallback_file='dictionaries/data/нормативный_словарь.json'
    ),

    # 8. Словарь иностранных слов (открытые источники)
    'foreign_words_ru': RealDictionarySource(
        name='foreign_words_ru',
        description='Словарь иностранных слов, используемых в русском языке (открытые источники).',
        url='https://github.com/ikimrus/foreign-words',
        format='json/txt',
        method='download',
        license='MIT',
        institution='Сообщество',
        fallback_file='dictionaries/data/иностранные_слова.json'
    ),

    # 9. Словарь запрещенных слов (на основе открытых списков)
    # Внимание: использование таких словарей требует осторожности
    'obscene_wordlist': RealDictionarySource(
        name='obscene_wordlist',
        description='Открытые списки обсценной лексики (для исследовательских целей).',
        url='https://github.com/LTD-Beget/badwords',
        format='txt/json',
        method='download',
        license='MIT',
        institution='Сообщество',
        fallback_file='dictionaries/data/запрещенные_слова.json'
    ),

    # 10. Словари от Яндекс (если доступны)
    'yandex_dictionaries': RealDictionarySource(
        name='yandex_dictionaries',
        description='Словари от Яндекс.Словарей (если есть API или выгрузки).',
        url='https://yandex.ru/dictionaries/',
        format='api',
        method='api',
        license='Требуется согласование',
        institution='Яндекс',
        fallback_file='dictionaries/data/нормативный_словарь.json'
    )
}


def get_real_source(name: str) -> Optional[RealDictionarySource]:
    """Получение реального источника по имени"""
    return REAL_SOURCES.get(name)


def list_real_sources() -> List[Dict]:
    """Список доступных реальных источников"""
    return [source.to_dict() for source in REAL_SOURCES.values()]


# Специальные методы загрузки для разных источников

def download_from_github(url: str, filepath: Path = None) -> List[str]:
    """
    Скачивание словаря с GitHub

    Args:
        url: URL репозитория или raw-файла
        filepath: Куда сохранить (если None - временный файл)

    Returns:
        Список слов
    """
    import tempfile
    import zipfile
    import io

    # Если это raw-файл
    if 'raw.githubusercontent.com' in url or url.endswith(('.txt', '.json', '.csv')):
        try:
            import requests
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            if filepath:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return parse_dictionary_file(filepath)

            # Парсим на лету
            content = response.text
            return extract_words_from_text(content)

        except Exception as e:
            print(f"Ошибка загрузки с GitHub: {e}")
            return []

    # Если это репозиторий - нужно клонировать или скачать архив
    # Преобразуем URL в raw для основных файлов
    if 'github.com' in url and not 'raw.githubusercontent.com' in url:
        # Пробуем найти основные файлы словарей
        # Например: https://github.com/danakt/russian-words
        # raw: https://raw.githubusercontent.com/danakt/russian-words/master/russian.txt

        parts = url.split('/')
        if len(parts) >= 5:
            owner = parts[3]
            repo = parts[4]
            # Пробуем стандартные пути
            possible_files = [
                f'https://raw.githubusercontent.com/{owner}/{repo}/master/russian.txt',
                f'https://raw.githubusercontent.com/{owner}/{repo}/main/russian.txt',
                f'https://raw.githubusercontent.com/{owner}/{repo}/master/words.txt',
                f'https://raw.githubusercontent.com/{owner}/{repo}/main/words.txt',
                f'https://raw.githubusercontent.com/{owner}/{repo}/master/dict.txt',
            ]

            for raw_url in possible_files:
                try:
                    import requests
                    response = requests.get(raw_url, timeout=5)
                    if response.status_code == 200:
                        return extract_words_from_text(response.text)
                except:
                    continue

    return []


def download_from_wiktionary(lang: str = 'ru', category: str = None) -> List[str]:
    """
    Скачивание слов из Викисловаря через API

    Args:
        lang: Язык (ru, en, etc.)
        category: Категория слов (глаголы, существительные, etc.)

    Returns:
        Список слов
    """
    import requests
    import xml.etree.ElementTree as ET

    words = set()

    try:
        # Используем MediaWiki API
        api_url = f'https://{lang}.wiktionary.org/w/api.php'

        # Получаем все страницы в категории (если указана)
        params = {
            'action': 'query',
            'list': 'allpages',
            'aplimit': 'max',
            'format': 'xml'
        }

        if category:
            params['apnamespace'] = '0'  # Основное пространство имен

        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()

        # Парсим XML
        root = ET.fromstring(response.text)

        for page in root.findall('.//page'):
            title = page.get('title')
            if title and len(title) > 1:
                words.add(title.lower())

        # Можно также парсить категории частей речи
        # Но это сложнее и требует множества запросов

    except Exception as e:
        print(f"Ошибка при загрузке с Викисловаря: {e}")

    return sorted(list(words))


def download_from_opencorpora() -> List[str]:
    """
    Скачивание словарей с OpenCorpora

    Returns:
        Список слов
    """
    import requests
    import xml.etree.ElementTree as ET

    words = set()

    try:
        # Скачиваем основной словарь
        url = 'https://opencorpora.org/files/export/opencorpora-export.zip'
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Распаковываем в памяти
        import zipfile
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # Ищем файлы с леммами
            for filename in z.namelist():
                if 'lemmas' in filename.lower() or 'dict' in filename.lower():
                    with z.open(filename) as f:
                        content = f.read().decode('utf-8')
                        # Парсим XML
                        try:
                            root = ET.fromstring(content)
                            for lemma in root.findall('.//lemma'):
                                word = lemma.get('name') or lemma.get('id')
                                if word:
                                    words.add(word.lower())
                        except:
                            # Простой парсинг по строкам
                            for line in content.split('\n'):
                                if '\t' in line:
                                    word = line.split('\t')[0]
                                    if word:
                                        words.add(word.lower())

    except Exception as e:
        print(f"Ошибка при загрузке с OpenCorpora: {e}")

    return sorted(list(words))


def download_hunspell_dictionary(url: str) -> List[str]:
    """
    Скачивание и конвертация словаря Hunspell

    Args:
        url: URL к .dic файлу

    Returns:
        Список слов
    """
    try:
        import requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        words = []
        for line in response.text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Формат Hunspell: слово/количество_форм
                word = line.split('/')[0].strip()
                if word:
                    words.append(word.lower())

        return sorted(list(set(words)))

    except Exception as e:
        print(f"Ошибка при загрузке Hunspell словаря: {e}")
        return []


def extract_words_from_text(text: str) -> List[str]:
    """
    Извлечение уникальных слов из текста

    Args:
        text: Текст для обработки

    Returns:
        Отсортированный список уникальных слов
    """
    import re

    # Находим слова (кириллица, латиница)
    words = re.findall(r'[а-яёА-ЯЁa-zA-Z]{2,}', text)

    # Нормализуем
    unique_words = set(w.lower() for w in words if len(w) > 1)

    return sorted(list(unique_words))


def parse_dictionary_file(filepath: Path) -> List[str]:
    """
    Парсинг файла словаря

    Args:
        filepath: Путь к файлу

    Returns:
        Список слов
    """
    if not filepath.exists():
        return []

    ext = filepath.suffix.lower()

    if ext == '.txt':
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return extract_words_from_text(f.read())

    elif ext == '.json':
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(w).lower() for w in data if isinstance(w, str)]
            elif isinstance(data, dict) and 'words' in data:
                return [str(w).lower() for w in data['words'] if isinstance(w, str)]

    elif ext == '.csv':
        import csv
        words = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                for cell in row:
                    if cell.strip():
                        words.append(cell.strip().lower())
        return sorted(list(set(words)))

    elif ext == '.xml':
        import xml.etree.ElementTree as ET
        words = []
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            # Ищем элементы с словами (зависит от структуры)
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    words.append(elem.text.strip().lower())
        except:
            pass
        return sorted(list(set(words)))

    return []


# Примеры реальных URL для скачивания

GITHUB_RAW_URLS = {
    'russian_words': 'https://raw.githubusercontent.com/danakt/russian-words/master/russian.txt',
    'russian_obscene': 'https://raw.githubusercontent.com/LTD-Beget/badwords/master/russian.txt',
    'common_words': 'https://raw.githubusercontent.com/martinsv/wordlist/master/russian.txt',
}

HUNSPELL_URLS = {
    'ru_RU': 'https://raw.githubusercontent.com/LibreOffice/dictionaries/master/ru_RU/ru_RU.dic',
}

OPENCORPORA_URLS = {
    'dict': 'https://opencorpora.org/files/export/opencorpora-export.zip',
}
