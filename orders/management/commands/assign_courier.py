from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.core.management.base import BaseCommand, CommandError
from django.http import Http404

from accounts.models import User
from orders.services import DeliveryConflict, assign_courier


def get_user(email):
    try:
        return User.objects.get_by_natural_key(email.strip())
    except User.DoesNotExist as error:
        raise CommandError(f"Учётная запись {email} не найдена.") from error


class Command(BaseCommand):
    help = "Назначить активного курьера подтверждённому заказу."

    def add_arguments(self, parser):
        parser.add_argument("order_id", type=UUID)
        parser.add_argument("courier_email")
        parser.add_argument("--operator-email", required=True)

    def handle(self, *args, **options):
        operator = get_user(options["operator_email"])
        courier = get_user(options["courier_email"])
        try:
            order = assign_courier(operator, order_id=options["order_id"], courier=courier)
        except PermissionDenied as error:
            raise CommandError("Укажите учётную запись активного администратора.") from error
        except Http404 as error:
            raise CommandError("Заказ не найден.") from error
        except DeliveryConflict as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f"Заказ {order.pk} назначен курьеру {courier.email}."))
