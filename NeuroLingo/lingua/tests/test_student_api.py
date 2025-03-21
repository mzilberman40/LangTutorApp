from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

class StudentAPITestCase(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            native_language='English',
            target_language='Spanish',
            proficiency_level='A1'
        )

    def test_get_students(self):
        response = self.client.get('/api/students/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'testuser')
