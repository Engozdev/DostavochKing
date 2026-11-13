from django import forms


class CheckoutForm(forms.Form):
    delivery_address = forms.CharField(
        label="Адрес доставки",
        max_length=500,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "street-address"}),
    )
    checkout_key = forms.UUIDField(widget=forms.HiddenInput)
    quote = forms.CharField(widget=forms.HiddenInput)
