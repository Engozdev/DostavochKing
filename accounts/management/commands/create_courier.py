import warnings
from getpass import GetPassWarning, getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from accounts.models import User


class Command(BaseCommand):
    help = "Создать учётную запись курьера с паролем, введённым в терминале."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", required=True)

    def handle(self, *args, **options):
        user = User(email=options["email"].strip(), name=options["name"].strip(), role=User.Role.COURIER)
        try:
            user.full_clean(exclude=["password"])
            with warnings.catch_warnings():
                warnings.simplefilter("error", GetPassWarning)
                password = getpass("Пароль курьера: ")
                confirmation = getpass("Повторите пароль: ")
            if password != confirmation:
                raise CommandError("Пароли не совпадают.")
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        except (EOFError, GetPassWarning, KeyboardInterrupt) as error:
            raise CommandError("Для ввода пароля запустите команду в интерактивном терминале.") from error

        user.set_password(password)
        try:
            with transaction.atomic():
                user.save()
        except IntegrityError as error:
            if User.objects.filter(email__iexact=user.email).exists():
                raise CommandError("Пользователь с такой электронной почтой уже зарегистрирован.") from error
            raise
        self.stdout.write(self.style.SUCCESS(f"Создан курьер {user.email}."))
