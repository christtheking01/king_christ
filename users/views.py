from django.shortcuts import render, redirect,get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from rest_framework import response
from rest_framework import generics,permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.db.models import Q
from .forms import AdminUserCreationForm, AdminUserEditForm, FirstTimePasswordChangeForm, UserForm, SignupForm, FamilyForm, FamilyMembershipForm
from .models import UserProfile,User, family, FamilyMembership

from member.models import CommunityLeader

def login_user(request):
    template = "registration/login.html"
    form = UserForm()
    context = {"form": form}
    return render(request, template, context)


@csrf_protect
def _logout(request):
    """Handle user logout."""
    logout(request)
    
    # Clear the session
    request.session.flush()
    
    # Redirect to login page
    return redirect('login_user')

def _login(request):
    next_url = request.POST.get('next') or request.GET.get('next') or 'home'
    
    if request.user.is_authenticated:
        if request.user.must_change_password:
            return redirect('change_password')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            if user.force_password_change:
                messages.info(request, 'You must change your password before continuing.')
                return redirect('change_password')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'registration/login.html', {'next': next_url})



def signup(request):
    template = "registration/signup.html"
    form = SignupForm()
    context = {"form": form}
    return render(request, template, context)


def signup_user(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        
        if form.is_valid():
            # Check for existing users
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            
            if User.objects.filter(username=username).exists():
                messages.error(request, "User with that username already exists")
                return render(request, "registration/signup.html", {"form": form})
            
            if User.objects.filter(email=email).exists():
                messages.error(request, "User with that email already exists")
                return render(request, "registration/signup.html", {"form": form})
            
            # Save the user
            user = form.save()
            messages.success(request, "Account created successfully! Please login.")
            return redirect("home")  # Redirect to login after successful registration
            
        else:
            # Form has errors - re-render with error messages
            return render(request, "registration/signup.html", {"form": form})
    
    else:
        # GET request - show empty form
        form = SignupForm()
        return render(request, "registration/signup.html", {"form": form})
    


@login_required
def user_profile(request):
    """
    Display the logged-in user's profile information
    """
    user = request.user
    context = {
        'user_profile': user,
        'user_active':True,
        'user_profile':True
    }
    return render(request, 'registration/user_profile.html', context)

@login_required
def view_user(request, user_id):
    """
    View another user's profile (admin only or for specific use cases)
    """
    user_profile = get_object_or_404(User, id=user_id)
    
    # Add permission logic if needed
    # if not request.user.is_admin and request.user != user_profile:
    #     return redirect('home')
    
    context = {
        'user_profile': user_profile,
        'is_active':True,
        'user_view':True
    }
    return render(request, 'registration/user_profile.html', context)

def is_admin(user):
    return user.is_authenticated and user.roles == 'Admin' or user.is_superuser

@login_required
@user_passes_test(is_admin)
def list_users(request):
    user = User.objects.all()
    users_with_profiles = []
    for users in user:
        users_with_profiles.append({
            'id':users.id,
            'username':users.username,
            'email':users.email,
            'first_name':users.firstname,
            'last_name':users.lastname,
            'roles':users.roles,
            'is_active':users.is_active,
            'date_joined':users.date_joined    
        })

        context ={'users':users_with_profiles}
    return render(request, 'registration/list_users.html', context)

@login_required
@user_passes_test(is_admin)
def create_user(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False, created_by=request.user)
            user.save()
            
            # Handle priest role assignment success message
            if user.roles == 'priest':
                priest_type = form.cleaned_data.get('priest_type')
                if priest_type:
                    priest_type_display = dict(PRIEST_ROLE_CHOICES).get(priest_type, priest_type)
                    messages.success(request, 
                        f'User {user.username} created successfully as {priest_type_display}! '
                        f'They will be required to change their password on first login.')
                else:
                    messages.success(request, 
                        f'User {user.username} created successfully as a Priest! '
                        f'They will be required to change their password on first login.')
            else:
                messages.success(request, 
                    f'User {user.username} created successfully! '
                    f'They will be required to change their password on first login.')
            return redirect('list_users')
    else:
        form = AdminUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form, 'users_active_add': True})


