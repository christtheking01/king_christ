from django import forms
from .models import Notification
from member.models import Member, Ministry, Community

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = [
            'title',
            'message',
            'recipient_type',
            'member',
            'ministry',
            'community',
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
            'member': forms.Select(attrs={
                'class': 'form-control'
            }),
            'ministry': forms.Select(attrs={
                'class': 'form-control'
            }),
            'community': forms.Select(attrs={
                'class': 'form-control'
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
        self.fields['community'].required = False
        
        # Filter only active members
        self.fields['member'].queryset = Member.objects.active()
    
    def clean(self):
        cleaned_data = super().clean()
        recipient_type = cleaned_data.get('recipient_type')
        member = cleaned_data.get('member')
        ministry = cleaned_data.get('ministry')
        community = cleaned_data.get('community')
        
        # Validate recipient based on type
        if recipient_type == 'MEMBER' and not member:
            raise forms.ValidationError('Please select a member')
        elif recipient_type == 'MINISTRY' and not ministry:
            raise forms.ValidationError('Please select a ministry')
        elif recipient_type == 'COMMUNITY' and not community:
            raise forms.ValidationError('Please select a community')
        
        return cleaned_data
