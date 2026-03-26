"""
Базовый класс для извлечения текста
"""

from pathlib import Path
from typing import Union


class TextExtractor:
    """Фабрика для извлечения текста из различных источников"""

    def __init__(self, source: Union[str, Path]):
        """
        Инициализация извлекателя

        Args:
            source: Источник - путь к файлу, URL или текст
        """
        self.source = str(source)
        self._extractor = self._select_extractor()

    def _select_extractor(self):
        """Выбор подходящего экстрактора на основе источника"""
        # Проверяем, является ли источник URL
        if self.source.startswith(('http://', 'https://', 'ftp://')):
            from .url_extractor import URLExtractor
            return URLExtractor(self.source)

        # Проверяем, является ли источник путем к файлу
        path = Path(self.source)
        if path.exists() and path.is_file():
            from .file_extractor import FileExtractor
            return FileExtractor(path)

        # По умолчанию считаем, что это plain text
        return PlainTextExtractor(self.source)

    def get_text(self) -> str:
        """Извлечение текста из источника"""
        return self._extractor.extract()


class PlainTextExtractor:
    """Экстрактор для простого текста"""

    def __init__(self, text: str):
        self.text = text

    def extract(self) -> str:
        """Возвращает текст как есть"""
        return self.text


class FileExtractor:
    """Базовый класс для извлечения из файлов"""

    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.html', '.htm', '.json', '.csv'}

    def __init__(self, filepath: Path):
        self.filepath = filepath

    def extract(self) -> str:
        """Извлечение текста из файла"""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Файл не найден: {self.filepath}")

        ext = self.filepath.suffix.lower()

        if ext == '.txt' or ext == '.md':
            return self._extract_text()
        elif ext in ['.html', '.htm']:
            return self._extract_html()
        elif ext == '.json':
            return self._extract_json()
        elif ext == '.csv':
            return self._extract_csv()
        else:
            # Пытаемся читать как текст
            return self._extract_text()

    def _extract_text(self) -> str:
        """Извлечение из текстового файла"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def _extract_html(self) -> str:
        """Извлечение текста из HTML файла"""
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

    def _extract_json(self) -> str:
        """Извлечение текста из JSON файла"""
        import json
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Рекурсивно извлекаем строковые значения
            return self._extract_strings_from_json(data)

    def _extract_strings_from_json(self, obj) -> str:
        """Рекурсивное извлечение строк из JSON"""
        if isinstance(obj, dict):
            texts = []
            for value in obj.values():
                texts.append(self._extract_strings_from_json(value))
            return ' '.join(texts)
        elif isinstance(obj, list):
            texts = [self._extract_strings_from_json(item) for item in obj]
            return ' '.join(texts)
        elif isinstance(obj, str):
            return obj
        else:
            return str(obj)

    def _extract_csv(self) -> str:
        """Извлечение текста из CSV файла"""
        import csv
        texts = []
        with open(self.filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                texts.append(' '.join(row))
        return '\n'.join(texts)
