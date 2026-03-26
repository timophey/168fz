"""
Экстрактор текста из URL/веб-страниц
"""

import requests
from typing import Union
from urllib.parse import urlparse


class URLExtractor:
    """Экстрактор текста из веб-страниц"""

    def __init__(self, url: str, timeout: int = 10):
        """
        Инициализация экстрактора

        Args:
            url: URL страницы
            timeout: Таймаут запроса в секундах
        """
        self.url = url
        self.timeout = timeout
        self._validate_url()

    def _validate_url(self):
        """Проверка корректности URL"""
        parsed = urlparse(self.url)
        if not parsed.scheme:
            raise ValueError(f"Некорректный URL: {self.url}")
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Поддерживаются только HTTP/HTTPS: {self.url}")

    def extract(self) -> str:
        """Извлечение текста из веб-страницы"""
        try:
            response = requests.get(self.url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'

            # Определяем тип контента
            content_type = response.headers.get('content-type', '').lower()

            if 'text/html' in content_type:
                return self._extract_from_html(response.text)
            elif 'application/json' in content_type:
                return self._extract_from_json(response.text)
            elif 'text/plain' in content_type:
                return response.text
            else:
                # Пытаемся извлечь текст из HTML по умолчанию
                return self._extract_from_html(response.text)

        except requests.RequestException as e:
            raise Exception(f"Ошибка при загрузке URL: {e}")

    def _extract_from_html(self, html: str) -> str:
        """Извлечение чистого текста из HTML"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Удаляем ненужные элементы
            for element in soup(['script', 'style', 'nav', 'header', 'footer',
                                 'aside', 'iframe', 'noscript']):
                element.decompose()

            # Удаляем элементы с определенными классами (навигация, реклама)
            for element in soup.find_all(class_=lambda x: x and any(
                term in str(x).lower() for term in ['nav', 'menu', 'sidebar', 'ad', 'banner']
            )):
                element.decompose()

            # Получаем текст
            text = soup.get_text(separator='\n')

            # Очищаем лишние пробелы и пустые строки
            lines = [line.strip() for line in text.split('\n')]
            lines = [line for line in lines if line]

            return '\n'.join(lines)

        except ImportError:
            # Простой fallback без BeautifulSoup
            import re
            # Удаляем HTML теги
            text = re.sub(r'<[^>]+>', ' ', html)
            # Удаляем лишние пробелы
            text = re.sub(r'\s+', ' ', text)
            # Заменяем HTML сущности
            text = text.replace('&nbsp;', ' ')
            text = text.replace('<', '<')
            text = text.replace('>', '>')
            text = text.replace('&', '&')
            text = text.replace('"', '"')
            return text.strip()

    def _extract_from_json(self, json_str: str) -> str:
        """Извлечение текста из JSON"""
        import json
        try:
            data = json.loads(json_str)
            return self._flatten_json(data)
        except json.JSONDecodeError:
            return json_str

    def _flatten_json(self, obj, separator=' ') -> str:
        """Преобразование JSON в плоский текст"""
        if isinstance(obj, dict):
            texts = []
            for key, value in obj.items():
                texts.append(f"{key}: {self._flatten_json(value)}")
            return separator.join(texts)
        elif isinstance(obj, list):
            return separator.join(self._flatten_json(item) for item in obj)
        elif isinstance(obj, str):
            return obj
        else:
            return str(obj)
