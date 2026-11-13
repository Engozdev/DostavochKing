from django import forms

from .models import PaymentAttempt


class MockPaymentForm(forms.Form):
    attempt_key = forms.UUIDField(widget=forms.HiddenInput)
    outcome = forms.ChoiceField(choices=PaymentAttempt.Result.choices)
