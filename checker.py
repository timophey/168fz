"""
Модуль проверки текста на соответствие закону № 168-ФЗ
"""

import re
from typing import Dict, List, Tuple
from dictionaries.manager import DictionaryManager


class LanguageChecker:
    """Проверка текста на соответствие требованиям закона о защите русского языка"""

    def __init__(self, dictionaries_dir: str = None):
        """
        Инициализация проверяющего

        Args:
            dictionaries_dir: Путь к папке со словарями
        """
        self.dict_manager = DictionaryManager(dictionaries_dir)

    def check_text(self, text: str, allowed_words: List[str] = None) -> Dict:
        """
        Полная проверка текста

        Args:
            text: текст для проверки
            allowed_words: дополнительный список разрешенных иностранных слов (опционально)

        Returns:
            Словарь с результатами проверки, включая all_words
        """
        results = {
            'source_text': text[:500] + ('...' if len(text) > 500 else ''),
            'statistics': {
                'total_chars': len(text),
                'total_words': 0,
                'unique_words': 0,
            },
            'dictionaries_used': self.dict_manager.list_dictionaries(),
            'checks': {
                'prohibited_words': [],
                'foreign_words': [],
                'normative_violations': [],
                'recommendations': []
            },
            'summary': {
                'has_prohibited': False,
                'has_foreign': False,
                'violation_count': 0,
                'risk_level': 'low'
            },
            'all_words': []
        }

        # Извлекаем слова из текста
        words = self._extract_words(text)
        results['statistics']['total_words'] = len(words)
        results['statistics']['unique_words'] = len(set(words))

        # Группируем слова по нижнему регистру
        word_groups = {}
        for word in words:
            word_lower = word.lower()
            if word_lower not in word_groups:
                word_groups[word_lower] = {
                    "representative": word,
                    "count": 1,
                    "variations": {word}
                }
            else:
                word_groups[word_lower]["count"] += 1
                word_groups[word_lower]["variations"].add(word)

        # Загружаем словари для быстрой проверки
        russian_alternatives = self.dict_manager.dictionaries.get('русские_аналоги', {}).get('words', set())
        normative_dict = self.dict_manager.dictionaries.get('нормативный_словарь', {}).get('words', set())
        allowed_foreign = self.dict_manager.dictionaries.get('allowed_foreign', {}).get('words', set())
        
        # Добавляем дополнительные разрешенные слова из запроса
        user_allowed_words = set(w.lower() for w in allowed_words) if allowed_words else set()
        all_allowed = allowed_foreign.union(user_allowed_words)
        
        # Проверяем каждую группу слов
        for word_lower, group in word_groups.items():
            representative = group["representative"]
            count = group["count"]
            variations = group["variations"]
            dict_results = self.dict_manager.check_word(word_lower)
            
            # Определяем статус и заполняем checks
            status = "ok"
            categories = []
            dictionaries = list(dict_results.keys())
            law_article = None
            recommendation = None
            explanation = None
            
            # Проверяем наличие латинских букв в representative
            has_latin = re.search(r'[a-zA-Z]', representative) is not None
            
            # 0. ПРИОРИТЕТ: Проверяем, находится ли слово в пользовательском списке исключений
            # Это позволяет обойти любые другие проверки (включая запрещенные слова)
            if word_lower in user_allowed_words:
                status = "exempted"
                explanation = 'Слово исключено из проверки пользователем (добавлено в allowed_words)'
                # Не добавляем в prohibited_words или foreign_words, даже если оно там было бы
            else:
                # 1. Запрещенные слова (высший приоритет после allowed_words)
                is_prohibited = any(key in dict_name.lower()
                                   for dict_name in dict_results.keys()
                                   for key in ['запрещенные', 'ненормативная', 'обсценная', 'нецензурная'])
                
                if is_prohibited:
                    status = "prohibited"
                    first_dict = next((d for d in dict_results.keys() if any(k in d.lower() for k in ['запрещенные', 'ненормативная'])), None)
                    law_article = self._get_law_article(first_dict) if first_dict else 'Статья 6.1'
                    explanation = 'Запрещенное слово - требует немедленного удаления согласно ст. 6.1 закона'
                    results['checks']['prohibited_words'].append({
                        'word': representative,
                        'count': count,
                        'dictionary': first_dict or list(dict_results.keys())[0],
                        'law_article': law_article,
                        'explanation': explanation
                    })
                    results['summary']['has_prohibited'] = True
                    results['summary']['violation_count'] += count
                else:
                    # Проверяем, является ли слово русским (находится в русских словарях, исключая явно иностранные)
                    is_russian = False
                    for dict_name in dict_results:
                        dict_name_lower = dict_name.lower()
                        # Пропускаем запрещенные словари
                        if any(k in dict_name_lower for k in ['запрещенные', 'ненормативная', 'обсценная', 'нецензурная']):
                            continue
                        # Пропускаем явно иностранные словари
                        if dict_name_lower in ['slovar_inostrannykh_slov', 'иностранные_слова', 'allowed_foreign']:
                            continue
                        # Пропускаем русские аналоги
                        if 'русские_аналоги' in dict_name_lower:
                            continue
                        is_russian = True
                        break
                    
                    if is_russian:
                        status = "ok"
                        explanation = 'Слово найдено в словаре русских слов'
                        if word_lower in normative_dict:
                            explanation = 'Слово соответствует нормативному словарю русского языка'
                    # 3. Проверяем иностранные слова с утвержденными русскими аналогами (ПЕРЕД allowed_foreign)
                    elif word_lower in russian_alternatives:
                        status = "foreign_with_alternative"
                        recommendation = self._suggest_russian_alternative(representative)
                        explanation = f'Иностранное слово, но имеет утвержденный русский аналог: {recommendation}'
                        results['checks']['foreign_words'].append({
                            'word': representative,
                            'count': count,
                            'dictionary': 'русские_аналоги',
                            'recommendation': recommendation,
                            'has_alternative': True,
                            'explanation': explanation
                        })
                        results['summary']['has_foreign'] = True
                    # 4. Проверяем разрешенные иностранные слова (международные стандарты, собственные имена)
                    elif word_lower in allowed_foreign:
                        status = "allowed"
                        explanation = 'Слово является разрешенным иностранным термином (международный стандарт/собственное имя)'
                        # Не добавляем в foreign_words, так как это разрешено
                    # 5. Проверяем другие иностранные слова (с латинскими буквами)
                    elif has_latin:
                        status = "foreign"
                        recommendation = self._suggest_russian_alternative(representative)
                        explanation = 'Иностранное слово без установленного русского аналога. Рекомендуется заменить на русский эквивалент.'
                        results['checks']['foreign_words'].append({
                            'word': representative,
                            'count': count,
                            'dictionary': 'иностранные_слова',
                            'recommendation': recommendation,
                            'has_alternative': False,
                            'explanation': explanation
                        })
                        results['summary']['has_foreign'] = True
                    else:
                        status = "unknown"
                        explanation = 'Слово не найдено ни в одном из загруженных словарей'
            
            # Проверка нормативных нарушений по ст. 6 закона
            # Нарушение: использование иностранного слова, когда есть утвержденный русский аналог
            if status == "foreign_with_alternative":
                results['checks']['normative_violations'].append({
                    'word': representative,
                    'count': count,
                    'dictionary': 'русские_аналоги',
                    'issue': 'Использование иностранного слова при наличии утвержденного русского аналога',
                    'explanation': 'Согласно ст. 6 закона № 168-ФЗ, рекомендуется использовать русский аналог вместо иностранного слова'
                })
                results['summary']['violation_count'] += count
            
            # Собираем категории
            for dict_name in dict_results.keys():
                category = self.dict_manager._categorize_dictionary(dict_name)
                categories.append(category)
            
            # Создаем запись для all_words
            word_data = {
                "word": representative,
                "status": status,
                "categories": list(set(categories)) if categories else ['Неизвестно'],
                "dictionaries": list(set(dictionaries)) if dictionaries else [],
                "law_article": law_article,
                "recommendation": recommendation,
                "explanation": explanation,
                "count": count,
                "variations_count": len(variations)
            }
            results['all_words'].append(word_data)
        
        # Сортируем all_words по умолчанию: по частоте (убывание), затем по алфавиту
        results['all_words'].sort(key=lambda x: (-x["count"], x["word"].lower()))
        
        # Генерируем рекомендации
        results['checks']['recommendations'] = self._generate_recommendations(results)

        # Определяем уровень риска
        results['summary']['risk_level'] = self._assess_risk(results)

        return results

    def _extract_words(self, text: str) -> List[str]:
        """Извлечение слов из текста"""
        # Извлекаем слова кириллицей и латиницей, включая дефисы и апострофы
        pattern = r'[а-яёА-ЯЁ\-a-zA-Z\']+'
        words = re.findall(pattern, text)
        return [w for w in words if len(w) > 1 or w.isalpha()]

    def _check_russian_alternative(self, foreign_word: str) -> bool:
        """Проверка наличия русского аналога"""
        russian_alternatives = self.dict_manager.dictionaries.get('русские_аналоги', {}).get('words', set())
        return foreign_word.lower() in russian_alternatives

    def _suggest_russian_alternative(self, foreign_word: str) -> str:
        """Предложение русского аналога"""
        word_lower = foreign_word.lower()

        # Проверяем словарь аналогов
        alternatives = self.dict_manager.dictionaries.get('русские_аналоги', {}).get('words', set())
        if word_lower in alternatives:
            return "Используйте утвержденный русский аналог"

        # Простые эвристики для частых слов
        common_foreign = {
            'online': 'в сети, онлайн',
            'offline': 'офлайн, автономно',
            'download': 'скачать',
            'upload': 'загрузить',
            'login': 'войти (в систему)',
            'logout': 'выйти (из системы)',
            'password': 'пароль',
            'email': 'электронная почта, e-mail',
            'website': 'веб-сайт, сайт',
            'blog': 'блог, дневник',
            'chat': 'чат, общение',
            'meeting': 'встреча, совещание',
            'deadline': 'срок, дедлайн',
            'feedback': 'обратная связь',
            'marketing': 'маркетинг, сбыт',
            'manager': 'менеджер, руководитель',
            'developer': 'разработчик',
            'designer': 'дизайнер',
            'feature': 'функция, особенность',
            'framework': 'фреймворк, каркас',
            'library': 'библиотека (кода)',
            'software': 'программное обеспечение, ПО',
            'hardware': 'аппаратное обеспечение, оборудование',
            'user': 'пользователь',
            'admin': 'администратор',
            'support': 'поддержка',
            'sale': 'распродажа',
            'winter': 'зима',
            'summer': 'лето',
            'spring': 'весна',
            'autumn': 'осень',
            'new': 'новый',
            'old': 'старый',
            'sale': 'распродажа, продажа',
            'winter': 'зима',
        }

        return common_foreign.get(word_lower, "Рассмотрите возможность использования русского термина")

    def _is_mixed_language_word(self, word: str) -> bool:
        """
        Проверка, является ли слово гибридным (смесь кириллицы и латиницы)
        
        Returns:
            True, если слово содержит и кириллические, и латинские символы
        """
        has_cyrillic = bool(re.search(r'[а-яёА-ЯЁ]', word))
        has_latin = bool(re.search(r'[a-zA-Z]', word))
        return has_cyrillic and has_latin

    def _check_normative_usage(self, word: str, context: str) -> bool:
        """
        Проверка корректности употребления слова в контексте
        
        Базовая реализация: проверяет, что слово есть в нормативном словаре.
        
        ПРИМЕЧАНИЕ: Этот метод в настоящее время НЕ используется в основном потоке проверки.
        Он оставлен для возможного будущего расширения (например, контекстного анализа).
        
        Текущая логика нормативных нарушений (ст. 6 закона):
        - Нарушением считается использование иностранного слова, когда есть утвержденный русский аналог.
        - Это проверяется в основном цикле (check_text): если статус "foreign_with_alternative",
          добавляется запись в normative_violations.
        """
        normative_dict = self.dict_manager.dictionaries.get('нормативный_словарь', {}).get('words', set())
        return word.lower() in normative_dict

    def _get_law_article(self, dict_name: str) -> str:
        """Определение статьи закона, нарушаемой при использовании слова"""
        law_articles = {
            'запрещенные_слова': 'Статья 6.1 (Запрет на использование ненормативной лексики)',
            'ненормативная_лексика': 'Статья 6.1',
            'иностранные_слова_без_необходимости': 'Статья 5 (Приоритет русского языка)',
            'искажение_языка': 'Статья 6 (Защита purity языка)',
        }

        for key, article in law_articles.items():
            if key in dict_name.lower():
                return article

        return 'Статья 5-6 (Общие требования к использованию языка)'

    def _generate_recommendations(self, results: Dict) -> List[str]:
        """Генерация рекомендаций на основе результатов проверки"""
        recommendations = []

        if results['summary']['has_prohibited']:
            recommendations.append(
                "⚠️  В тексте обнаружены запрещенные слова. "
                "Необходимо немедленно удалить их согласно ст. 6.1 закона № 168-ФЗ"
            )

        if results['summary']['has_foreign']:
            foreign_count = len(results['checks']['foreign_words'])
            with_alternatives = sum(1 for fw in results['checks']['foreign_words'] if fw.get('has_alternative'))
            
            rec_text = f"🌐 Обнаружено {foreign_count} иностранных слов. "
            if with_alternatives > 0:
                rec_text += f"У {with_alternatives} из них есть русские аналоги. "
            rec_text += "Рекомендуется заменять иностранные слова на русские аналоги, если это возможно без ущерба для смысла (ст. 5 закона)."
            recommendations.append(rec_text)

        if len(results['checks']['normative_violations']) > 0:
            recommendations.append(
                "📚 Обнаружены возможные нарушения норм русского языка. "
                "Рекомендуется проверить употребление слов в нормативных словарях"
            )

        if not any([results['summary']['has_prohibited'],
                    results['summary']['has_foreign'],
                    results['checks']['normative_violations']]):
            recommendations.append(
                "✅ Текст соответствует основным требованиям закона № 168-ФЗ"
            )

        return recommendations

    def _assess_risk(self, results: Dict) -> str:
        """Оценка уровня риска"""
        if results['summary']['has_prohibited']:
            return 'high'
        elif results['summary']['violation_count'] > 5:
            # Считаем все нарушения: запрещенные слова, иностранные без аналога, нормативные
            return 'medium'
        elif results['summary']['has_foreign'] and len(results['checks']['foreign_words']) >= 1:
            # Даже одно иностранное слово без русского аналога - риск
            return 'medium'
        else:
            return 'low'

    def get_dictionary_info(self) -> List[Dict]:
        """Получение информации о загруженных словарях"""
        return self.dict_manager.list_dictionaries()
