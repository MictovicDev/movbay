from locust import HttpUser, task, between, events

class MovBayUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Automatically log in when each user is spawned"""
        response = self.client.post("/users/login/", json={
            "email": "awaemekamichael@gmail.com",
            "password": "hellomike123"
        })

        if response.status_code == 200:
            token = response.json().get("token")
            if token:
                self.client.headers.update({
                    "Authorization": f"Bearer {token}"
                })
                self.token = token
                print(token)
            else:
                self.environment.runner.quit()  # login succeeded but no token? stop
        else:
            print(f"Login failed: {response.status_code} {response.text}")
            self.environment.runner.quit()

    # @task(2)
    # def browse_products(self):
    #     self.client.get("/products/")  # headers already include Authorization

        

 