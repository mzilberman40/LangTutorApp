import unittest
from step01.clean_and_validate_input import clean_and_validate_input

class TestStep01Input(unittest.TestCase):

    def test_cleaning_words(self):
        from re import sub

        raw_words = [" Chat", "CHAT!", "chat", "apple.", "APPLE"]
        expected = {"chat", "apple"}

        cleaned = set()
        for word in raw_words:
            w = sub(r"[^\w\s]", "", word).strip().lower()
            if w:
                cleaned.add(w)

        self.assertEqual(cleaned, expected)

    def test_invalid_words_type(self):
        with self.assertRaises(ValueError):
            clean_and_validate_input({"words": "notalist", "N": 5})

    def test_invalid_word_elements(self):
        with self.assertRaises(ValueError):
            clean_and_validate_input({"words": ["valid", 123], "N": 5})

    def test_invalid_language(self):
        with self.assertRaises(ValueError):
            clean_and_validate_input({
                "words": ["chat"],
                "native_lang": "Martian",
                "learning_lang": "British English",
                "level": "B1",
                "N": 5
            })

    def test_invalid_level(self):
        with self.assertRaises(ValueError):
            clean_and_validate_input({
                "words": ["chat"],
                "native_lang": "Russian",
                "learning_lang": "British English",
                "level": "B3",
                "N": 5
            })

    def test_invalid_N(self):
        with self.assertRaises(ValueError):
            clean_and_validate_input({
                "words": ["chat"],
                "native_lang": "Russian",
                "learning_lang": "British English",
                "level": "B1",
                "N": 0
            })

if __name__ == "__main__":
    unittest.main()
