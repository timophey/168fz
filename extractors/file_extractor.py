"""
Экстрактор текста из файлов
"""

from pathlib import Path
from typing import Union
from .base import FileExtractor


class TextFileExtractor(FileExtractor):
    """Экстрактор для текстовых файлов (.txt, .md)"""

    def extract(self) -> str:
        with open(self.filepath, 'r', encoding='utf-8') as f:
            return f.read()


class HTMLFileExtractor(FileExtractor):
    """Экстрактор для HTML файлов"""

    def extract(self) -> str:
        try:
            from bs4 import BeautifulSoup
            with open(self.filepath, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                # Удаляем скрипты и стили
                for script in soup(["script", "style"]):
                    script.decompose()
                return soup.get_text()
        except ImportError:
            # Если BeautifulSoup не установлен, извлекаем простым способом
            import re
            with open(self.filepath, 'r', encoding='utf-8') as f:
                html = f.read()
                # Удаляем HTML теги
                text = re.sub(r'<[^>]+>', ' ', html)
                # Удаляем лишние пробелы
                text = re.sub(r'\s+', ' ', text)
                return text.strip()


class JSONFileExtractor(FileExtractor):
    """Экстрактор для JSON файлов"""

    def extract(self) -> str:
        import json
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return self._extract_strings(data)

    def _extract_strings(self, obj) -> str:
        """Рекурсивное извлечение строк"""
        if isinstance(obj, dict):
            texts = [self._extract_strings(v) for v in obj.values()]
            return ' '.join(texts)
        elif isinstance(obj, list):
            texts = [self._extract_strings(item) for item in obj]
            return ' '.join(texts)
        elif isinstance(obj, str):
            return obj
        else:
            return str(obj)


class CSVFileExtractor(FileExtractor):
    """Экстрактор для CSV файлов"""

    def extract(self) -> str:
        import csv
        texts = []
        with open(self.filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                texts.append(' '.join(row))
        return '\n'.join(texts)


def get_file_extractor(filepath: Path):
    """Фабрика для получения экстрактора по расширению файла"""
    ext = filepath.suffix.lower()

    extractors = {
        '.txt': TextFileExtractor,
        '.md': TextFileExtractor,
        '.html': HTMLFileExtractor,
        '.htm': HTMLFileExtractor,
        '.json': JSONFileExtractor,
        '.csv': CSVFileExtractor,
    }

    extractor_class = extractors.get(ext, TextFileExtractor)
    return extractor_class(filepath)
