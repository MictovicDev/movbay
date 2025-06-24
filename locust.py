from locust import HttpUser, task, between

class MovBayUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Log in and store token for future requests"""
        with self.client.post("/users/login/", json={
            "email": "awaemekamichael@gmail.com",
            "password": "hellomike123"
        }, catch_response=True) as response:

            if response.status_code == 200:
                token = response.json().get("token", "").get("access")
                if token:
                    self.client.headers.update({
                        "Authorization": f"Bearer {token}"
                    })
                    response.success()
                else:
                    response.failure("Login success but no token")
                    self.environment.runner.quit()
            else:
                response.failure(f"Login failed: {response.status_code}")
                self.environment.runner.quit()

    @task
    def browse_products(self):
        with self.client.get("/products/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"/products/ failed: {response.status_code} - {response.text}")
