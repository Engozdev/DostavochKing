from django import forms


class AddItemForm(forms.Form):
    quantity = forms.IntegerField(label="Количество", min_value=1)


class RemoveItemForm(forms.Form):
    version = forms.IntegerField(label="Версия корзины", min_value=0, widget=forms.HiddenInput)


class UpdateItemForm(AddItemForm, RemoveItemForm):
    pass
