from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from lingua.models import Lesson

class LessonAPITestCase(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(username='lessonuser', password='password123')
        Lesson.objects.create(student=self.student, title='Basic Spanish')

    def test_get_lessons(self):
        response = self.client.get('/api/lessons/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Basic Spanish')
