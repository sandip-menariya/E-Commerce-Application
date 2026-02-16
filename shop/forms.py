from django import forms
from .models import UserAddressModel, MerchantAccount

class UserAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddressModel
        fields = ["full_name", "mobile", "country", "state", "city", "postal_code", "address_line"] 
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "input form-control"}),
            "address_line": forms.TextInput(attrs={"class": "input form-control"}),
            "mobile": forms.TextInput(attrs={"class": "input form-control"}),
            "state": forms.TextInput(attrs={"class": "input form-control"}),
            "city": forms.TextInput(attrs={"class": "input form-control"}),
            "country": forms.TextInput(attrs={"class": "input form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "input form-control"}),
        }
class MerchantRegistrationForm(forms.ModelForm):
    class Meta:
        model=MerchantAccount
        fields=["shop_name","description","adhar_card","pan_card","bank_details"]
        widgets={
            "shop_name":forms.TextInput(attrs={"class":"input form-control"}),
            "description":forms.Textarea(attrs={"class":"input form-control"}),
            "adhar_card":forms.TextInput(attrs={"class":"input form-control"}),
            "pan_card":forms.TextInput(attrs={"class":"input form-control"}),
            "bank_details":forms.TextInput(attrs={"class":"input form-control"}),
        }