"""
Морфологический анализатор для поиска базовых форм слов

Использует pymorphy3 для определения начальной формы слова,
что позволяет находить слова в словарях даже если они представлены
в производной форме (например, "Шкурение" -> "Шкурить").
"""

from typing import List, Optional, Set
from dataclasses import dataclass

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


class MorphAnalyzer:
    """
    Морфологический анализатор для русского языка
    
    Позволяет находить базовую (нормальную) форму слова,
    что полезно для поиска в словарях.
    """
    
    def __init__(self):
        """Инициализация анализатора"""
        if not MORPH_AVAILABLE:
            raise ImportError(
                "pymorphy3 не установлен. "
                "Установите его: pip install pymorphy3"
            )
        self._morph = pymorphy3.MorphAnalyzer()
    
    def get_normal_form(self, word: str) -> Optional[str]:
        """
        Получение нормальной (базовой) формы слова
        
        Args:
            word: слово для анализа
            
        Returns:
            Нормальная форма слова или None если не удалось определить
        """
        word_lower = word.lower()
        parses = self._morph.parse(word_lower)
        
        if not parses:
            return None
        
        # Берем первый (наиболее вероятный) разбор
        best_parse = parses[0]
        return best_parse.normal_form
    
    def get_all_normal_forms(self, word: str) -> List[MorphResult]:
        """
        Получение всех возможных нормальных форм слова
        
        Args:
            word: слово для анализа
            
        Returns:
            Список возможных нормальных форм с метаданными
        """
        word_lower = word.lower()
        parses = self._morph.parse(word_lower)
        
        if not parses:
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
        return results
    
    def find_in_dictionary(self, word: str, dictionary_words: Set[str]) -> Optional[str]:
        """
        Поиск слова в словаре с использованием морфологического анализа
        
        Сначала проверяет точное совпадение, затем пытается найти
        базовую форму в словаре.
        
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
        
        # 2. Получаем нормальную форму и ищем её
        normal_form = self.get_normal_form(word_lower)
        if normal_form and normal_form in dictionary_words:
            return normal_form
        
        # 3. Проверяем все возможные формы
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
        forms = []
        word_lower = word.lower()
        
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
