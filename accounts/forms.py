from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm

from .models import User


EMAIL_EXISTS = "Пользователь с такой электронной почтой уже зарегистрирован."


class RegistrationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("name", "email")
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name", "autofocus": True}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(EMAIL_EXISTS)
        return email


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "autofocus": True, "class": "form-control"}
        ),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "class": "form-control"}),
    )
