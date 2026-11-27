from types import SimpleNamespace

from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase

from accounts.access import require_admin, require_client, require_courier
from accounts.models import User
from tests.steps import step


class AccessRulesTests(SimpleTestCase):
    @step("Клиент не получает права оператора")
    def test_client_cannot_act_as_admin(self):
        actor = SimpleNamespace(is_authenticated=True, is_active=True, role=User.Role.CLIENT)
        with self.assertRaises(PermissionDenied):
            require_admin(actor)

    @step("Заблокированный пользователь не проходит проверку роли")
    def test_inactive_user_is_denied(self):
        actor = SimpleNamespace(is_authenticated=True, is_active=False, role=User.Role.COURIER)
        with self.assertRaises(PermissionDenied):
            require_courier(actor)

    @step("Активный клиент проходит проверку роли")
    def test_active_client_is_allowed(self):
        actor = SimpleNamespace(is_authenticated=True, is_active=True, role=User.Role.CLIENT)
        self.assertIsNone(require_client(actor))
