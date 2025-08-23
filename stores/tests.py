# myapp/tests/test_views.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from stores.models import Store, Product # Adjust with your actual app name
from stores.views import ClientViewStore
from rest_framework_simplejwt.tokens import AccessToken
import json


class ClientViewStoreTests(APITestCase):

    def setUp(self):
        # Create a user
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.store = Store.objects.create(name='Test Store', owner=self.user)
        # Create a JWT token for the user
        self.access_token = AccessToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        self.url = reverse('store-detail', kwargs={'store_id': self.store.id})
    
    def test_authenticated_user_can_view_store(self):
        """
        Ensure an authenticated user can successfully view a store.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Store')
        
        
    def test_unauthenticated_user_cannot_view_store(self):
        """
        Ensure unauthenticated users cannot access the store view.
        """
        self.client.credentials()  # Clear any authentication
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_view_store_not_found(self):
        """
        Ensure a 404 response is returned for a non-existent store.
        """
        invalid_url = reverse('store-detail', kwargs={'store_id': 9999})  # An ID that doesn't exist
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Store not found')
        
        
