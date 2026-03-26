"""
Конфигурация источников словарей согласно закону № 168-ФЗ

Закон требует использования официальных словарей, но не все из них доступны для автоматической загрузки.
Поэтому приложение поддерживает два типа источников:

1. ОФИЦИАЛЬНЫЕ (официальные институты) - требуют ручной настройки и согласования
2. РЕАЛЬНЫЕ (доступные открытые источники) - можно скачивать автоматически

Для production рекомендуется использовать официальные источники, но если они недоступны,
можно использовать открытые аналоги с fallback-механизмом.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from pathlib import Path


@dataclass
class DictionarySource:
    """Конфигурация источника словаря"""
    name: str
    official_name: str
    description: str
    url: str
    format: str  # json, csv, txt, xml, html
    method: str  # api, download, parse, custom
    license: str
    institution: str = ""
    version: str = "2024"
    last_updated: Optional[str] = None
    fallback_file: Optional[str] = None
    # Дополнительные параметры для загрузки
    download_url: Optional[str] = None  # Прямой URL для скачивания
    api_endpoint: Optional[str] = None  # API endpoint
    parser: Optional[str] = None  # Имя парсера в real_sources

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'official_name': self.official_name,
            'description': self.description,
            'url': self.url,
            'format': self.format,
            'method': self.method,
            'license': self.license,
            'institution': self.institution,
            'version': self.version,
            'last_updated': self.last_updated,
            'fallback_file': self.fallback_file,
            'download_url': self.download_url,
            'api_endpoint': self.api_endpoint,
            'parser': self.parser
        }


# ============================================================================
# РЕАЛЬНЫЕ ИСТОЧНИКИ - РАБОТАЮЩИЕ И ДОСТУПНЫЕ
# ============================================================================

OFFICIAL_DICTIONARIES: Dict[str, DictionarySource] = {
    # 1. Русские слова - GitHub (открытый источник)
    'ru_words_github': DictionarySource(
        name='ru_words_github',
        official_name='Список русских слов (GitHub)',
        description='Открытый список русских слов из репозитория danakt/russian-words. Содержит ~200 000 слов.',
        url='https://github.com/danakt/russian-words',
        format='txt',
        method='download',
        license='MIT',
        institution='Сообщество (danakt)',
        version='2024',
        download_url='https://raw.githubusercontent.com/danakt/russian-words/master/russian.txt',
        fallback_file='dictionaries/data/нормативный_словарь.json',
        parser='github'
    ),

    # 2. Словарь Hunspell (используется в LibreOffice, Firefox)
    'hunspell_ru': DictionarySource(
        name='hunspell_ru',
        official_name='Hunspell словарь русского языка',
        description='Орфографический словарь Hunspell для русского языка. Используется в LibreOffice, Firefox, Chrome. Содержит ~200 000 слов.',
        url='https://github.com/LibreOffice/dictionaries',
        format='dic',
        method='download',
        license='MPL/LGPL',
        institution='Сообщество LibreOffice',
        version='2024',
        download_url='https://raw.githubusercontent.com/LibreOffice/dictionaries/master/ru_RU/ru_RU.dic',
        fallback_file='dictionaries/data/нормативный_словарь.json',
        parser='hunspell'
    ),

    # 3. OpenCorpora - открытый корпус
    'opencorpora': DictionarySource(
        name='opencorpora',
        official_name='OpenCorpora словарь',
        description='Открытый размеченный корпус русского языка с лемматизацией. Содержит ~500 000 словоформ.',
        url='https://opencorpora.org/',
        format='xml',
        method='download',
        license='CC BY-SA 3.0',
        institution='OpenCorpora',
        version='2024',
        download_url='https://opencorpora.org/files/export/opencorpora-export.zip',
        fallback_file='dictionaries/data/нормативный_словарь.json',
        parser='opencorpora'
    ),

    # 4. Словарь иностранных слов - GitHub
    'foreign_words_github': DictionarySource(
        name='foreign_words_github',
        official_name='Словарь иностранных слов (GitHub)',
        description='Открытый список иностранных слов, используемых в русском языке.',
        url='https://github.com/ikimrus/foreign-words',
        format='json',
        method='download',
        license='MIT',
        institution='Сообщество',
        version='2024',
        download_url='https://raw.githubusercontent.com/ikimrus/foreign-words/master/foreign-words.json',
        fallback_file='dictionaries/data/иностранные_слова.json',
        parser='json'
    ),

    # 5. Список обсценной лексики (исследовательский)
    'obscene_github': DictionarySource(
        name='obscene_github',
        official_name='Список обсценной лексики (GitHub)',
        description='Открытый список русских нецензурных слов (для исследовательских целей).',
        url='https://github.com/LTD-Beget/badwords',
        format='txt',
        method='download',
        license='MIT',
        institution='Сообщество',
        version='2024',
        download_url='https://raw.githubusercontent.com/LTD-Beget/badwords/master/russian.txt',
        fallback_file='dictionaries/data/запрещенные_слова.json',
        parser='txt'
    ),

    # 6. Русский тезаурус (синонимы)
    'thesaurus_github': DictionarySource(
        name='thesaurus_github',
        official_name='Русский тезаурус (GitHub)',
        description='Открытый тезаурус русского языка с синонимами и антонимами.',
        url='https://github.com/akutuzov/ru_thesaurus',
        format='json',
        method='download',
        license='CC BY-SA 4.0',
        institution='Сообщество',
        version='2024',
        download_url='https://raw.githubusercontent.com/akutuzov/ru_thesaurus/master/ru_thesaurus.json',
        fallback_file='dictionaries/data/нормативный_словарь.json',
        parser='json'
    ),

    # 7. Hunspell для иностранных слов (дополнительно)
    'hunspell_en': DictionarySource(
        name='hunspell_en',
        official_name='Hunspell словарь английского языка',
        description='Словарь английских слов для проверки иностранной лексики.',
        url='https://github.com/LibreOffice/dictionaries',
        format='dic',
        method='download',
        license='MPL/LGPL',
        institution='Сообщество LibreOffice',
        version='2024',
        download_url='https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en_US/en_US.dic',
        fallback_file='dictionaries/data/иностранные_слова.json',
        parser='hunspell'
    ),
}

# ============================================================================
# ОФИЦИАЛЬНЫЕ ИСТОЧНИКИ (если будут доступны)
# ============================================================================

LEGACY_OFFICIAL_SOURCES: Dict[str, DictionarySource] = {
    # Эти источники официальны, но сейчас недоступны для автоматической загрузки
    'gramota_ru': DictionarySource(
        name='gramota_ru',
        official_name='Грамота.ру',
        description='Официальная справочная система. Требует ручного извлечения или коммерческой лицензии.',
        url='https://gramota.ru/',
        format='html',
        method='custom',
        license='Требуется согласование',
        institution='Институт русского языка им. В. В. Виноградова РАН',
        fallback_file='dictionaries/data/нормативный_словарь.json'
    ),

    'opencorpora_official': DictionarySource(
        name='opencorpora_official',
        official_name='OpenCorpora (официальный)',
        description='Официальный корпус русского языка. Доступен для скачивания вручную.',
        url='https://opencorpora.org/',
        format='xml',
        method='download',
        license='CC BY-SA 3.0',
        institution='OpenCorpora',
        download_url='https://opencorpora.org/files/export/opencorpora-export.zip',
        fallback_file='dictionaries/data/нормативный_словарь.json',
        parser='opencorpora'
    ),
}


def get_dictionary_source(name: str) -> Optional[DictionarySource]:
    """Получение источника словаря по имени (сначала ищем в реальных)"""
    return OFFICIAL_DICTIONARIES.get(name) or LEGACY_OFFICIAL_SOURCES.get(name)


def list_available_sources() -> Dict[str, List[Dict]]:
    """Список всех доступных источников"""
    return {
        'real': [s.to_dict() for s in OFFICIAL_DICTIONARIES.values()],
        'legacy': [s.to_dict() for s in LEGACY_OFFICIAL_SOURCES.values()]
    }


def save_sources_config(config_path: Path = Path('sync/sources_config.json')):
    """Сохранение конфигурации источников в файл"""
    import json
    config = {
        'real_sources': [s.to_dict() for s in OFFICIAL_DICTIONARIES.values()],
        'legacy_sources': [s.to_dict() for s in LEGACY_OFFICIAL_SOURCES.values()],
        'last_updated': None,
        'note': 'Конфигурация источников словарей. Реальные источники работают автоматически, legacy требуют ручной настройки.'
    }
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
