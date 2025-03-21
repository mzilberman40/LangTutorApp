from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from lingua.models import Entity, Phrase, StudentProgress

class StudentProgressAPITestCase(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(username='progressuser', password='password123')
        self.entity = Entity.objects.create(student=self.student, text_native='Hello', text_target='Hola')
        self.phrase = Phrase.objects.create(entity=self.entity, text_native='How are you?', text_target='¿Cómo estás?')
        StudentProgress.objects.create(student=self.student, phrase=self.phrase, recall_accuracy=80.0, repetition_count=3)

    def test_get_student_progress(self):
        response = self.client.get('/api/student-progress/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['recall_accuracy'], 80.0)
