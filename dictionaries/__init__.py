"""
Модуль для работы со словарями проверки русского языка
"""

from .loader import DictionaryLoader
from .manager import DictionaryManager
from .morph_analyzer import MorphAnalyzer, MORPH_AVAILABLE

__all__ = ['DictionaryLoader', 'DictionaryManager', 'MorphAnalyzer', 'MORPH_AVAILABLE']
