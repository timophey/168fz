"""
Модуль синхронизации с официальными словарями, указанными в законе № 168-ФЗ
"""

from .sources import OFFICIAL_DICTIONARIES, save_sources_config
from .synchronizer import DictionarySynchronizer

__all__ = ['OFFICIAL_DICTIONARIES', 'DictionarySynchronizer', 'save_sources_config']
