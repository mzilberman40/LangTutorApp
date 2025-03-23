from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from lingua.models import Entity, Phrase

class PhraseAPITestCase(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='phraseuser',
            password='password123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.student)

        self.entity = Entity.objects.create(
            student=self.student,
            text_native='Hi',
            text_target='Hola'
        )

        Phrase.objects.create(
            entity=self.entity,
            text_native='How are you?',
            text_target='¿Cómo estás?'
        )

    def test_get_phrases(self):
        response = self.client.get('/api/phrases/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text_native'], 'How are you?')

    def test_create_phrase(self):
        data = {
            "entity": self.entity.id,
            "text_native": "Nice to meet you",
            "text_target": "Mucho gusto"
        }
        response = self.client.post('/api/phrases/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Phrase.objects.count(), 2)
        self.assertEqual(Phrase.objects.last().text_target, "Mucho gusto")
