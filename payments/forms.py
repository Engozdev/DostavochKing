from django import forms

from .models import PaymentAttempt


class MockPaymentForm(forms.Form):
    attempt_key = forms.UUIDField(widget=forms.HiddenInput)
    outcome = forms.ChoiceField(choices=[
        (result.value, result.label)
        for result in (PaymentAttempt.Result.SUCCEEDED, PaymentAttempt.Result.FAILED)
    ])
