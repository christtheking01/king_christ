from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, family, FamilyMembership


class UserForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField()

class AdminUserEditForm(forms.ModelForm):
    new_password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        label='New Password',
        required=False,
        help_text="Leave blank to keep current password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        label='Confirm New Password',
        required=False
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'firstname', 'lastname', 'phone', 
                  'is_active', 'is_staff', 'is_superuser']
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and new_password != confirm_password:
            raise forms.ValidationError("Passwords don't match")
        
        return cleaned_data

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    username = forms.CharField(required=True)
    class Meta:
        model = User
        fields = ('email', 'username', 'firstname', 'lastname', 'password1', 'password2', "roles", 'phone')

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        username = cleaned_data.get('username')

        if not email and not username:
            raise forms.ValidationError("You must provide  an email address and a username.")

        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")

class AdminUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    
    # Define role choices explicitly (matching the User model roles)
    ROLE_CHOICES = [
        ('admin','Admin'),
        ('Chairperson','Chairperson'),
        ('Secretary','Secretary'),
        ('Accountant','Accountant'),
        ('Member','Member'),
        ('active_member', 'Active Member'),
        ('priest', 'Priest'),
        ('catechist', 'Catechist'),
        ('treasurer', 'Treasurer'),
        ('vice_chairperson', 'Vice Chairperson'),
        ('coordinator', 'Coordinator'),
        ('liturgical', 'Liturgical'),
        ('evangelization', 'Evangelization'),
        ('youth', 'Youth'),
        ('choir', 'Choir'),
        ('reader', 'Reader'),
    ]
    
    # Role selection for user type
    roles = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='Member',
        label='User Role',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_roles'})
    )
    
    # Priest type - only shown when role is 'priest'
    PRIEST_TYPE_CHOICES = [
        ('', '-- Select Priest Type --'),
        ('parish_priest', 'Parish Priest'),
        ('assistant_priest', 'Assistant Priest'),
        ('normal_priest', 'Normal Priest'),
    ]
    
    priest_type = forms.ChoiceField(
        choices=PRIEST_TYPE_CHOICES,
        required=False,
        label='Priest Type',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_priest_type'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'firstname', 'lastname', 'phone', 'is_active', 'is_staff', 'roles']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'firstname': forms.TextInput(attrs={'class': 'form-control'}),
            'lastname': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        roles = cleaned_data.get('roles')
        priest_type = cleaned_data.get('priest_type')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords don't match")
        
        # Validate priest type when role is priest
        if roles == 'priest' and not priest_type:
            raise forms.ValidationError("Please select a priest type when creating a priest user.")
        
        return cleaned_data
    
    def save(self, commit=True, created_by=None):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.must_change_password = True  # Force password change
        if created_by:
            user.created_by = created_by
        if commit:
            user.save()
            # Handle priest profile creation
            if user.roles == 'priest':
                priest_type = self.cleaned_data.get('priest_type')
                if priest_type:
                    profile, created = UserProfile.objects.get_or_create(user=user)
                    profile.title = priest_type
                    profile.save()
        return user


class FirstTimePasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
        label='Current Password'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
        label='New Password',
        help_text='Password must be at least 8 characters long'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
        label='Confirm New Password'
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError('Current password is incorrect')
        return old_password
    
    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password')
        if len(new_password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long')
        return new_password
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        old_password = cleaned_data.get('old_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("New passwords don't match")
            
            if old_password and new_password == old_password:
                raise forms.ValidationError("New password must be different from current password")
        
        return cleaned_data
    
    def save(self):
        from django.utils import timezone
        password = self.cleaned_data['new_password']
        self.user.set_password(password)
        self.user.must_change_password = False
        self.user.password_changed_at = timezone.now()
        self.user.save()
        return self.user


class FamilyForm(forms.ModelForm):
    class Meta:
        model = family
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter family name',
                'required': True
            })
        }

class FamilyMembershipForm(forms.ModelForm):
    class Meta:
        model = FamilyMembership
        fields = ['user', 'family', 'role']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'family': forms.Select(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter users to show only those without family membership
        if self.instance.pk:
            # For existing membership, exclude current user from other memberships
            self.fields['user'].queryset = User.objects.filter(
                family_membership=None
            ) | User.objects.filter(id=self.instance.user.id)
        else:
            # For new membership, show only users without family
            self.fields['user'].queryset = User.objects.filter(
                family_membership=None
            )
