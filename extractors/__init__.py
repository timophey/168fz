"""
Модуль для извлечения текста из различных источников
"""

from .base import TextExtractor
from .file_extractor import FileExtractor
from .url_extractor import URLExtractor

__all__ = ['TextExtractor', 'FileExtractor', 'URLExtractor']
