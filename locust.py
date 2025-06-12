from locust import HttpUser, task, between

class AuthenticatedApiUser(HttpUser):
    # Wait 1-3 seconds between tasks
    wait_time = between(1, 3)
    
    # The base URL of your API
    host = "http://localhost:8000"  # Change to your API's URL
    
    def on_start(self):
        """Called when a user starts before any tasks are scheduled"""
        # Login to get token
        response = self.client.post(
            "/users/login/",  # Change to your login endpoint
            json={
                "email": "awaemekamichael@gmail.com",  # Use a test user
                "password": "hellomike123"  # Use the test user's password
            }
        )
        # Store the token for future requests
        print(f"Me {response}")
        self.token = response.json()["token"]['access']  # Adjust based on your auth response
    
    @task
    def get_protected_data(self):
        """Example protected endpoint"""
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/products/", headers=headers)  # Change to your endpoint