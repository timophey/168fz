#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности XLSX импорта/экспорта
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from dictionaries.manager import DictionaryManager
from dictionaries.loader import DictionaryLoader

def test_xlsx_roundtrip():
    """Тест: экспорт -> импорт -> сравнение"""
    print("🧪 Тест XLSX экспорта/импорта")
    
    # Создаем тестовый словарь
    test_dict = {
        'words': {'test', 'пример', 'demo'},
        'mappings': {
            'test': 'тест',
            'пример': 'пример',
            'demo': 'демо'
        },
        'name': 'test_dict',
        'version': '1.0',
        'source': 'user',
        'category': 'Термины',
        'description': 'Тестовый словарь'
    }
    
    # Экспортируем в XLSX
    test_dir = Path('dictionaries/user_data')
    test_dir.mkdir(exist_ok=True)
    export_path = test_dir / 'test_export.xlsx'
    
    print(f"📤 Экспортируем в {export_path}")
    DictionaryLoader.save_to_xlsx(test_dict, export_path)
    
    # Импортируем из XLSX
    print(f"📥 Импортируем из {export_path}")
    imported = DictionaryLoader.load_from_xlsx(export_path)
    
    # Сравниваем
    print("\n📊 Результаты:")
    print(f"  Слова: {imported['words']}")
    print(f"  Mappings: {imported.get('mappings', {})}")
    print(f"  Category: {imported.get('category', 'N/A')}")
    print(f"  Description: {imported.get('description', 'N/A')}")
    
    # Проверяем
    assert imported['words'] == test_dict['words'], "Слова не совпадают!"
    assert imported.get('mappings', {}) == test_dict['mappings'], "Mappings не совпадают!"
    assert imported.get('category') == test_dict['category'], "Category не совпадает!"
    assert imported.get('description') == test_dict['description'], "Description не совпадает!"
    
    print("\n✅ Тест пройден!")
    
    # Удаляем тестовый файл
    export_path.unlink()
    print(f"🗑️  Удален {export_path}")

def test_manager_integration():
    """Тест интеграции с DictionaryManager"""
    print("\n🧪 Тест DictionaryManager с user_data")
    
    manager = DictionaryManager(
        dictionaries_dir=Path('dictionaries/data'),
        user_data_dir=Path('dictionaries/user_data')
    )
    
    print(f"📚 Загружено словарей: {len(manager.dictionaries)}")
    print("📋 Список:")
    for name, data in manager.dictionaries.items():
        source = data.get('source', 'unknown')
        print(f"  - {name} (source: {source}, words: {len(data['words'])})")
    
    # Проверяем, что пользовательские словари загружаются
    user_dicts = [d for d in manager.dictionaries.values() if d.get('source') == 'user']
    print(f"\n👤 Пользовательских словарей: {len(user_dicts)}")
    
    if user_dicts:
        print("✅ Пользовательские словари загружены!")
    else:
        print("ℹ️  Пользовательские словари отсутствуют (это нормально для первого запуска)")

if __name__ == '__main__':
    try:
        test_xlsx_roundtrip()
        test_manager_integration()
        print("\n🎉 Все тесты пройдены!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
