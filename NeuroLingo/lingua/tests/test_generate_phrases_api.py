from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from lingua.models import Entity, Phrase

class GeneratePhrasesAPITestCase(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='aiuser', password='password123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.student)

        Entity.objects.create(student=self.student, text_native="apple", text_target="manzana")
        Entity.objects.create(student=self.student, text_native="book", text_target="libro")

    def test_generate_phrases_from_entities(self):
        response = self.client.post('/api/generate-phrases/', {
            'student_id': self.student.id,
            'num_phrases_per_entity': 2
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertGreaterEqual(Phrase.objects.count(), 4)  # at least 2 per entity

        phrases = Phrase.objects.all()
        self.assertTrue(all(p.entity.student == self.student for p in phrases))
