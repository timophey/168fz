"""
Тест морфологического анализа на редких/специфических словах

Проверяет случаи, когда слово в производной форме ОТСУТСТВУЕТ в словаре,
но его базовая форма ПРИСУТСТВУЕТ.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dictionaries.manager import DictionaryManager
from dictionaries.morph_analyzer import MorphAnalyzer, MORPH_AVAILABLE
from pathlib import Path


def test_rare_words():
    """Тест на редких словах, которых точно нет в словарях"""
    if not MORPH_AVAILABLE:
        print("⚠️ pymorphy3 не установлен, пропускаем тест")
        return
    
    manager = DictionaryManager(
        dictionaries_dir=Path('dictionaries/data'),
        use_morph_analysis=True
    )
    analyzer = MorphAnalyzer()
    
    # Редкие/специфические слова в производных формах
    # Ключевой момент: эти слова в ТАКОЙ форме скорее всего отсутствуют в словарях
    test_cases = [
        # Отглагольные существительные на -ение (редкие)
        ("взрыхлением", "взрыхлить", "Сельское хозяйство"),
        ("вспахиванием", "вспахивать", "Сельское хозяйство"),
        ("раскорчёвкой", "раскорчёвка", "Сельское хозяйство"),
        
        # Технические термины в косвенных падежах
        ("фрезерованием", "фрезерование", "Инженерия"),
        ("шлифованием", "шлифование", "Инженерия"),
        ("гальванизированием", "гальванизировать", "Инженерия"),
        
        # Юридические термины
        ("правоприменением", "правоприменение", "Право"),
        ("законодательствованием", "законодательствовать", "Право"),
        ("нормотворчеством", "нормотворчество", "Право"),
        
        # Медицинские термины
        ("обезболиванием", "обезболивание", "Медицина"),
        ("наркозированием", "наркозирование", "Медицина"),
        ("реанимированием", "реанимировать", "Медицина"),
        
        # IT-термины
        ("дебаггингом", "дебаггинг", "IT"),
        ("рефакторингом", "рефакторинг", "IT"),
        ("деплоем", "деплой", "IT"),
        
        # Научные термины
        ("экспериментированием", "экспериментирование", "Наука"),
        ("исследовательством", "исследовательство", "Наука"),
        ("наблюдением", "наблюдение", "Наука"),
    ]
    
    print("=" * 80)
    print("Тест на редких/специфических словах")
    print("=" * 80)
    print(f"{'Слово':<35} {'Базовая':<25} {'Найдено':<10} {'Морфо':<8} Область")
    print("-" * 80)
    
    found_count = 0
    morph_count = 0
    total = len(test_cases)
    
    for word, expected_base, domain in test_cases:
        result = manager.check_word(word)
        found = bool(result['dictionaries'])
        via_morph = result['found_via_morph']
        found_word = result['found_word']
        
        if found:
            found_count += 1
            if via_morph:
                morph_count += 1
        
        status = "✓" if found else "✗"
        morph_tag = "[M]" if via_morph else "   "
        
        print(f"  {status} {word:<33} {found_word:<25} {morph_tag:<8} {domain}")
    
    print("-" * 80)
    print(f"Найдено: {found_count}/{total}")
    print(f"Через морфоанализ: {morph_count}/{total}")
    
    # Отдельно покажем слова, которые НЕ найдены
    not_found = []
    for word, expected_base, domain in test_cases:
        result = manager.check_word(word)
        if not result['dictionaries']:
            not_found.append((word, expected_base, domain))
    
    if not_found:
        print(f"\nНе найдено ({len(not_found)}):")
        for word, expected_base, domain in not_found:
            # Попробуем хотя бы получить базовую форму
            base = analyzer.get_normal_form(word)
            print(f"  '{word}' -> pymorphy3: '{base}' (ожидалось: '{expected_base}')")


def test_specific_word_in_checker():
    """Тест конкретного слова "шкурение" через checker"""
    if not MORPH_AVAILABLE:
        print("⚠️ pymorphy3 не установлен, пропускаем тест")
        return
    
    from checker import LanguageChecker
    
    checker = LanguageChecker()
    
    # Проверяем, что "шкурение" не находится напрямую
    result_direct = checker.dict_manager.check_word("шкурение")
    print(f"\nПрямая проверка 'шкурение':")
    print(f"  Найдено: {bool(result_direct['dictionaries'])}")
    print(f"  Через морфоанализ: {result_direct['found_via_morph']}")
    print(f"  Найденное слово: {result_direct['found_word']}")
    
    # Проверяем, что "шкурить" находится напрямую
    result_base = checker.dict_manager.check_word("шкурить")
    print(f"\nПрямая проверка 'шкурить':")
    print(f"  Найдено: {bool(result_base['dictionaries'])}")
    print(f"  Через морфоанализ: {result_base['found_via_morph']}")
    print(f"  Найденное слово: {result_base['found_word']}")
    
    # Полный анализ текста
    print(f"\nПолный анализ текста:")
    text = "Шкурение деревянных поверхностей требует аккуратности"
    result = checker.check_text(text)
    
    for word_data in result['all_words']:
        if word_data['word'].lower() in ['шкурение', 'шкурить']:
            print(f"  '{word_data['word']}': status={word_data['status']}, "
                  f"found_via_morph={word_data.get('found_via_morph')}, "
                  f"found_word={word_data.get('found_word')}")


def test_morph_heuristics():
    """Тест эвристик для отглагольных существительных"""
    if not MORPH_AVAILABLE:
        print("⚠️ pymorphy3 не установлен, пропускаем тест")
        return
    
    analyzer = MorphAnalyzer()
    
    # Словарь с базовыми формами
    test_dict = {"шкурить", "шлифовать", "полировать", "красить", "пилить",
                 "строгать", "сверлить", "точить", "резать", "клеить"}
    
    test_words = [
        "шкурение",
        "шлифование",
        "полирование",
        "крашение",
        "пиление",
        "строгание",
        "сверление",
        "точение",
        "резание",
        "клеение",
    ]
    
    print("\n" + "=" * 60)
    print("Тест эвристик для отглагольных существительных")
    print("=" * 60)
    
    found = 0
    for word in test_words:
        result = analyzer.find_in_dictionary(word, test_dict)
        if result:
            found += 1
            print(f"  ✓ '{word}' -> '{result}'")
        else:
            # Попробуем через pymorphy3
            base = analyzer.get_normal_form(word)
            print(f"  ✗ '{word}' -> pymorphy3: '{base}' (не найдено в словаре)")
    
    print(f"\nНайдено: {found}/{len(test_words)}")


if __name__ == "__main__":
    test_rare_words()
    test_specific_word_in_checker()
    test_morph_heuristics()
    
    print("\n" + "=" * 80)
    print("Тестирование завершено")
    print("=" * 80)
