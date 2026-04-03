"""
Тест морфологического анализа

Проверяет, что слова в производных формах находятся в словарях
через поиск базовой формы.
"""

import sys
import os

# Добавляем путь к модулю
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dictionaries.morph_analyzer import MorphAnalyzer, MORPH_AVAILABLE


def test_morph_analyzer():
    """Тест базового морфологического анализа"""
    if not MORPH_AVAILABLE:
        print("⚠️ pymorphy3 не установлен, пропускаем тест")
        return
    
    analyzer = MorphAnalyzer()
    
    # Тест 1: Отглагольное существительное
    word = "шкурение"
    normal_form = analyzer.get_normal_form(word)
    print(f"Тест 1: '{word}' -> '{normal_form}'")
    
    # Тест 2: Глагол в другой форме
    word = "шлифую"
    normal_form = analyzer.get_normal_form(word)
    print(f"Тест 2: '{word}' -> '{normal_form}'")
    
    # Тест 3: Прилагательное в краткой форме
    word = "красив"
    normal_form = analyzer.get_normal_form(word)
    print(f"Тест 3: '{word}' -> '{normal_form}'")
    
    # Тест 4: Существительное в множественном числе
    word = "слова"
    normal_form = analyzer.get_normal_form(word)
    print(f"Тест 4: '{word}' -> '{normal_form}'")
    
    # Тест 5: Поиск в словаре
    dictionary_words = {"шкурить", "шлифовать", "красивый", "слово"}
    
    test_cases = [
        ("шкурение", "шкурить"),
        ("шлифую", "шлифовать"),
        ("красив", "красивый"),
        ("словами", "слово"),
    ]
    
    print("\nТест 5: Поиск в словаре через морфоанализ")
    for word, expected in test_cases:
        found = analyzer.find_in_dictionary(word, dictionary_words)
        status = "✓" if found == expected else "✗"
        print(f"  {status} '{word}' -> '{found}' (ожидалось: '{expected}')")


def test_dictionary_manager_with_morph():
    """Тест DictionaryManager с морфологическим анализом"""
    if not MORPH_AVAILABLE:
        print("⚠️ pymorphy3 не установлен, пропускаем тест")
        return
    
    from dictionaries.manager import DictionaryManager
    from pathlib import Path
    
    # Создаем менеджер с морфоанализом
    manager = DictionaryManager(
        dictionaries_dir=Path('dictionaries/data'),
        use_morph_analysis=True
    )
    
    # Проверяем слово в производной форме
    test_words = ["шкурение", "шлифую", "красив"]
    
    print("\nТест DictionaryManager:")
    for word in test_words:
        result = manager.check_word(word)
        found = bool(result['dictionaries'])
        morph_info = f" (через морфоанализ: {result['found_word']})" if result['found_via_morph'] else ""
        status = "✓" if found else "✗"
        print(f"  {status} '{word}' -> найдено: {found}{morph_info}")


if __name__ == "__main__":
    print("=" * 50)
    print("Тест морфологического анализа")
    print("=" * 50)
    
    test_morph_analyzer()
    test_dictionary_manager_with_morph()
    
    print("\n" + "=" * 50)
    print("Тестирование завершено")
    print("=" * 50)
