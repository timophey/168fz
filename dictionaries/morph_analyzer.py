"""
Морфологический анализатор для поиска базовых форм слов

Использует pymorphy3 для определения начальной формы слова,
что позволяет находить слова в словарях даже если они представлены
в производной форме (например, "Шкурение" -> "Шкурить").
"""

from typing import List, Optional, Set
from dataclasses import dataclass
from collections import OrderedDict

try:
    import pymorphy3
    MORPH_AVAILABLE = True
except ImportError:
    MORPH_AVAILABLE = False


@dataclass
class MorphResult:
    """Результат морфологического анализа"""
    original_word: str
    normal_form: str
    pos: str  # Часть речи
    score: float  # Уверенность (0-1)


class LRUCache:
    """
    Simple LRU cache implementation with bounded size.
    Uses OrderedDict for O(1) get/set operations.
    """
    
    def __init__(self, maxsize: int = 50000):
        self.maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()
    
    def get(self, key, default=None):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return default
    
    def put(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)
    
    def __contains__(self, key):
        return key in self._cache
    
    def __len__(self):
        return len(self._cache)
    
    def clear(self):
        self._cache.clear()


class MorphAnalyzer:
    """
    Морфологический анализатор для русского языка
    
    Позволяет находить базовую (нормальную) форму слова,
    что полезно для поиска в словарях.
    """
    
    # Maximum cache sizes to prevent memory issues
    MAX_NORMAL_FORM_CACHE = 50000
    MAX_ALL_FORMS_CACHE = 30000
    MAX_DERIVED_FORMS_CACHE = 30000
    
    def __init__(self):
        """Инициализация анализатора"""
        if not MORPH_AVAILABLE:
            raise ImportError(
                "pymorphy3 не установлен. "
                "Установите его: pip install pymorphy3"
            )
        self._morph = pymorphy3.MorphAnalyzer()
        # Bounded LRU caches for morphological analysis results
        self._normal_form_cache = LRUCache(self.MAX_NORMAL_FORM_CACHE)
        self._all_forms_cache = LRUCache(self.MAX_ALL_FORMS_CACHE)
        self._derived_forms_cache = LRUCache(self.MAX_DERIVED_FORMS_CACHE)
        # Note: find_in_dictionary is NOT cached because it depends on
        # the dictionary set which changes. Caching it would cause
        # unbounded memory growth with different dictionary combinations.
    
    def get_normal_form(self, word: str) -> Optional[str]:
        """
        Получение нормальной (базовой) формы слова
        
        Args:
            word: слово для анализа
            
        Returns:
            Нормальная форма слова или None если не удалось определить
        """
        word_lower = word.lower()
        
        # Check cache first
        cached = self._normal_form_cache.get(word_lower)
        if cached is not None or word_lower in self._normal_form_cache:
            return cached
        
        parses = self._morph.parse(word_lower)
        
        if not parses:
            self._normal_form_cache.put(word_lower, None)
            return None
        
        # Берем первый (наиболее вероятный) разбор
        best_parse = parses[0]
        result = best_parse.normal_form
        self._normal_form_cache.put(word_lower, result)
        return result
    
    def get_all_normal_forms(self, word: str) -> List[MorphResult]:
        """
        Получение всех возможных нормальных форм слова
        
        Args:
            word: слово для анализа
            
        Returns:
            Список возможных нормальных форм с метаданными
        """
        word_lower = word.lower()
        
        # Check cache first
        if word_lower in self._all_forms_cache:
            return self._all_forms_cache.get(word_lower)
        
        parses = self._morph.parse(word_lower)
        
        if not parses:
            self._all_forms_cache.put(word_lower, [])
            return []
        
        results = []
        for parse in parses:
            # Score в pymorphy3 уже нормализован (0-1)
            # Получаем часть речи - в pymorphy3 это TypedGrammeme
            pos_value = 'unknown'
            if parse.tag.POS:
                # В pymorphy3 POS может быть строкой или TypedGrammeme
                if hasattr(parse.tag.POS, 'value'):
                    pos_value = str(parse.tag.POS.value)
                else:
                    pos_value = str(parse.tag.POS)
            
            results.append(MorphResult(
                original_word=word,
                normal_form=parse.normal_form,
                pos=pos_value,
                score=parse.score
            ))
        
        # Сортируем по score (убывание)
        results.sort(key=lambda x: -x.score)
        self._all_forms_cache.put(word_lower, results)
        return results
    
    def find_in_dictionary(self, word: str, dictionary_words: Set[str]) -> Optional[str]:
        """
        Поиск слова в словаре с использованием морфологического анализа
        
        Сначала проверяет точное совпадение, затем пытается найти
        базовую форму в словаре.
        
        Note: This method is intentionally NOT cached because the result
        depends on the dictionary_words set, which can vary between calls.
        Caching with dictionary set as key would cause unbounded memory growth.
        
        Args:
            word: слово для поиска
            dictionary_words: множество слов в словаре
            
        Returns:
            Найденное слово в словаре или None
        """
        word_lower = word.lower()
        
        # 1. Проверяем точное совпадение
        if word_lower in dictionary_words:
            return word_lower
        
        # 2. Получаем нормальную форму и ищем её (this IS cached internally)
        normal_form = self.get_normal_form(word_lower)
        if normal_form and normal_form in dictionary_words:
            return normal_form
        
        # 3. Проверяем все возможные формы (this IS cached internally)
        all_forms = self.get_all_normal_forms(word_lower)
        for form in all_forms:
            if form.normal_form in dictionary_words:
                return form.normal_form
        
        # 4. Проверяем производные формы (суффиксы, окончания)
        # Это особенно полезно для отглагольных существительных
        derived_forms = self._get_derived_forms(word_lower)
        for derived in derived_forms:
            if derived in dictionary_words:
                return derived
        
        return None
    
    def _get_derived_forms(self, word: str) -> List[str]:
        """
        Генерация производных форм слова
        
        Для отглагольных существительных (например, "Шкурение")
        пытается восстановить глагол ("Шкурить").
        
        Args:
            word: слово
            
        Returns:
            Список возможных производных форм
        """
        word_lower = word.lower()
        
        # Check cache first
        if word_lower in self._derived_forms_cache:
            return self._derived_forms_cache.get(word_lower)
        
        forms = []
        
        # Отглагольные существительные на -ение/-ение -> глагол на -ить
        if word_lower.endswith('ение'):
            stem = word_lower[:-4]
            forms.append(stem + 'ить')  # шкурение -> шкурить
            forms.append(stem + 'еть')  # альтернатива
            forms.append(stem + 'ать')  # альтернатива
        
        # Существительные на -ние -> глагол
        elif word_lower.endswith('ние'):
            stem = word_lower[:-3]
            forms.append(stem + 'ить')
            forms.append(stem + 'еть')
            forms.append(stem + 'ать')
        
        # Существительные на -тие -> глагол
        elif word_lower.endswith('тие'):
            stem = word_lower[:-3]
            forms.append(stem + 'ить')
            forms.append(stem + 'еть')
        
        # Причастия на -щий -> глагол
        elif word_lower.endswith('щий'):
            stem = word_lower[:-3]
            forms.append(stem + 'ить')
            forms.append(stem + 'ать')
        
        # Деепричастия на -я/-ши -> глагол
        elif word_lower.endswith('я') and len(word_lower) > 2:
            stem = word_lower[:-1]
            forms.append(stem + 'ить')
            forms.append(stem + 'ать')
            forms.append(stem + 'еть')
        
        # Краткие прилагательные -> полные
        elif word_lower.endswith('ен') and len(word_lower) > 3:
            stem = word_lower[:-2]
            forms.append(stem + 'енный')
            forms.append(stem + 'енный')
        
        # Сравнительная степень -> положительная
        elif word_lower.endswith('ее') or word_lower.endswith('ей'):
            stem = word_lower[:-2]
            forms.append(stem + 'ый')
            forms.append(stem + 'ий')
        
        self._derived_forms_cache.put(word_lower, forms)
        return forms
    
    def is_valid_russian_word(self, word: str) -> bool:
        """
        Проверка, является ли слово корректным русским словом
        
        Args:
            word: слово для проверки
            
        Returns:
            True если слово похоже на корректное русское слово
        """
        word_lower = word.lower()
        parses = self._morph.parse(word_lower)
        
        if not parses:
            return False
        
        # Если есть разборы с высокой вероятностью - слово корректное
        best_parse = parses[0]
        return best_parse.score > 0.1
    
    def get_word_info(self, word: str) -> dict:
        """
        Получение полной информации о слове
        
        Args:
            word: слово для анализа
            
        Returns:
            Словарь с информацией о слове
        """
        word_lower = word.lower()
        parses = self._morph.parse(word_lower)
        
        if not parses:
            return {
                'word': word,
                'is_valid': False,
                'normal_forms': [],
                'all_parses': []
            }
        
        all_parses = []
        for parse in parses:
            # Получаем часть речи
            pos_value = 'unknown'
            if parse.tag.POS:
                if hasattr(parse.tag.POS, 'value'):
                    pos_value = str(parse.tag.POS.value)
                else:
                    pos_value = str(parse.tag.POS)
            
            parse_info = {
                'normal_form': parse.normal_form,
                'pos': pos_value,
                'grammemes': list(parse.tag.grammemes) if hasattr(parse.tag, 'grammemes') else [],
                'score': parse.score
            }
            all_parses.append(parse_info)
        
        return {
            'word': word,
            'is_valid': True,
            'normal_forms': [p.normal_form for p in parses],
            'all_parses': all_parses
        }
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Dictionary with cache sizes
        """
        return {
            'normal_form_cache_size': len(self._normal_form_cache),
            'all_forms_cache_size': len(self._all_forms_cache),
            'derived_forms_cache_size': len(self._derived_forms_cache),
            'normal_form_cache_max': self.MAX_NORMAL_FORM_CACHE,
            'all_forms_cache_max': self.MAX_ALL_FORMS_CACHE,
            'derived_forms_cache_max': self.MAX_DERIVED_FORMS_CACHE,
        }
    
    def clear_caches(self):
        """Clear all caches."""
        self._normal_form_cache.clear()
        self._all_forms_cache.clear()
        self._derived_forms_cache.clear()
