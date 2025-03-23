from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

class JWTAuthTestCase(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='jwtstudent',
            email='jwtstudent@example.com',
            password='strongpassword123'
        )

    def test_obtain_jwt_token(self):
        response = self.client.post('/api/token/', {
            'username': 'jwtstudent',
            'password': 'strongpassword123'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_invalid_credentials(self):
        response = self.client.post('/api/token/', {
            'username': 'jwtstudent',
            'password': 'wrongpassword'
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)

    def test_refresh_jwt_token(self):
        obtain_response = self.client.post('/api/token/', {
            'username': 'jwtstudent',
            'password': 'strongpassword123'
        })
        refresh_token = obtain_response.data['refresh']

        refresh_response = self.client.post('/api/token/refresh/', {
            'refresh': refresh_token
        })

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)

    def test_invalid_refresh_token(self):
        refresh_response = self.client.post('/api/token/refresh/', {
            'refresh': 'invalidtoken'
        })

        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', refresh_response.data)
