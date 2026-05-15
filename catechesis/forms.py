from django import forms
from .models import SacramentRequest, Sacrament, CatechesisMember

class MemberRegistrationForm(forms.ModelForm):
    class Meta:
        model = CatechesisMember
        fields = [
            'member_category', 'first_name', 'last_name', 'gender', 'date_of_birth', 
            'place_of_birth', 'nationality',
            'email', 'phone', 'address',
            'parent_guardian_name', 'parent_guardian_phone', 'parent_guardian_email',
            'father_name', 'father_religion',
            'mother_name', 'mother_religion',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
            'medical_notes', 'previous_parish',
            'godparent_sponsor_name', 'godparent_sponsor_religion',
            'birth_certificate', 'baptism_certificate'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'medical_notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Any allergies or medical conditions...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email optional (required=False)
        self.fields['email'].required = False
        self.fields['phone'].required = False
        # Add help texts
        self.fields['gender'].widget.attrs['class'] = 'form-control'
        self.fields['father_religion'].widget.attrs['class'] = 'form-control'
        self.fields['mother_religion'].widget.attrs['class'] = 'form-control'
        self.fields['godparent_sponsor_religion'].widget.attrs['class'] = 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        member_category = cleaned_data.get('member_category')
        email = cleaned_data.get('email')
        parent_guardian_name = cleaned_data.get('parent_guardian_name')
        parent_guardian_phone = cleaned_data.get('parent_guardian_phone')
        
        # Adults (18+) require email
        if member_category == 'adult' and not email:
            self.add_error('email', 'Email is required for adult members.')
        
        # Minors (child, teen) require parent/guardian info
        if member_category in ['child', 'teen']:
            if not parent_guardian_name:
                self.add_error('parent_guardian_name', 'Parent/Guardian name is required for minors.')
            if not parent_guardian_phone:
                self.add_error('parent_guardian_phone', 'Parent/Guardian phone is required for minors.')
        
        return cleaned_data


class SacramentRequestForm(forms.ModelForm):
    class Meta:
        model = SacramentRequest
        fields = ['sacrament', 'notes']
        widgets = {
            'sacrament': forms.Select(attrs={'class': 'form-control', 'id': 'id_sacrament'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any additional information...', 'class': 'form-control'}),
        }
        labels = {
            'sacrament': 'Select Sacrament',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add empty choice at the beginning
        from .models import SacramentRequest
        choices = [('', '-- Choose a Sacrament --')] + list(SacramentRequest.SACRAMENT_CHOICES)
        self.fields['sacrament'].choices = choices
        self.fields['sacrament'].required = True


class ReviewForm(forms.Form):
    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter review notes...'}),
        required=True,
        label='Review Notes'
    )
    scheduled_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label='Schedule Date (if approving)'
    )
    send_notification = forms.BooleanField(
        initial=True,
        required=False,
        label='Send SMS/Email notification to member'
    )