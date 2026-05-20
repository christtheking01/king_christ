from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

from .models import CatechesisMember, CatechesisInstructor, SacramentClass, SacramentRequest, Enrollment
from users.models import User

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


class SacramentClassForm(forms.ModelForm):
    class Meta:
        model = SacramentClass
        fields = [
            'name', 'sacrament_type', 'description',
            'start_date', 'end_date', 'class_time', 'meeting_day',
            'location', 'coordinator', 'instructors', 'max_capacity', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sacrament_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'class_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'meeting_day': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'coordinator': forms.Select(attrs={'class': 'form-control'}),
            'instructors': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'max_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Class Name',
            'sacrament_type': 'Sacrament Type',
            'description': 'Description',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'class_time': 'Class Time',
            'meeting_day': 'Meeting Day',
            'location': 'Location',
            'coordinator': 'Coordinator',
            'instructors': 'Instructors',
            'max_capacity': 'Maximum Capacity',
            'status': 'Status',
        }


class CatechesisInstructorForm(forms.ModelForm):
    class Meta:
        model = CatechesisInstructor
        fields = ['entry_type', 'user', 'first_name', 'last_name', 'email', 'phone', 'gender', 'qualification', 'specilization', 'status']
        widgets = {
            'entry_type': forms.Select(attrs={'class': 'form-control', 'id': 'entry_type_select'}),
            'user': forms.Select(attrs={'class': 'form-control', 'id': 'user_select'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'first_name_input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'last_name_input'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'id': 'email_input'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'id': 'phone_input'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'specilization': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'entry_type': 'Entry Type',
            'user': 'Select User',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email',
            'phone': 'Phone',
            'gender': 'Gender',
            'qualification': 'Qualification',
            'specilization': 'Specialization',
            'status': 'Status',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter users to only show those with catechist role and not already instructors
        if self.instance.pk:
            # For editing, exclude current user from the filter
            self.fields['user'].queryset = User.objects.filter(
                roles='catechist'
            ).filter(
                Q(catechesisinstructor__isnull=True) | Q(catechesisinstructor=self.instance)
            )
        else:
            # For creating, only show users with catechist role who are not already instructors
            self.fields['user'].queryset = User.objects.filter(
                roles='catechist',
                catechesisinstructor__isnull=True
            )
        
        # Make manual fields required if entry_type is manual
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['email'].required = False
        self.fields['phone'].required = False
        self.fields['user'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        entry_type = cleaned_data.get('entry_type')
        user = cleaned_data.get('user')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        
        if entry_type == 'user':
            if not user:
                self.add_error('user', 'Please select a user from the system.')
        elif entry_type == 'manual':
            if not first_name:
                self.add_error('first_name', 'First name is required for manual entry.')
            if not last_name:
                self.add_error('last_name', 'Last name is required for manual entry.')
        
        return cleaned_data


class EnrollmentForm(forms.Form):
    """Form for enrolling members in a class"""
    sacrament_class = forms.ModelChoiceField(
        queryset=SacramentClass.objects.filter(status__in=['ACTIVE', 'UPCOMING']),
        required=True,
        empty_label="Select a class...",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    members = forms.ModelMultipleChoiceField(
        queryset=CatechesisMember.objects.filter(is_deleted=False).select_related(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'member-checkbox'}),
        required=False
    )
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search members by name...'
    }))
    
    def __init__(self, *args, **kwargs):
        sacrament_class = kwargs.pop('sacrament_class', None)
        super().__init__(*args, **kwargs)
        
        # If a specific class is provided, set it as the initial value
        if sacrament_class:
            self.fields['sacrament_class'].initial = sacrament_class
            self.fields['sacrament_class'].widget.attrs['disabled'] = True
        
        # Filter members based on selected class
        if sacrament_class:
            self.filter_members_for_class(sacrament_class)
    
    def filter_members_for_class(self, sacrament_class):
        """Filter members based on the selected sacrament class"""
        # Exclude members already enrolled in this class
        enrolled_member_ids = sacrament_class.enrollments.filter(
            status='ENROLLED'
        ).values_list('catechesis_member_id', flat=True)
        
        # Exclude members already enrolled in other classes of same sacrament type
        other_class_enrolled_ids = Enrollment.objects.filter(
            sacrament_class__sacrament_type=sacrament_class.sacrament_type,
            status='ENROLLED'
        ).exclude(
            sacrament_class=sacrament_class
        ).values_list('catechesis_member_id', flat=True)
        
        # Map SacramentRequest sacrament values (lowercase) to SacramentClass sacrament_type values (uppercase)
        sacrament_type_map = {
            'baptism': 'BAPTISM',
            'eucharist': 'FIRST_COMMUNION',
            'confirmation': 'CONFIRMATION',
            'reconciliation': 'RECONCILIATION',
            'marriage': 'CONFIRMATION',
            'holy_orders': 'CONFIRMATION',
            'anointing_sick': 'FIRST_COMMUNION',
        }
        
        # Get the sacrament type to filter by (convert from class type to request type)
        request_sacrament_type = None
        for request_type, class_type in sacrament_type_map.items():
            if class_type == sacrament_class.sacrament_type:
                request_sacrament_type = request_type
                break
        
        if not request_sacrament_type:
            request_sacrament_type = sacrament_class.sacrament_type.lower()
        
        # Filter members who have approved sacrament requests for this type
        approved_request_member_ids = SacramentRequest.objects.filter(
            sacrament=request_sacrament_type,
            status='approved'
        ).values_list('member_id', flat=True)
        
        # Apply all filters
        self.fields['members'].queryset = self.fields['members'].queryset.filter(
            id__in=approved_request_member_ids
        ).exclude(
            id__in=enrolled_member_ids
        ).exclude(
            id__in=other_class_enrolled_ids
        )