@login_required
def edit_user(request, user_id):
    """
    Enhanced edit user view with proper validation and password handling
    """
    # Permission check
    if not request.user.is_staff :
        messages.warning(request, "Access denied. Admin privileges required.")
        return redirect('home')
    
    editing_user = get_object_or_404(User, id=user_id)
    
    # Check if current user can edit superuser (only superusers can edit other superusers)
    if editing_user.is_superuser and not request.user.is_superuser:
        messages.error(request, "Only superusers can edit superuser accounts.")
        return redirect('list_users')
    
    if request.method == 'POST':
        # Handle form data manually
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        is_active = 'is_active' in request.POST
        is_staff = 'is_staff' in request.POST
        is_superuser = 'is_superuser' in request.POST if request.user.is_superuser else False
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Basic validation
        errors = []
        
        # Check if username already exists (excluding current user)
        if User.objects.filter(username=username).exclude(id=editing_user.id).exists():
            errors.append("Username already exists.")
        
        # Check if email already exists (excluding current user)
        if User.objects.filter(email=email).exclude(id=editing_user.id).exists():
            errors.append("Email already exists.")
        
        # Password validation
        if new_password:
            if len(new_password) < 8:
                errors.append("Password must be at least 8 characters long.")
            if new_password != confirm_password:
                errors.append("Passwords do not match.")
        
        # For non-superusers editing superusers, prevent changes
        if editing_user.is_superuser and not request.user.is_superuser:
            # Keep original values
            username = editing_user.username
            email = editing_user.email
            is_active = editing_user.is_active
            is_staff = True  # Superusers must be staff
            is_superuser = True  # Cannot change superuser status
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Update user
            editing_user.username = username
            editing_user.email = email
            editing_user.first_name = first_name
            editing_user.last_name = last_name
            editing_user.is_active = is_active
            editing_user.is_staff = is_staff
            
            # Only superusers can change superuser status
            if request.user.is_superuser:
                editing_user.is_superuser = is_superuser
            
            # Update password if provided
            if new_password:
                editing_user.set_password(new_password)
                messages.info(request, "Password has been updated.")
            
            editing_user.save()
            messages.success(request, f'User {editing_user.username} updated successfully!')
            return redirect('list_users')
    
    context = {
        'editing_user': editing_user,
        'can_edit_superuser': request.user.is_superuser,
        'is_self_edit': request.user.id == editing_user.id,
    }
    return render(request, 'registration/edit_user.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = FirstTimePasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Keep user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('home')
    else:
        form = FirstTimePasswordChangeForm(request.user)
    
    return render(request, 'registration/change_password.html', {
        'form': form,
        'is_forced': request.user.force_password_change
    })
    

@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Delete a user"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            username = user.username
            
            # Prevent self-deletion
            if request.user.id == user.id:
                messages.error(request, 'You cannot delete your own account!')
            else:
                user.delete()
                messages.success(request, f'User {username} deleted successfully!')
                
        except User.DoesNotExist:
            messages.error(request, 'User not found!')
    
    return redirect('list_users')


def login_api(request):
    if request.method == "POST":
        form = UserForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    response = {"STATUS": "OK", "USER_ID": user.pk}
                    return JsonResponse(response, content_type="Application/json", safe=False)
                else:
                    response = {"STATUS": "INACTIVE"}
                    return JsonResponse(response, content_type="Application/json", safe=False)
            else:
                response = {"STATUS": "INVALID USER CREDENTIALS", "CODE": -1}
                return JsonResponse(response, content_type="Application/json", safe=False)

        else:
            response = {"STATUS": "VALIDATION ERROR"}
            return JsonResponse(response, content_type="Application/json", safe=False)


def signup_api(request):
    if request.method == "POST":
        form = SignupForm(request.POST or None)
        if form.is_valid():
            form.save()
            response = {"STATUS": "OK", "CODE": 0}
            return JsonResponse(response, content_type="Application/json", safe=False)
        else:
            response = {"STATUS": "ERROR", "CODE": -1}
            return JsonResponse(response, content_type="Application/json", safe=False)


# Family Class-Based Views
class FamilyListView(LoginRequiredMixin, ListView):
    """List all families"""
    model = family
    template_name = 'registration/family_list.html'
    context_object_name = 'families'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['family_list_active'] = True
        return context


class FamilyCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create a new family"""
    model = family
    form_class = FamilyForm
    template_name = 'registration/family_form.html'
    success_url = reverse_lazy('family_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'Admin'

    def form_valid(self, form):
        messages.success(self.request, f'Family "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class FamilyDetailView(LoginRequiredMixin, DetailView):
    """View family details"""
    model = family
    template_name = 'registration/family_detail.html'
    context_object_name = 'family'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['family_detail_active'] = True
        context['memberships'] = self.object.memberships.all().select_related('user')
        return context


class FamilyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update family details"""
    model = family
    form_class = FamilyForm
    template_name = 'registration/family_form.html'
    success_url = reverse_lazy('family_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'Admin'

    def form_valid(self, form):
        messages.success(self.request, f'Family "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class FamilyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a family"""
    model = family
    template_name = 'registration/family_confirm_delete.html'
    success_url = reverse_lazy('family_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.roles == 'Admin'

    def delete(self, request, *args, **kwargs):
        family_obj = self.get_object()
        messages.success(request, f'Family "{family_obj.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Family Membership Class-Based Views
class FamilyMembershipListView(LoginRequiredMixin, ListView):
    """List all family memberships"""
    model = FamilyMembership
    template_name = 'registration/family_membership_list.html'
    context_object_name = 'memberships'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membership_list_active'] = True
        return context


class FamilyMembershipCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Add a new family membership"""
    model = FamilyMembership
    form_class = FamilyMembershipForm
    template_name = 'registration/family_membership_form.html'
    success_url = reverse_lazy('family_membership_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'Admin'

    def form_valid(self, form):
        messages.success(self.request, f'Membership for "{form.instance.user.username}" created successfully!')
        return super().form_valid(form)


class FamilyMembershipUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update family membership"""
    model = FamilyMembership
    form_class = FamilyMembershipForm
    template_name = 'registration/family_membership_form.html'
    success_url = reverse_lazy('family_membership_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'Admin'

    def form_valid(self, form):
        messages.success(self.request, f'Membership for "{form.instance.user.username}" updated successfully!')
        return super().form_valid(form)


class FamilyMembershipDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete family membership"""
    model = FamilyMembership
    template_name = 'registration/family_membership_confirm_delete.html'
    success_url = reverse_lazy('family_membership_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'Admin'

    def delete(self, request, *args, **kwargs):
        membership = self.get_object()
        messages.success(request, f'Membership for "{membership.user.username}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


# =============================================================================
# PRIEST ROLE MANAGEMENT VIEWS
# =============================================================================

PRIEST_ROLE_CHOICES = [
    ('parish_priest', 'Parish Priest'),
    ('assistant_priest', 'Assistant Priest'),
    ('normal_priest', 'Normal Priest'),
]


def is_admin_or_staff(user):
    """Check if user is admin, superuser, or staff"""
    return user.is_authenticated and (user.is_superuser or user.is_staff or user.roles in ['admin', 'Admin'])


@login_required
@user_passes_test(is_admin_or_staff)
def priest_role_management(request):
    """
    Display all priests with their role assignments.
    Enforces: 1 Parish Priest, 1 Assistant Priest, many Normal Priests
    """
    # Get all users with priest role
    priests = User.objects.filter(roles='priest')
    
    # Get priest profiles with their specific roles
    # We'll use a custom approach since we need to track priest types
    # For now, we'll use the UserProfile's title field to store priest type
    
    parish_priest = None
    assistant_priest = None
    normal_priests = []
    priests_without_role = []
    
    for priest in priests:
        try:
            profile = priest.userprofile
            priest_type = profile.title or ''
            
            if priest_type == 'parish_priest':
                parish_priest = {
                    'user': priest,
                    'profile': profile,
                    'role_display': 'Parish Priest'
                }
            elif priest_type == 'assistant_priest':
                assistant_priest = {
                    'user': priest,
                    'profile': profile,
                    'role_display': 'Assistant Priest'
                }
            elif priest_type == 'normal_priest':
                normal_priests.append({
                    'user': priest,
                    'profile': profile,
                    'role_display': 'Normal Priest'
                })
            else:
                priests_without_role.append({
                    'user': priest,
                    'profile': profile,
                    'role_display': 'Not Assigned'
                })
        except UserProfile.DoesNotExist:
            priests_without_role.append({
                'user': priest,
                'profile': None,
                'role_display': 'Not Assigned'
            })
    
    # Check for validation issues
    validation_messages = []
    if not parish_priest:
        validation_messages.append("No Parish Priest assigned. Please assign one.")
    if not assistant_priest:
        validation_messages.append("No Assistant Priest assigned. Please assign one.")
    
    context = {
        'parish_priest': parish_priest,
        'assistant_priest': assistant_priest,
        'normal_priests': normal_priests,
        'priests_without_role': priests_without_role,
        'roles_active': True,
        'validation_messages': validation_messages,
        'PRIEST_ROLE_CHOICES': PRIEST_ROLE_CHOICES,
    }
    return render(request, 'registration/priest_role_management.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def assign_priest_role(request, user_id):
    """
    Assign a specific priest role to a user.
    Enforces the constraints: only 1 Parish Priest, 1 Assistant Priest
    """
    priest = get_object_or_404(User, id=user_id, roles='priest')
    
    if request.method == 'POST':
        priest_role = request.POST.get('priest_role')
        
        # Validation: Check constraints
        if priest_role == 'parish_priest':
            # Check if another parish priest exists
            existing = UserProfile.objects.filter(
                title='parish_priest'
            ).exclude(user=priest).first()
            if existing:
                messages.error(request, 
                    f'Cannot assign Parish Priest role. {existing.user.full_name() or existing.user.username} is already the Parish Priest. '
                    f'Please reassign that role first.')
                return redirect('priest_role_management')
                
        elif priest_role == 'assistant_priest':
            # Check if another assistant priest exists
            existing = UserProfile.objects.filter(
                title='assistant_priest'
            ).exclude(user=priest).first()
            if existing:
                messages.error(request, 
                    f'Cannot assign Assistant Priest role. {existing.user.full_name() or existing.user.username} is already the Assistant Priest. '
                    f'Please reassign that role first.')
                return redirect('priest_role_management')
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=priest)
        
        # Store the old role for messaging
        old_role = profile.title
        
        # Assign the new role
        profile.title = priest_role
        profile.save()
        
        role_display = dict(PRIEST_ROLE_CHOICES).get(priest_role, priest_role)
        messages.success(request, 
            f'Successfully assigned {role_display} role to {priest.full_name() or priest.username}.')
        
        return redirect('priest_role_management')
    
    # Get available roles for this priest
    available_roles = list(PRIEST_ROLE_CHOICES)
    
    # Remove restricted roles if already taken by someone else
    if UserProfile.objects.filter(title='parish_priest').exclude(user=priest).exists():
        available_roles = [r for r in available_roles if r[0] != 'parish_priest']
    if UserProfile.objects.filter(title='assistant_priest').exclude(user=priest).exists():
        available_roles = [r for r in available_roles if r[0] != 'assistant_priest']
    
    # Extract just the role values for easier template checking
    available_role_values = [r[0] for r in available_roles]
    
    try:
        current_profile = priest.userprofile
        current_role = current_profile.title
    except UserProfile.DoesNotExist:
        current_profile = None
        current_role = None
    
    context = {
        'priest': priest,
        'current_role': current_role,
        'available_roles': available_roles,
        'available_role_values': available_role_values,
        'PRIEST_ROLE_CHOICES': PRIEST_ROLE_CHOICES,
        'roles_active': True,
    }
    return render(request, 'registration/assign_priest_role.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def remove_priest_role(request, user_id):
    """
    Remove priest role assignment from a user.
    """
    priest = get_object_or_404(User, id=user_id, roles='priest')
    
    if request.method == 'POST':
        try:
            profile = priest.userprofile
            old_role = profile.title
            old_role_display = dict(PRIEST_ROLE_CHOICES).get(old_role, old_role)
            
            # Clear the priest type but keep the profile
            profile.title = ''
            profile.save()
            
            messages.success(request, 
                f'Removed {old_role_display} role from {priest.full_name() or priest.username}.')
        except UserProfile.DoesNotExist:
            messages.info(request, f'{priest.full_name() or priest.username} had no priest role assigned.')
        
        return redirect('priest_role_management')
    
    try:
        profile = priest.userprofile
        current_role = profile.title
        current_role_display = dict(PRIEST_ROLE_CHOICES).get(current_role, current_role)
    except UserProfile.DoesNotExist:
        current_role = None
        current_role_display = None
    
    context = {
        'priest': priest,
        'current_role': current_role,
        'current_role_display': current_role_display,
        'roles_active': True,
    }
    return render(request, 'registration/remove_priest_role.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def priest_list(request):
    """
    List all priests with filtering by role type.
    """
    role_filter = request.GET.get('role', 'all')
    
    # Get all priest users
    priests = User.objects.filter(roles='priest').select_related('userprofile')
    
    # Apply filter
    if role_filter == 'parish_priest':
        priests = [p for p in priests if hasattr(p, 'userprofile') and p.userprofile.title == 'parish_priest']
    elif role_filter == 'assistant_priest':
        priests = [p for p in priests if hasattr(p, 'userprofile') and p.userprofile.title == 'assistant_priest']
    elif role_filter == 'normal_priest':
        priests = [p for p in priests if hasattr(p, 'userprofile') and p.userprofile.title == 'normal_priest']
    elif role_filter == 'unassigned':
        priests = [p for p in priests if not hasattr(p, 'userprofile') or not p.userprofile.title]
    
    # Prepare priest data
    priest_data = []
    for priest in priests:
        try:
            profile = priest.userprofile
            priest_type = profile.title or ''
        except UserProfile.DoesNotExist:
            profile = None
            priest_type = ''
        
        role_display = dict(PRIEST_ROLE_CHOICES).get(priest_type, 'Not Assigned')
        
        priest_data.append({
            'user': priest,
            'profile': profile,
            'priest_type': priest_type,
            'role_display': role_display,
        })
    
    context = {
        'priests': priest_data,
        'role_filter': role_filter,
        'roles_active': True,
        'PRIEST_ROLE_CHOICES': PRIEST_ROLE_CHOICES,
    }
    return render(request, 'registration/priest_list.html', context)
