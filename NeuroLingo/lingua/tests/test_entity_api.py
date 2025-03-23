from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from lingua.models import Entity
from rest_framework.test import APIClient

class EntityAPITestCase(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='entityuser',
            email='entityuser@example.com',
            password='password123',
            native_language='English',
            target_language='Spanish',
            proficiency_level='A1'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.student)

        Entity.objects.create(
            student=self.student,
            text_native='Hello',
            text_target='Hola'
        )

    def test_get_entities(self):
        response = self.client.get('/api/entities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text_native'], 'Hello')

    def test_create_entity(self):
        data = {
            "text_native": "Goodbye",
            "text_target": "Adiós",
            "student": self.student.id
        }
        response = self.client.post('/api/entities/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Entity.objects.count(), 2)
        self.assertEqual(Entity.objects.last().text_target, "Adiós")
