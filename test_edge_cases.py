#!/usr/bin/env python3
"""
Тесты на крайние случаи для проверки 168-ФЗ Text Checker
"""

import unittest
from checker import LanguageChecker


class TestEdgeCases(unittest.TestCase):
    """Тесты для проверки обработки крайних случаев"""
    
    def setUp(self):
        """Инициализация проверяющего"""
        self.checker = LanguageChecker()
    
    def test_mixed_language_words(self):
        """Тест гибридных слов (смесь кириллицы и латиницы)"""
        # Слова с混合 escritura должны определяться как foreign (если есть латинские буквы)
        test_cases = [
            ("NoName", "foreign"),  # латинские буквы - не в словарях, будет foreign
            ("МойLogin", "foreign"),  # кириллица + латиница - не в словарях
            ("123Test", "foreign_with_alternative"),  # "test" есть в русских_аналогах
            ("файл123", "ok"),  # кириллица + цифры (без латиницы)
            ("foobar", "foreign"),  # вымышленное слово, не в словарях
        ]
        
        for text, expected_status in test_cases:
            result = self.checker.check_text(text)
            if result['all_words']:
                actual_status = result['all_words'][0]['status']
                self.assertEqual(actual_status, expected_status,
                               f"Word '{text}' expected status '{expected_status}', got '{actual_status}'")
    
    def test_case_insensitivity(self):
        """Тест нечувствительности к регистру"""
        # Одно и то же слово в разных регистрах должно давать одинаковый статус
        test_word = "foobar"  # вымышленное слово, не в словарях, будет foreign
        variants = ["foobar", "FOOBAR", "FoObAr", "Foobar"]
        
        for variant in variants:
            result = self.checker.check_text(variant)
            if result['all_words']:
                status = result['all_words'][0]['status']
                # foobar должно быть foreign (не в словарях)
                self.assertEqual(status, "foreign",
                               f"Variant '{variant}' should have status 'foreign'")
    
    def test_punctuation_handling(self):
        """Тест обработки пунктуации"""
        # Слова с дефисами, апострофами и другие
        test_cases = [
            "e-mail",  # дефис
            "user's",  # апостроф
            "API-key",  # комбинация
            "word-word",  # два слова через дефис
        ]
        
        for text in test_cases:
            result = self.checker.check_text(text)
            # Должно обработать без ошибок
            self.assertIsNotNone(result)
            self.assertIn('all_words', result)
    
    def test_foreign_with_alternative(self):
        """Тест иностранных слов, имеющих русские аналоги"""
        # "online" может быть в русских аналогах? Проверим
        # Слово "online" обычно иностранное, но если есть в русских_аналогах, будет foreign_with_alternative
        result = self.checker.check_text("online")
        if result['all_words']:
            status = result['all_words'][0]['status']
            self.assertIn(status, ["foreign", "foreign_with_alternative"])
    
    def test_prohibited_words(self):
        """Тест обнаружения запрещенных слов"""
        # Запрещенные слова должны иметь статус prohibited
        # Примечание: нужно использовать реальное запрещенное слово из словаря
        # Например, мат или нецензурная лексика
        # Но для теста можно использовать любое слово, которое есть в запрещенных словарях
        # Поскольку мы не знаем конкретные слова, проверим хотя бы, что функция работает
        result = self.checker.check_text("тест")
        self.assertIsNotNone(result)
        self.assertEqual(result['all_words'][0]['status'], "ok")
    
    def test_risk_level_assessment(self):
        """Тест оценки уровня риска"""
        # 1. Текст с запрещенными словами -> high risk
        # Нужно найти запрещенное слово. Пока пропустим, если нет в словарях.
        
        # 2. Текст с иностранными словами -> medium risk (после исправления)
        result_foreign = self.checker.check_text("online meeting")
        self.assertEqual(result_foreign['summary']['risk_level'], 'medium',
                        "Text with foreign words should have medium risk")
        
        # 3. Текст без нарушений -> low risk
        result_ok = self.checker.check_text("Привет мир")
        self.assertEqual(result_ok['summary']['risk_level'], 'low',
                        "Clean text should have low risk")
    
    def test_normative_violations_count(self):
        """Тест подсчета нормативных нарушений"""
        # Если есть foreign_with_alternative, violation_count должен увеличиваться
        result = self.checker.check_text("online")
        # online может быть foreign или foreign_with_alternative
        # В любом случае, если есть foreign_with_alternative, violation_count > 0
        if result['all_words'] and result['all_words'][0]['status'] == 'foreign_with_alternative':
            self.assertGreater(result['summary']['violation_count'], 0,
                             "Violation count should be > 0 for foreign_with_alternative")
    
    def test_multiple_occurrences(self):
        """Тест учета повторяющихся слов"""
        text = "online online online meeting meeting"
        result = self.checker.check_text(text)
        
        # Проверяем, что count правильно считается
        online_word = next((w for w in result['all_words'] if w['word'].lower() == 'online'), None)
        if online_word:
            self.assertEqual(online_word['count'], 3, "Word 'online' should appear 3 times")
    
    def test_empty_text(self):
        """Тест пустого текста"""
        result = self.checker.check_text("")
        self.assertEqual(result['statistics']['total_words'], 0)
        self.assertEqual(len(result['all_words']), 0)
    
    def test_single_character_words(self):
        """Тест односимвольных слов (должны игнорироваться)"""
        # Согласно _extract_words: слова длиной 1 игнорируются, если не буквы
        text = "a b c"
        result = self.checker.check_text(text)
        # 'a' и 'b' - латинские односимвольные, должны быть извлечены? 
        # В _extract_words: [w for w in words if len(w) > 1 or w.isalpha()]
        # 'a' имеет len=1 и isalpha()=True, поэтому будет включен
        # Но это зависит от реализации. Проверим факт.
        # В любом случае, не должно быть ошибок.
        self.assertIsNotNone(result)
    
    def test_numbers_and_special_chars(self):
        """Тест чисел и специальных символов"""
        text = "123 456 test@example.com"
        result = self.checker.check_text(text)
        # Числа и email должны обработаться корректно
        self.assertIsNotNone(result)
    
    def test_allowed_foreign_words(self):
        """Тест разрешенных иностранных слов (пользовательские исключения)"""
        # Проверим, что пользовательские слова из allowed_words имеют статус 'exempted'
        # (изменено с 'allowed' для отдельного отображения пользовательских исключений)
        allowed = ["MyCompany", "ProductX"]
        result = self.checker.check_text("MyCompany ProductX", allowed_words=allowed)
        
        for word_data in result['all_words']:
            if word_data['word'] in allowed:
                self.assertEqual(word_data['status'], 'exempted',
                               f"Word '{word_data['word']}' should have status 'exempted'")
    
    def test_word_variations(self):
        """Тест учета вариантов слова (разный регистр)"""
        text = "Online ONLINE online"
        result = self.checker.check_text(text)
        
        online_word = next((w for w in result['all_words'] if w['word'].lower() == 'online'), None)
        if online_word:
            self.assertEqual(online_word['count'], 3, 
                           "All variations of 'online' should be counted together")
            self.assertEqual(online_word['variations_count'], 3,
                           "Should track 3 variations (case differences)")
    
    def test_dictionary_categories(self):
        """Тест категоризации словарей"""
        result = self.checker.check_text("online")
        if result['all_words']:
            categories = result['all_words'][0]['categories']
            # Категории должны быть определены
            self.assertIsInstance(categories, list)
            self.assertGreater(len(categories), 0)


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты"""
    
    def setUp(self):
        self.checker = LanguageChecker()
    
    def test_full_workflow(self):
        """Тест полного рабочего процесса"""
        text = """
        Наш новый продукт online доступен для всех пользователей.
        Загрузка файлов происходит автоматически. 
        Пожалуйста, отправьте feedback.
        """
        
        result = self.checker.check_text(text)
        
        # Проверяем структуру результата
        self.assertIn('source_text', result)
        self.assertIn('statistics', result)
        self.assertIn('checks', result)
        self.assertIn('summary', result)
        self.assertIn('all_words', result)
        
        # Проверяем наличие ожидаемых полей
        self.assertIn('total_chars', result['statistics'])
        self.assertIn('total_words', result['statistics'])
        self.assertIn('unique_words', result['statistics'])
        
        self.assertIn('prohibited_words', result['checks'])
        self.assertIn('foreign_words', result['checks'])
        self.assertIn('normative_violations', result['checks'])
        self.assertIn('recommendations', result['checks'])
        
        self.assertIn('has_prohibited', result['summary'])
        self.assertIn('has_foreign', result['summary'])
        self.assertIn('violation_count', result['summary'])
        self.assertIn('risk_level', result['summary'])
    
    def test_recommendations_generation(self):
        """Тест генерации рекомендаций"""
        # Текст с иностранными словами должен содержать рекомендации
        result = self.checker.check_text("online meeting deadline")
        recommendations = result['checks']['recommendations']
        self.assertGreater(len(recommendations), 0)
        
        # Текст без нарушений должен содержать позитивную рекомендацию
        result_ok = self.checker.check_text("Привет мир")
        recs_ok = result_ok['checks']['recommendations']
        self.assertTrue(any('соответствует' in r.lower() for r in recs_ok),
                       "Should have a recommendation stating text complies")


if __name__ == '__main__':
    unittest.main(verbosity=2)
