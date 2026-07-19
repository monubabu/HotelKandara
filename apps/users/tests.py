from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

class AuthenticationTests(APITestCase):

    def setUp(self):
        """
        Runs before every test. We populate a test user in the temporary
        test database so we can test the login functionality.
        """
        self.registration_url = reverse('register')  # Resolves to /api/users/register/
        self.login_url = reverse('login')            # Resolves to /api/users/login/
        
        self.user_data = {
            "username": "test_guest",
            "email": "guest@hotel.com",
            "password": "supersecurepassword123",
            "role": "guest",
            "phone_number": "1234567890"
        }
        
        # Create a user directly in the database for the login tests
        self.existing_user = User.objects.create_user(
            username="existing_user",
            email="existing@hotel.com",
            password="existingpassword123",
            role="guest"
        )

    def test_user_registration_successful(self):
        """
        Ensure we can create a new user account through the API endpoint.
        """
        response = self.client.post(self.registration_url, self.user_data, format='json')
        
        # Check that the HTTP status code is 201 CREATED
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that the database actually contains the user now
        self.assertTrue(User.objects.filter(email=self.user_data['email']).exists())
        
        # Verify the returned JSON contains the correct message and fields
        self.assertEqual(response.data['message'], "User registered successfully")
        self.assertEqual(response.data['user']['email'], self.user_data['email'])
        self.assertEqual(response.data['user']['role'], "guest")
        
        # Crucial security check: Ensure the response text doesn't accidentally leak the password hash
        self.assertNotIn('password', response.data['user'])

    def test_user_login_successful_returns_jwt_tokens(self):
        """
        Ensure a user with valid credentials can log in and receive JWT tokens.
        """
        login_credentials = {
            "email": "existing@hotel.com",
            "password": "existingpassword123"
        }
        
        response = self.client.post(self.login_url, login_credentials, format='json')
        
        # Check that the status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify that the frontend gets both access and refresh tokens
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verify user profile data is returned in the token payload block
        self.assertEqual(response.data['user']['email'], "existing@hotel.com")
        self.assertEqual(response.data['user']['role'], "guest")

    def test_user_login_fails_with_invalid_credentials(self):
        """
        Ensure that logging in with an incorrect password fails securely.
        """
        wrong_credentials = {
            "email": "existing@hotel.com",
            "password": "wrongpassword_here"
        }
        
        response = self.client.post(self.login_url, wrong_credentials, format='json')
        
        # Check that the server blocks the request with a 401 UNAUTHORIZED status
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Ensure tokens are NOT included in the failed payload
        self.assertNotIn('access', response.data)
        self.assertEqual(response.data['error'], "Invalid email or password")