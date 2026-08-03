from django import forms
from django.forms import formset_factory
from django.utils import timezone
from .models import TithePayment
from member.models import Member

class TithePaymentForm(forms.ModelForm):
    class Meta:
        model = TithePayment
        fields = ['name', 'guest_name', 'contact_number', 'amount', 'status', 'date']
        widgets = {
            'name': forms.HiddenInput(),
            'guest_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Guest name...'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number...'}),
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rename label for contact_number to match telephone
        self.fields['contact_number'].label = 'Telephone'
        self.fields['guest_name'].required = False
        self.fields['name'].required = False
        
    def clean(self):
        cleaned_data = super().clean()
        member = cleaned_data.get('name')
        guest_name = cleaned_data.get('guest_name')
        
        # Ensure either member or guest name is provided
        if not member and not guest_name:
            raise forms.ValidationError("Please select a member or enter a guest name.")
        
        return cleaned_data


class GuestTithePaymentForm(forms.ModelForm):
    """Dedicated form for guest tithe payments with full details"""
    class Meta:
        model = TithePayment
        fields = ['guest_name', 'contact_number', 'amount', 'status', 'date']
        widgets = {
            'guest_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter guest name...'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number...'
            }),
            'date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'class': 'form-control',
                'placeholder': 'Enter amount...'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['guest_name'].required = True
        self.fields['contact_number'].required = True
        self.fields['amount'].required = True
        self.fields['status'].required = True
        self.fields['date'].required = True
        self.fields['status'].initial = 'cash'
    
    def save(self, commit=True):
        payment = super().save(commit=False)
        payment.name = None  # Ensure no member is linked
        if commit:
            payment.save()
        return payment


class BulkTithePaymentForm(forms.ModelForm):
    member_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control member-search-input',
            'placeholder': 'Search member by name or phone...',
            'autocomplete': 'off'
        }),
        help_text='Type to search for a member'
    )

    class Meta:
        model = TithePayment
        fields = ['name', 'amount', 'status']
        widgets = {
            'name': forms.HiddenInput(attrs={'class': 'form-control member-id-input'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'Amount'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['amount'].required = True
        self.fields['status'].required = True
        self.fields['status'].initial = 'cash'


# Formset for bulk payments
BulkTithePaymentFormSet = formset_factory(
    BulkTithePaymentForm,
    extra=5,
    min_num=1,
    max_num=500,  # Allow up to 500 payments in bulk
    validate_min=True,
    can_delete=True
)


class BulkSMSForm(forms.Form):
    """Form for sending bulk SMS to tithe payment recipients"""
    SMS_TEMPLATE_CHOICES = [
        ('default', 'Default - Payment Confirmation'),
        ('custom', 'Custom Template'),
    ]
    
    recipient_filter = forms.ChoiceField(
        choices=[
            ('all', 'All Recent Payments (Last 30 Days)'),
            ('selected', 'Selected Payments'),
            ('unsent', 'Payments Without SMS'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='all'
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text='Filter payments from this date'
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text='Filter payments until this date'
    )
    
    template_type = forms.ChoiceField(
        choices=SMS_TEMPLATE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='default'
    )
    
    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Available variables: {name}, {amount}, {date}, {payment_method}'
        }),
        help_text='Use {name}, {amount}, {date}, {payment_method} as placeholders'
    )
    
    payment_ids = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text='Comma-separated payment IDs for selected recipients'
    )
    
    rate_limit_delay = forms.IntegerField(
        initial=1,
        min_value=0,
        max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='Delay in seconds between SMS sends (0-10)'
    )