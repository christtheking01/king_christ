from django import forms
from django.forms import inlineformset_factory
from .models import Member, Ministry, CommunityLeader,Committee,MinistryLeader


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'name', 'code', 'active', 'shepherd', 'ministry', 'telephone',
            'location', 'fathers_name', 'mothers_name', 'guardians_name',
            'new_believer_school', 'pays_tithe', 'working', 'schooling', 'picture','transfer_update','transfered'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 001PT'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+255 XXX XXX XXX'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter location'}),
            'fathers_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mothers_name': forms.TextInput(attrs={'class': 'form-control'}),
            'guardians_name': forms.TextInput(attrs={'class': 'form-control'}),
            'shepherd': forms.Select(attrs={'class': 'form-control'}),
            'ministry': forms.Select(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'new_believer_school': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pays_tithe': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'working': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'schooling': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'transfered': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'transfer_update': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Enter details of the member'}),
            'picture': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
"""    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        if telephone and not telephone.startswith('+'):
            raise forms.ValidationError("Phone number must start with country code (e.g., +255)")
        return telephone"""

class MinistryForm(forms.ModelForm):
    class Meta:
        model = Ministry
        fields = ['name', 'feast_name', 'feast_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter ministry name'
            }),
            'feast_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter feast name'
            }),
            'feast_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }


class MinistryLeaderForm(forms.ModelForm):
    class Meta:
        model = MinistryLeader
        fields = ['leader_name', 'position', 'community', 'phone', 'email', 'appointed_date']
        widgets = {
            'leader_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter leader name'
            }),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'community': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Select community'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+255XXXXXXXXX'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'leader@example.com'
            }),
            'appointed_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'community': 'Community *',
            'leader_name': 'Leader Name *',
            'position': 'Position *',
        }


# Formset for multiple leaders
MinistryLeaderFormSet = inlineformset_factory(
    Ministry,
    MinistryLeader,
    form=MinistryLeaderForm,
    extra=3,  # Number of empty forms to display
    can_delete=True,
    min_num=1,  # Minimum number of leaders required
    validate_min=True
)


class CommitteeForm(forms.ModelForm):
    class Meta:
        model = Committee
        fields = ['Commitee_name', 'description', 'member', 'position', 'phone']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Fix: Add proper styling and make fields optional
        self.fields['Commitee_name'].widget.attrs.update({
            'class': 'input-field committee-name',
            'placeholder': 'Enter committee name',
            'required': 'required'
        })
        
        self.fields['description'].widget.attrs.update({
            'class': 'input-field',
            'placeholder': 'Write the functions of your committee'
        })
        
        # Fix: Use TextInput with datalist instead of Select
        self.fields['member'].widget = forms.TextInput(attrs={
            'class': 'member-search input-field',
            'list': 'member-list',
            'autocomplete': 'off',
            'placeholder': 'Search member...',
            'required': 'required'
        })
        
        self.fields['position'].widget.attrs.update({
            'class': 'input-field',
            'required': 'required'
        })
        
        self.fields['phone'].widget.attrs.update({
            'class': 'phone-display input-field',
            'readonly': 'readonly',
            'placeholder': 'Phone will auto-populate'
        })
        
        # Fix: Make phone not required since it auto-populates
        self.fields['phone'].required = False



class ShepherdForm(forms.ModelForm):
    class Meta:
        model = CommunityLeader
        fields = ['community_name', 'name', 'leader', 'description', 'phone']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

