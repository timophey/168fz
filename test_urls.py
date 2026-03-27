#!/usr/bin/env python3
"""
Тестирование сервиса на указанных URL
"""

import requests
import json
from collections import Counter
import re

URLS = [
    # IT/Tech сайты - максимальное количество английских терминов и аббревиатур
    "https://habr.com/ru/feed/",
    "https://habr.com/ru/companies/",
    "https://vc.ru/",
    "https://cnews.ru/",
    "https://3dnews.ru/",
    "https://www.ixbt.com/",
    "https://tadviser.ru/",
    
    # Гейминг - английские названия игр, терминов, сленг
    "https://stopgame.ru/",
    "https://www.igromania.ru/",
    "https://www.playground.ru/",
    
    # Бизнес/стартапы - англицизмы, жаргон, аббревиатуры
    "https://rb.ru/",
    "https://www.sostav.ru/",
    "https://www.slideshare.net/ru/feed",
    
    # Соцсети и пользовательский контент - сленг, жаргон
    "https://pikabu.ru/",
    "https://dtf.ru/",
    "https://tjournal.ru/",
    
    # Технические блоги и документация
    "https://yandex.ru/dev/",
    "https://developers.google.com/",
    
    # Новостные сайты с международной тематикой
    "https://www.kommersant.ru/",
    "https://www.rbc.ru/",
    
    # Специализированные ресурсы
    "https://www.opennet.ru/",
    "https://www.linux.org.ru/",
    
    # Маркетинг и реклама
    "https://www.adindex.ru/",
    "https://www.cossa.ru/",
]

def test_url(url):
    """Проверка одного URL"""
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/check",
            json={"url": url},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data["data"]
            else:
                return {"error": data.get("detail", "Unknown error")}
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def analyze_results(results):
    """Анализ результатов проверки"""
    for url, data in results.items():
        print(f"\n{'='*80}")
        print(f"URL: {url}")
        print(f"{'='*80}")
        
        if "error" in data:
            print(f"Ошибка: {data['error']}")
            continue
        
        stats = data.get("statistics", {})
        summary = data.get("summary", {})
        all_words = data.get("all_words", [])
        checks = data.get("checks", {})
        
        print(f"\nСтатистика:")
        print(f"  Всего слов: {stats.get('total_words', 0)}")
        print(f"  Уникальных: {stats.get('unique_words', 0)}")
        print(f"  Уровень риска: {summary.get('risk_level', 'unknown')}")
        print(f"  Нарушений: {summary.get('violation_count', 0)}")
        
        print(f"\nВсе слова (сгруппированные): {len(all_words)} уникальных")
        if all_words:
            # Показать топ-10 самых частых слов
            sorted_words = sorted(all_words, key=lambda x: x.get('count', 1), reverse=True)[:10]
            print("  Топ-10 слов по частоте:")
            for w in sorted_words:
                print(f"    {w['word']}: {w.get('count', 1)} (статус: {w['status']})")
        
        print(f"\nЗапрещенные слова: {len(checks.get('prohibited_words', []))}")
        for item in checks.get('prohibited_words', [])[:5]:
            print(f"  {item['word']}: {item.get('count', 1)} - {item.get('law_article', '-')}")
        
        print(f"\nИностранные слова: {len(checks.get('foreign_words', []))}")
        for item in checks.get('foreign_words', [])[:10]:
            print(f"  {item['word']}: {item.get('count', 1)} - {item.get('recommendation', '-')}")
        
        # Анализ потенциально опасных слов (транслитерация)
        all_words_data = data.get("all_words", [])
        potential_transliterations = []
        
        for w in all_words_data:
            word = w['word']
            # Ищем слова с латинскими буквами или смесью
            if re.search(r'[a-zA-Z]', word):
                potential_transliterations.append(w)
            # Ищем слова, которые могут быть иностранными по контексту (статус foreign или foreign_with_alternative)
            if w['status'] in ['foreign', 'foreign_with_alternative']:
                if w not in potential_transliterations:
                    potential_transliterations.append(w)
        
        if potential_transliterations:
            print(f"\nПотенциально иностранные/транслитерированные слова: {len(potential_transliterations)}")
            # Группируем по статусу
            by_status = {}
            for w in potential_transliterations:
                status = w['status']
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(w)
            
            for status, words in by_status.items():
                print(f"  {status}: {len(words)} слов")
                # Показать примеры
                for w in sorted(words, key=lambda x: x.get('count', 1), reverse=True)[:5]:
                    print(f"    {w['word']}: {w.get('count', 1)}")

def main():
    print("Тестирование сервиса 168-ФЗ Text Checker")
    print(f"Всего URL для проверки: {len(URLS)}")
    
    results = {}
    for url in URLS:
        print(f"\nПроверяю: {url}")
        result = test_url(url)
        results[url] = result
    
    # Сохраняем результаты в файл
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nРезультаты сохранены в test_results.json")
    
    # Анализируем
    analyze_results(results)

if __name__ == "__main__":
    main()
