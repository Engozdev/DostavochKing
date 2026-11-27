from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tests.factories import product, user
from tests.steps import step


class AccountsCatalogIntegrationTests(TestCase):
    @step("Поиск каталога показывает подходящий активный товар")
    def test_catalog_search(self):
        product(name="Молоко")
        product(name="Хлеб")
        product(name="Молоко скрытое", active=False)
        response = self.client.get(reverse("catalog:list"), {"q": "молоко"})
        names = [item.name for item in response.context["page_obj"]]
        self.assertEqual(names, ["Молоко"])

    @step("Оператору доступен список заказов, клиенту доступ запрещён")
    def test_operator_route_checks_role(self):
        client_user = user()
        operator = user("operator@example.test", role=User.Role.ADMIN)
        self.client.force_login(client_user)
        self.assertEqual(self.client.get(reverse("backoffice:list")).status_code, 403)
        self.client.force_login(operator)
        self.assertEqual(self.client.get(reverse("backoffice:list")).status_code, 200)
