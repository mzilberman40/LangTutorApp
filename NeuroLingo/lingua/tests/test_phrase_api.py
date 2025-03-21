from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from lingua.models import Entity, Phrase

class PhraseAPITestCase(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='phraseuser',
            password='password123'
        )
        self.entity = Entity.objects.create(student=self.student, text_native='Hello', text_target='Hola')
        Phrase.objects.create(entity=self.entity, text_native='How are you?', text_target='¿Cómo estás?')

    def test_get_phrases(self):
        response = self.client.get('/api/phrases/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text_native'], 'How are you?')
