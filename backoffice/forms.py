from django import forms

from accounts.models import User


class CourierChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, courier):
        return f"{courier.name} ({courier.email})"


class CourierAssignmentForm(forms.Form):
    assignment_version = forms.RegexField(
        regex=r"\A[0-9a-f]{64}\Z",
        widget=forms.HiddenInput,
        error_messages={
            "required": "Проверьте текущее назначение и отправьте форму снова.",
            "invalid": "Проверьте текущее назначение и отправьте форму снова.",
        },
    )
    courier = CourierChoiceField(
        queryset=User.objects.filter(role=User.Role.COURIER, is_active=True).order_by("name", "email"),
        label="Курьер",
        empty_label="Выберите курьера",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
