from django import forms
from .models import Notification
from member.models import Member, Ministry, Committee, Community
from datetime import datetime

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = [
            'title',
            'message',
            'recipient_type',
            'target_audience',
            'priority',
            'member',
            'ministry',
            'committee',
            'community',
            'custom_phone_numbers',
            'send_sms'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter notification title'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your message (max 160 characters for single SMS)',
                'rows': 4
            }),
            'recipient_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'target_audience': forms.Select(attrs={
                'class': 'form-control'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control'
            }),
            'member': forms.Select(attrs={
                'class': 'form-control'
            }),
            'ministry': forms.Select(attrs={
                'class': 'form-control'
            }),
            'committee': forms.Select(attrs={
                'class': 'form-control'
            }),
            'community': forms.Select(attrs={
                'class': 'form-control'
            }),
            'custom_phone_numbers': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone numbers separated by commas (e.g., +255712345678, +255723456789)',
                'rows': 3
            }),
            'send_sms': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make recipient fields not required initially
        self.fields['member'].required = False
        self.fields['ministry'].required = False
        self.fields['committee'].required = False
        self.fields['community'].required = False
        self.fields['custom_phone_numbers'].required = False

        # Filter only active members
        self.fields['member'].queryset = Member.objects.active()
        
        # Populate ministry dropdown with available ministries
        self.fields['ministry'].queryset = Ministry.objects.all()
        self.fields['ministry'].empty_label = "Select a Ministry"
        
        # Populate committee dropdown with available committees
        self.fields['committee'].queryset = Committee.objects.all()
        self.fields['committee'].empty_label = "Select a Committee"
        
        # Populate community dropdown with available communities
        self.fields['community'].queryset = Community.objects.all()
        self.fields['community'].empty_label = "Select a Community"
        
            
    def clean(self):
        cleaned_data = super().clean()
        recipient_type = cleaned_data.get('recipient_type')
        member = cleaned_data.get('member')
        ministry = cleaned_data.get('ministry')
        committee = cleaned_data.get('committee')
        community = cleaned_data.get('community')
        custom_phone_numbers = cleaned_data.get('custom_phone_numbers')

        # Validate recipient based on type
        if recipient_type == 'MEMBER' and not member:
            raise forms.ValidationError('Please select a member')
        elif recipient_type == 'MINISTRY' and not ministry:
            raise forms.ValidationError('Please select a ministry')
        elif recipient_type == 'COMMITTEE' and not committee:
            raise forms.ValidationError('Please select a committee')
        elif recipient_type == 'COMMUNITY' and not community:
            raise forms.ValidationError('Please select a community')
        elif recipient_type == 'CUSTOM_PHONES' and not custom_phone_numbers:
            raise forms.ValidationError('Please enter at least one phone number')

        return cleaned_data


class TitheReminderForm(forms.ModelForm):
    """Form for sending tithe reminders with month selection"""
    month = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'month',
            'placeholder': 'YYYY-MM'
        }),
        initial=datetime.now().strftime('%Y-%m'),
        help_text="Select the month for tithe reminders"
    )
    
    DELIVERY_CHOICES = [
        ('both', 'SMS + Portal (Recommended)'),
        ('sms_only', 'SMS Only'),
        ('portal_only', 'Portal Only'),
    ]
    
    delivery_method = forms.ChoiceField(
        choices=DELIVERY_CHOICES,
        initial='both',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'help_text': 'Choose how to send reminders'
        }),
        help_text="Select delivery method for reminders"
    )
    
    class Meta:
        model = Notification
        fields = ['title', 'message', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter reminder title'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter reminder message. Use {member_name} and {month} as placeholders',
                'rows': 4
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove send_sms field since we're using delivery_method
        if 'send_sms' in self.fields:
            del self.fields['send_sms']


class PledgeReminderForm(forms.ModelForm):
    """Form for sending pledge reminders"""
    include_pending = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Include members with pending (unpaid) pledges"
    )
    include_partial = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Include members with partial pledges"
    )
    
    class Meta:
        model = Notification
        fields = ['title', 'message', 'priority', 'send_sms']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter reminder title'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter reminder message. Use {member_name}, {pledge_amount}, {amount_paid}, {balance} as placeholders',
                'rows': 4
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control'
            }),
            'send_sms': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['send_sms'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        include_pending = cleaned_data.get('include_pending', False)
        include_partial = cleaned_data.get('include_partial', False)
        
        if not include_pending and not include_partial:
            raise forms.ValidationError('Please select at least one pledge status (Pending or Partial)')
        
        return cleaned_data
