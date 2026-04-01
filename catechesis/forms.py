from django import forms
from .models import SacramentRequest, Sacrament,CatechesisMember

class MemberRegistrationForm(forms.ModelForm):
    class Meta:
        model = CatechesisMember
        fields = ['first_name', 'last_name', 'date_of_birth', 'email', 
                  'phone', 'address', 'birth_certificate']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class SacramentRequestForm(forms.ModelForm):
    class Meta:
        model = SacramentRequest
        fields = ['sacrament', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any additional information...'}),
        }


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