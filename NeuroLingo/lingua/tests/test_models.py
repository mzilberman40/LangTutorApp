from django.test import TestCase
from django.contrib.auth import get_user_model
from lingua.models import Entity, Phrase, Lesson, StudentProgress

class StudentModelTest(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='testuser', email='test@example.com', password='password123',
            native_language='English', target_language='Spanish', proficiency_level='A1'
        )

    def test_student_creation(self):
        self.assertEqual(self.student.username, 'testuser')
        self.assertEqual(self.student.native_language, 'English')
        self.assertEqual(self.student.target_language, 'Spanish')
        self.assertEqual(self.student.proficiency_level, 'A1')

class EntityModelTest(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(username='testuser', password='password123')
        self.entity = Entity.objects.create(student=self.student, text_native='Hello', text_target='Hola')

    def test_entity_creation(self):
        self.assertEqual(self.entity.text_native, 'Hello')
        self.assertEqual(self.entity.text_target, 'Hola')
        self.assertEqual(self.entity.student.username, 'testuser')

class PhraseModelTest(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(username='testuser', password='password123')
        self.entity = Entity.objects.create(student=self.student, text_native='Hello', text_target='Hola')
        self.phrase = Phrase.objects.create(entity=self.entity, text_native='How are you?', text_target='¿Cómo estás?')

    def test_phrase_creation(self):
        self.assertEqual(self.phrase.text_native, 'How are you?')
        self.assertEqual(self.phrase.text_target, '¿Cómo estás?')
        self.assertEqual(self.phrase.entity.text_native, 'Hello')

class LessonModelTest(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(username='testuser', password='password123')
        self.lesson = Lesson.objects.create(student=self.student, title='Basic Spanish')

    def test_lesson_creation(self):
        self.assertEqual(self.lesson.title, 'Basic Spanish')
        self.assertEqual(self.lesson.student.username, 'testuser')

class StudentProgressModelTest(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(username='testuser', password='password123')
        self.entity = Entity.objects.create(student=self.student, text_native='Hello', text_target='Hola')
        self.phrase = Phrase.objects.create(entity=self.entity, text_native='How are you?', text_target='¿Cómo estás?')
        self.progress = StudentProgress.objects.create(student=self.student, phrase=self.phrase, recall_accuracy=80.0, repetition_count=3)

    def test_progress_creation(self):
        self.assertEqual(self.progress.student.username, 'testuser')
        self.assertEqual(self.progress.phrase.text_native, 'How are you?')
        self.assertEqual(self.progress.recall_accuracy, 80.0)
        self.assertEqual(self.progress.repetition_count, 3)
