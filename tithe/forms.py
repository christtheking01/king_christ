from django import forms
from .models import TithePayment
from member.models import Member

class TithePaymentForm(forms.ModelForm):
    class Meta:
        model = TithePayment
        fields = ['name', 'contact_number', 'amount', 'status', 'date']
        widgets = {
            'name': forms.HiddenInput(),
            'contact_number': forms.HiddenInput(),
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rename label for contact_number to match telephone
        self.fields['contact_number'].label = 'Telephone'
        
    def clean(self):
        cleaned_data = super().clean()
        # Ensure member is selected
        if not cleaned_data.get('name'):
            raise forms.ValidationError("Please select a member.")
        return cleaned_data