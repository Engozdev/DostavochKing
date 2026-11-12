from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email).lower()

    def get_by_natural_key(self, email):
        return self.get(email__iexact=self.normalize_email(email))

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Электронная почта обязательна.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Role.ADMIN)
        if not (
            extra_fields["is_staff"]
            and extra_fields["is_superuser"]
            and extra_fields["role"] == self.model.Role.ADMIN
        ):
            raise ValueError("Суперпользователю нужны права и роль администратора.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Клиент"
        COURIER = "COURIER", "Курьер"
        ADMIN = "ADMIN", "Администратор"

    username = None
    first_name = None
    last_name = None
    name = models.CharField("имя", max_length=150)
    email = models.EmailField("электронная почта", unique=True)
    role = models.CharField("роль", max_length=7, choices=Role, default=Role.CLIENT)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_email_case_insensitive"),
        ]

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name
