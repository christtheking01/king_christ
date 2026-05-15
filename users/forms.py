from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserProfile, family, FamilyMembership, ChurchMember, ChurchMemberProfile
from member.models import MemberSacrament


class UserForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField()


class MemberSacramentForm(forms.ModelForm):
    """Form for adding/updating sacrament records for a user/member"""
    
    class Meta:
        model = MemberSacrament
        fields = ['sacrament_type', 'date_received', 'place_received', 'minister_name', 
                  'certificate_file', 'supporting_document']
        widgets = {
            'sacrament_type': forms.Select(attrs={'class': 'form-control'}),
            'date_received': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'place_received': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parish/Church name'}),
            'minister_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Priest/Deacon name'}),
            'certificate_file': forms.FileInput(attrs={'class': 'form-control'}),
            'supporting_document': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.member = kwargs.pop('member', None)
        self.requested_by = kwargs.pop('requested_by', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        sacrament = super().save(commit=False)
        
        # Set the user or member relationship
        if self.user:
            sacrament.user = self.user
        if self.member:
            sacrament.member = self.member
        if self.requested_by:
            sacrament.requested_by = self.requested_by
        
        # Default status is pending (needs verification)
        sacrament.verification_status = 'pending'
        
        if commit:
            sacrament.save()
        return sacrament


class SacramentVerificationForm(forms.Form):
    """Form for catechesis staff to verify/reject sacrament records"""
    
    VERIFICATION_ACTIONS = [
        ('verify', 'Verify - Approve Sacrament'),
        ('reject', 'Reject - Request More Information'),
    ]
    
    action = forms.ChoiceField(
        choices=VERIFICATION_ACTIONS,
        widget=forms.RadioSelect,
        label='Verification Action'
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 
                                     'placeholder': 'Enter verification notes or rejection reason...'}),
        label='Verification Notes',
        required=False
    )

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
    
    # Use model role choices directly so form values match the User model exactly
    ROLE_CHOICES = User.ROLE_CHOICES
    
    # Role selection for user type
    roles = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='member',
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
        self.user.force_password_change = False
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


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile information"""
    
    # User fields that can be edited
    firstname = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    lastname = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['title', 'about', 'telephone', 'whatsapp_line', 'facebook_link', 
                  'twitter_link', 'instagram_link', 'picture']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Title/Position'}),
            'about': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about yourself...'}),
            'telephone': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Telephone Number'}),
            'whatsapp_line': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'WhatsApp Number'}),
            'facebook_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://facebook.com/username'}),
            'twitter_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://twitter.com/username'}),
            'instagram_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://instagram.com/username'}),
            'picture': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


# ============================================================================
# CHURCH MEMBER PORTAL FORMS
# ============================================================================

class ChurchMemberRegistrationForm(forms.Form):
    """Registration form for church members - creates User + ChurchMember"""
    
    firstname = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your first name'
        }),
        label='First Name'
    )
    lastname = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your last name'
        }),
        label='Last Name'
    )
    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        }),
        label='Username'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        }),
        label='Email Address'
    )
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+255XXXXXXXXX'
        }),
        label='Phone Number'
    )
    member_code = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 001PT (if you have one)'
        }),
        label='Member Code (Optional)',
        help_text='Enter your member code if you have one. This helps us link your account to your church records.'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password'
        }),
        label='Password',
        help_text='Password must be at least 8 characters long'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        }),
        label='Confirm Password'
    )
    
    VERIFICATION_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('both', 'Both Email & SMS'),
    ]
    
    verification_method = forms.ChoiceField(
        choices=VERIFICATION_CHOICES,
        initial='email',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='How should we send your verification code?'
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if ChurchMember.objects.filter(phone=phone).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords don't match.")
        
        # If member code is provided, validate it exists and matches the name
        member_code = cleaned_data.get('member_code')
        first_name = cleaned_data.get('first_name', '')
        lastname = cleaned_data.get('lastname', '')
        
        if member_code:
            from member.models import Member
            # Combine first and last name to match against Member.name
            full_name = f"{first_name} {lastname}".strip()
            
            # Check both code and name to match the specific member
            member = Member.objects.filter(
                code=member_code,
                name__icontains=full_name,
                active=True
            ).first()
            
            if member:
                cleaned_data['found_member'] = member
            else:
                # Try matching with just first name if full name doesn't match
                member = Member.objects.filter(
                    code=member_code,
                    name__icontains=first_name,
                    active=True
                ).first()
                
                if member:
                    cleaned_data['found_member'] = member
                else:
                    self.add_error('member_code', "Member code and name do not match our records. Please check your code and name or leave blank if you don't have one.")
        
        return cleaned_data


class ChurchMemberVerificationForm(forms.Form):
    """Form for entering verification code"""
    
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': '000000',
            'autocomplete': 'off'
        }),
        label='Verification Code',
        help_text='Enter the 6-digit code sent to you'
    )
    
    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().replace(' ', '')
        if not code:
            raise forms.ValidationError("Please enter the verification code.")
        if not code.isdigit():
            raise forms.ValidationError("Code must contain only numbers.")
        if len(code) != 6:
            raise forms.ValidationError("Code must be exactly 6 digits.")
        return code


class ChurchMemberLoginForm(forms.Form):
    """Login form for church members - authenticates against User model"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email'
        }),
        label='Username / Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your password'
        }),
        label='Password'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate
            from django.contrib.auth import authenticate
            
            # Try username first, then email
            user = authenticate(username=username, password=password)
            
            if not user:
                # Try finding by email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
            
            if not user:
                raise forms.ValidationError("Invalid username/email or password.")
            
            # Check if user has a ChurchMember profile
            try:
                church_member = user.church_member
                if not church_member.is_portal_active:
                    raise forms.ValidationError("Your portal account is not active. Please verify your email/phone or contact admin.")
                cleaned_data['user'] = user
                cleaned_data['church_member'] = church_member
            except ChurchMember.DoesNotExist:
                raise forms.ValidationError("This account is not registered for the member portal. Please use the staff login.")
        
        return cleaned_data


class ChurchMemberProfileForm(forms.ModelForm):
    """Form for editing church member profile"""
    
    class Meta:
        model = ChurchMemberProfile
        fields = ['address', 'city', 'emergency_contact_name', 'emergency_contact_phone',
                  'receive_email_notifications', 'receive_sms_notifications', 'bio']
        widgets = {
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Your home address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City/Town'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency contact name'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+255XXXXXXXXX'
            }),
            'receive_email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'receive_sms_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
        }


class ChurchMemberPasswordChangeForm(forms.Form):
    """Password change form for church members"""
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current password'
        }),
        label='Current Password'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password'
        }),
        label='New Password',
        help_text='Password must be at least 8 characters long'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        label='Confirm New Password'
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        current = self.cleaned_data.get('current_password')
        if not self.user.check_password(current):
            raise forms.ValidationError("Current password is incorrect.")
        return current
    
    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        new = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')
        
        if new and confirm and new != confirm:
            self.add_error('confirm_password', "Passwords don't match.")
        
        return cleaned_data
