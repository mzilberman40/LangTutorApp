from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status


class JWTAuthAPITestCase(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='jwtuser',
            email='jwtuser@example.com',
            password='strongpassword123'
        )

    def test_obtain_jwt_token(self):
        response = self.client.post('/api/token/', {'username': 'jwtuser', 'password': 'strongpassword123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_refresh_jwt_token(self):
        obtain_response = self.client.post('/api/token/', {'username': 'jwtuser', 'password': 'strongpassword123'})
        refresh_token = obtain_response.data['refresh']

        refresh_response = self.client.post('/api/token/refresh/', {'refresh': refresh_token})
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)
