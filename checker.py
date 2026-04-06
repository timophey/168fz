"""
Модуль проверки текста на соответствие закону № 168-ФЗ
"""

import os
import re
from typing import Dict, List, Tuple, Optional
from dictionaries.manager import DictionaryManager


class LanguageChecker:
    """Проверка текста на соответствие требованиям закона о защите русского языка"""

    # Maximum number of words to return in all_words response
    # This prevents memory issues with very large texts
    MAX_WORDS_IN_RESPONSE = int(os.getenv('MAX_WORDS_IN_RESPONSE', '5000'))

    def __init__(self, dictionaries_dir: str = None):
        """
        Инициализация проверяющего

        Args:
            dictionaries_dir: Путь к папке со словарями
        """
        self.dict_manager = DictionaryManager(dictionaries_dir)

    def check_text(self, text: str, allowed_words: List[str] = None, dictionary_names: List[str] = None) -> Dict:
        """
        Полная проверка текста

        Args:
            text: текст для проверки
            allowed_words: дополнительный список разрешенных иностранных слов (опционально)
            dictionary_names: список имен словарей для проверки (None = все словари)

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
            'dictionaries_used': [],  # Будет заполнено ниже
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

        # Загружаем словари для быстрой проверки (только если они в выбранном списке)
        russian_alternatives = set()
        normative_dict = set()
        allowed_foreign = set()

        # Определяем, какие словари доступны
        if dictionary_names is None or 'русские_аналоги' in dictionary_names:
            russian_alternatives = self.dict_manager.dictionaries.get('русские_аналоги', {}).get('words', set())
        if dictionary_names is None or 'нормативный_словарь' in dictionary_names:
            normative_dict = self.dict_manager.dictionaries.get('нормативный_словарь', {}).get('words', set())
        if dictionary_names is None or 'allowed_foreign' in dictionary_names:
            allowed_foreign = self.dict_manager.dictionaries.get('allowed_foreign', {}).get('words', set())

        # Формируем список использованных словарей для отчета
        all_dicts_info = self.dict_manager.list_dictionaries()
        if dictionary_names is None:
            results['dictionaries_used'] = all_dicts_info
        else:
            results['dictionaries_used'] = [d for d in all_dicts_info if d['name'] in dictionary_names]
        
        # Добавляем дополнительные разрешенные слова из запроса
        user_allowed_words = set(w.lower() for w in allowed_words) if allowed_words else set()
        all_allowed = allowed_foreign.union(user_allowed_words)
        
        # DEBUG: Log allowed_words for troubleshooting
        import sys
        print(f"[DEBUG] allowed_words received: {allowed_words}", file=sys.stderr)
        print(f"[DEBUG] user_allowed_words: {user_allowed_words}", file=sys.stderr)
        
        # Проверяем каждую группу слов
        for word_lower, group in word_groups.items():
            representative = group["representative"]
            count = group["count"]
            variations = group["variations"]
            check_result = self.dict_manager.check_word(word_lower, dictionary_names)
            dict_results = check_result['dictionaries']
            found_via_morph = check_result['found_via_morph']
            found_word = check_result['found_word']
            
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
                # DEBUG: Log exempted words
                print(f"[DEBUG] Word '{word_lower}' exempted (in user_allowed_words)", file=sys.stderr)
                # Не добавляем в prohibited_words или foreign_words, даже если оно там было бы
            else:
                # 1. Запрещенные слова (высший приоритет после allowed_words)
                # Проверяем по категории словаря, а не по названию
                is_prohibited = any(
                    self.dict_manager.get_dictionary_category(dict_name) == 'Запрещенные слова'
                    for dict_name in dict_results.keys()
                )
                
                if is_prohibited:
                    status = "prohibited"
                    # Находим первый словарь с категорией "Запрещенные слова"
                    first_dict = next((d for d in dict_results.keys()
                                       if self.dict_manager.get_dictionary_category(d) == 'Запрещенные слова'), None)
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
                    # 2. Проверяем, является ли слово русским (находится в нормативных словарях)
                    is_russian = any(
                        self.dict_manager.get_dictionary_category(dict_name) == 'Нормативные слова'
                        for dict_name in dict_results.keys()
                    )
                    
                    if is_russian:
                        status = "ok"
                        if found_via_morph:
                            explanation = f'Слово найдено в словаре русских слов через морфологический анализ (базовая форма: {found_word})'
                        elif word_lower in normative_dict:
                            explanation = 'Слово соответствует нормативному словарю русского языка'
                        else:
                            explanation = 'Слово найдено в словаре русских слов'
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
            
            # Получаем коды категорий
            unique_categories = set(categories) if categories else set()
            category_codes = [self.dict_manager.get_category_code(cat) for cat in unique_categories] if unique_categories else ['unknown']
            
            # Создаем запись для all_words
            word_data = {
                "word": representative,
                "status": status,
                "categories": list(unique_categories) if unique_categories else ['Неизвестно'],
                "category_codes": category_codes,
                "dictionaries": list(set(dictionaries)) if dictionaries else [],
                "law_article": law_article,
                "recommendation": recommendation,
                "explanation": explanation,
                "count": count,
                "variations_count": len(variations),
                "found_via_morph": found_via_morph,
                "found_word": found_word if found_via_morph else None
            }
            results['all_words'].append(word_data)
        
        # Сортируем all_words по умолчанию: по частоте (убывание), затем по алфавиту
        results['all_words'].sort(key=lambda x: (-x["count"], x["word"].lower()))
        
        # Limit the number of words in response to prevent memory issues
        # Store total count before truncating
        total_words_count = len(results['all_words'])
        if total_words_count > self.MAX_WORDS_IN_RESPONSE:
            results['all_words'] = results['all_words'][:self.MAX_WORDS_IN_RESPONSE]
            results['all_words_truncated'] = True
            results['all_words_total'] = total_words_count
        
        # Генерируем рекомендации
        results['checks']['recommendations'] = self._generate_recommendations(results)

        # Определяем уровень риска
        results['summary']['risk_level'] = self._assess_risk(results)

        return results

    def _extract_words(self, text: str) -> List[str]:
        """Извлечение слов из текста"""
        # Извлекаем слова, состоящие из букв. Дефисы и апострофы допускаются только внутри слова.
        # Паттерн: начинается с буквы, затем может содержать буквы, дефисы и апострофы,
        # и заканчивается буквой. Это исключает дефисы/апострофы в начале и конце.
        pattern = r'\b[a-zA-Zа-яёА-ЯЁ]+(?:[\'-][a-zA-Zа-яёА-ЯЁ]+)*\b'
        words = re.findall(pattern, text)
        return words

    def _check_russian_alternative(self, foreign_word: str) -> bool:
        """Проверка наличия русского аналога"""
        russian_alternatives = self.dict_manager.dictionaries.get('русские_аналоги', {}).get('words', set())
        return foreign_word.lower() in russian_alternatives

    def _suggest_russian_alternative(self, foreign_word: str) -> str:
        """Предложение русского аналога"""
        word_lower = foreign_word.lower()

        # 1. Проверяем словарь аналогов (маппинги)
        rus_analogs = self.dict_manager.dictionaries.get('русские_аналоги', {})
        mappings = rus_analogs.get('mappings', {})
        if word_lower in mappings:
            return mappings[word_lower]

        # 2. Простые эвристики для частых слов (fallback)
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
            'client': 'клиент',
            'server': 'сервер',
            'cloud': 'облако',
            'data': 'данные',
            'info': 'информация',
            'system': 'система',
            'network': 'сеть',
            'web': 'веб',
            'app': 'приложение',
            'tool': 'инструмент',
            'script': 'скрипт',
            'code': 'код',
            'bug': 'ошибка',
            'fix': 'исправление',
            'patch': 'заплатка',
            'release': 'релиз',
            'version': 'версия',
            'update': 'обновление',
            'install': 'установить',
            'uninstall': 'удалить',
            'run': 'запустить',
            'execute': 'выполнить',
            'process': 'процесс',
            'thread': 'поток',
            'memory': 'память',
            'disk': 'диск',
            'file': 'файл',
            'folder': 'папка',
            'directory': 'каталог',
            'interface': 'интерфейс',
            'ui': 'пользовательский интерфейс',
            'ux': 'пользовательский опыт',
            'frontend': 'фронтенд',
            'backend': 'бэкенд',
            'fullstack': 'фулстек',
            'database': 'база данных',
            'db': 'база данных',
            'sql': 'SQL',
            'nosql': 'NoSQL',
            'api': 'API',
            'rest': 'REST',
            'json': 'JSON',
            'xml': 'XML',
            'http': 'HTTP',
            'https': 'HTTPS',
            'url': 'адрес (URL)',
            'link': 'ссылка',
            'host': 'хост',
            'domain': 'домен',
            'certificate': 'сертификат',
            'ssl': 'SSL',
            'tls': 'TLS',
            'firewall': 'межсетевой экран',
            'virus': 'вирус',
            'malware': 'вредоносное ПО',
            'security': 'безопасность',
            'backup': 'резервная копия',
            'restore': 'восстановить',
            'log': 'журнал',
            'debug': 'отладка',
            'test': 'тест',
            'qa': 'контроль качества',
            'devops': 'девопс',
            'ci': 'непрерывная интеграция',
            'cd': 'непрерывное развертывание',
            'git': 'Git',
            'repo': 'репозиторий',
            'branch': 'ветка',
            'merge': 'слияние',
            'commit': 'коммит',
            'push': 'отправить',
            'pull': 'получить',
            'clone': 'клонировать',
            'fork': 'форк',
            'pullrequest': 'запрос на включение',
            'issue': 'проблема',
            'ticket': 'тикет',
            'project': 'проект',
            'task': 'задача',
            'todo': 'список задач',
            'milestone': 'веха',
            'sprint': 'спринт',
            'agile': 'агILE',
            'scrum': 'Scrum',
            'kanban': 'Канбан',
            'board': 'доска',
            'chart': 'график',
            'graph': 'граф',
            'report': 'отчет',
            'dashboard': 'панель управления',
            'metric': 'метрика',
            'kpi': 'KPI',
            'roi': 'ROI',
            'seo': 'SEO',
            'sem': 'SEM',
            'ppc': 'PPC',
            'crm': 'CRM',
            'erp': 'ERP',
            'cms': 'CMS',
            'saas': 'SaaS',
            'paas': 'PaaS',
            'iaas': 'IaaS',
            'b2b': 'B2B',
            'b2c': 'B2C',
            'c2c': 'C2C',
            'p2p': 'P2P',
        }

        suggestion = common_foreign.get(word_lower)
        if suggestion:
            return suggestion

        # 3. Общая рекомендация
        return "Рассмотрите возможность использования русского термина"

    def _is_mixed_language_word(self, word: str) -> bool:
        """
        Проверка, является ли слово гибридным (смесь кириллицы и латиницы)
        
        Returns:
            True, если слово содержит и кириллические, и латинские символы
        """
        has_cyrillic = bool(re.search(r'[а-яёА-ЯЁ]', word))
        has_latin = bool(re.search(r'[a-zA-Z]', word))
        return has_cyrillic and has_latin

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
        """Оценка уровня риска с настраиваемыми порогами"""
        if results['summary']['has_prohibited']:
            return 'high'

        # Читаем пороги из переменных окружения (с значениями по умолчанию)
        violation_threshold = int(os.getenv('RISK_THRESHOLD_VIOLATIONS', '5'))
        foreign_ratio_threshold = float(os.getenv('RISK_THRESHOLD_FOREIGN_RATIO', '0.1'))
        foreign_count_threshold = int(os.getenv('RISK_THRESHOLD_FOREIGN_COUNT', '3'))

        # Много нарушений (запрещенные слова + foreign_with_alternative)
        if results['summary']['violation_count'] > violation_threshold:
            return 'medium'

        # Иностранные слова без русского аналога (status 'foreign')
        if results['summary']['has_foreign']:
            total_words = results['statistics']['total_words']
            foreign_count = len(results['checks']['foreign_words'])
            if total_words > 0:
                foreign_ratio = foreign_count / total_words
                # medium если иностранных слов превышает порог по доле или количеству
                if foreign_ratio > foreign_ratio_threshold or foreign_count >= foreign_count_threshold:
                    return 'medium'
            # Если total_words == 0, low

        return 'low'

    def get_dictionary_info(self) -> List[Dict]:
        """Получение информации о загруженных словарях"""
        return self.dict_manager.list_dictionaries()
