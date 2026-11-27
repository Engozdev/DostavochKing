from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from accounts.models import User
from orders.models import Order, OrderStatusHistory
from orders.services import DeliveryConflict, accept_delivery, assign_courier, assignment_version, complete_delivery, start_delivery
from tests.factories import user
from tests.steps import step


class DeliveryIntegrationTests(TestCase):
    def setUp(self):
        self.client_user = user()
        self.operator = user("operator@example.test", role=User.Role.ADMIN)
        self.courier = user("courier@example.test", role=User.Role.COURIER)
        self.order = Order.objects.create(
            client=self.client_user, delivery_address="Москва, Тестовая 1", total_amount=Decimal("120.00"),
            checkout_key=uuid4(), request_hash="a" * 64, status=Order.Status.CONFIRMED,
        )

    @step("Оператор назначает курьера с актуальной версией назначения")
    def test_assign_courier(self):
        assign_courier(self.operator, order_id=self.order.pk, courier=self.courier,
                       expected_assignment_version=assignment_version(self.order))
        self.order.refresh_from_db()
        self.assertEqual(self.order.courier_id, self.courier.pk)

    @step("Доставка проходит этапы принятия, пути и вручения")
    def test_delivery_lifecycle(self):
        assign_courier(self.operator, order_id=self.order.pk, courier=self.courier)
        accept_delivery(self.courier, order_id=self.order.pk)
        start_delivery(self.courier, order_id=self.order.pk)
        complete_delivery(self.courier, order_id=self.order.pk)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DELIVERED)
        self.assertEqual(OrderStatusHistory.objects.filter(order=self.order).count(), 3)

    @step("Повторное действие в неправильном статусе не продвигает доставку")
    def test_invalid_transition(self):
        assign_courier(self.operator, order_id=self.order.pk, courier=self.courier)
        with self.assertRaises(DeliveryConflict):
            complete_delivery(self.courier, order_id=self.order.pk)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)
