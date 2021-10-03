import time

from locust import HttpUser, task, between


class WebsiteDeliver(HttpUser):
    """Тестирование GET и POST запросов."""

    wait_time = between(5, 15)

    @task  # type: ignore
    def post_page(self) -> None:
        """Проверка POST запросов(создание и обновление доставок)."""
        for deliver_id in range(100, 250):
            self.client.post("/deliveries/", json={"id": str(deliver_id), "status": "to_do"})
            time.sleep(1)

    @task(3)  # type: ignore
    def get_page(self) -> None:
        """Проверка GET запросов(получение списка всех доставок)."""
        self.client.get("/deliveries/")
