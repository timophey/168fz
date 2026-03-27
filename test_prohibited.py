#!/usr/bin/env python3
"""
Тестовый скрипт для проверки, что слова из словаря "Запрещенные слова" помечаются как prohibited
"""

from checker import LanguageChecker

# Инициализируем проверяющий
checker = LanguageChecker()

# Проверяем текст с запрещенными словами
test_text = "Этот текст содержит запрещенные слова: нахуй, говно, сука"

print("=" * 60)
print("Тестирование запрещенных слов")
print("=" * 60)
print(f"Текст: {test_text}")
print()

result = checker.check_text(test_text)

print("Результаты:")
print(f"  Всего слов: {result['statistics']['total_words']}")
print(f"  Уникальных слов: {result['statistics']['unique_words']}")
print()

print("Запрещенные слова, найденные в проверке:")
if result['checks']['prohibited_words']:
    for item in result['checks']['prohibited_words']:
        print(f"  - {item['word']} (словарь: {item['dictionary']}, статья: {item['law_article']})")
else:
    print("  НЕ НАЙДЕНО")
print()

print("Все слова с их статусами:")
for word_data in result['all_words']:
    print(f"  {word_data['word']}: {word_data['status']} (категории: {', '.join(word_data['categories'])})")
print()

print("Сводка:")
print(f"  Найдены запрещенные слова: {result['summary']['has_prohibited']}")
print(f"  Уровень риска: {result['summary']['risk_level']}")
print()

print("Использованные словари:")
for dict_info in result['dictionaries_used']:
    print(f"  - {dict_info['name']} ({dict_info['category']})")

print()
print("=" * 60)
print("Тест завершен")
print("=" * 60)

# Проверяем, что запрещенные слова были найдены
if result['summary']['has_prohibited']:
    print("✅ ТЕСТ ПРОЙДЕН: Запрещенные слова правильно обнаружены")
else:
    print("❌ ТЕСТ ПРОВАЛЕН: Запрещенные слова НЕ обнаружены")
