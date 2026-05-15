from functools import wraps
from django.shortcuts import render, redirect,get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_protect
from django.conf import settings
from django.core.paginator import Paginator
from rest_framework import response
from rest_framework import generics,permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum
from chartjs.views.lines import BaseLineChartView
from .forms import AdminUserCreationForm, AdminUserEditForm, FirstTimePasswordChangeForm, UserForm, SignupForm, FamilyForm, FamilyMembershipForm, UserProfileForm
from .models import UserProfile,User, family, FamilyMembership

from member.models import CommunityLeader
from tithe.models import TithePayment
from events.models import Event, EventRegistration
from finance.models import EventPledge

def anonymous_required(function=None, redirect_url=None):
    """Decorator that redirects authenticated users away from login pages.
    Church members are redirected to the portal, staff to home."""
    def check_anonymous(user):
        if not user.is_authenticated:
            return True
        return False
    
    def get_redirect_url(user):
        # If user is a church member, redirect to portal
        if hasattr(user, 'church_member') and user.church_member.is_portal_active:
            return 'portal_dashboard'
        return redirect_url or settings.LOGIN_REDIRECT_URL or 'home'
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                redirect_to = get_redirect_url(request.user)
                return redirect(redirect_to)
            return view_func(request, *args, **kwargs)
        return wrapper
    
    if function:
        return decorator(function)
    return decorator


def staff_only(view_func):
    """Decorator to restrict views to staff only - church members are redirected to portal."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page.")
            return redirect('login_user')
        
        # Check if user is a church member (not staff)
        if hasattr(request.user, 'church_member') and request.user.church_member.is_portal_active:
            messages.warning(request, "Please use the member portal for church member access.")
            return redirect('portal_dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


@anonymous_required
def login_user(request):
    """Display login form - redirects authenticated users appropriately."""
    template = "registration/login.html"
    form = UserForm()
    next_url = request.GET.get('next') or ''
    context = {"form": form, "next": next_url, "redirect_to": request.get_full_path()}
    
    response = render(request, template, context)
    
    # Prevent browser from caching this page - fixes back-button issues
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    response['Vary'] = 'Cookie'
    
    return response


@csrf_protect
def _logout(request):
    """Handle user logout."""
    logout(request)
    
    # Clear the session
    request.session.flush()
    
    # Redirect to login page
    return redirect('login_user')

@anonymous_required
def _login(request):
    """Unified login for staff and church members - POST handler."""
    next_url = request.POST.get('next') or request.GET.get('next')
    
    if request.method == 'POST':
        username_input = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Try to authenticate
        user = None
        
        # First try username
        user = authenticate(request, username=username_input, password=password)
        
        # If not found, try finding by email
        if not user:
            try:
                user_obj = User.objects.get(email__iexact=username_input)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            # Check if user is active
            if not user.is_active:
                messages.error(request, 'Your account is inactive. Please contact the administrator.')
                response = render(request, 'registration/login.html', {'next': next_url})
                _add_no_cache_headers(response)
                return response
            
            # Check if this is a portal user (has ChurchMember)
            try:
                church_member = user.church_member
                if not church_member.is_portal_active:
                    messages.error(request, 'Your portal account is not active. Please verify your email/phone or contact admin.')
                    response = render(request, 'registration/login.html', {'next': next_url})
                    _add_no_cache_headers(response)
                    return response
                # It's a portal user - log them in
                login(request, user)
                request.session['is_church_member'] = True
                messages.success(request, f'Welcome back, {church_member.get_full_name()}!')
                # Use reverse for proper URL resolution
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect('portal_dashboard')
            except (ChurchMember.DoesNotExist, User.church_member.RelatedObjectDoesNotExist):
                # It's a staff user (no ChurchMember profile)
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                # Use reverse for proper URL resolution
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect('home')
        else:
            messages.error(request, 'Invalid username/email or password.')
    
    response = render(request, 'registration/login.html', {'next': next_url})
    _add_no_cache_headers(response)
    return response


def _add_no_cache_headers(response):
    """Add cache-control headers to prevent back-button issues."""
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    response['Vary'] = 'Cookie'
    return response


def _redirect_after_login(request, user):
    """Redirect user based on their type after login"""
    try:
        church_member = user.church_member
        if church_member.is_portal_active:
            return redirect('portal_dashboard')
    except ChurchMember.DoesNotExist:
        pass
    return redirect('home')



@anonymous_required
def signup(request):
    """Display signup form - redirects authenticated users to home."""
    template = "registration/signup.html"
    form = SignupForm()
    context = {"form": form}
    
    response = render(request, template, context)
    
    # Prevent browser from caching this page
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@anonymous_required
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
def edit_profile(request):
    """
    Edit user profile information
    """
    user = request.user
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Save profile
            profile = form.save()
            # Update user fields
            user.firstname = form.cleaned_data.get('firstname', user.firstname)
            user.lastname = form.cleaned_data.get('lastname', user.lastname)
            user.phone = form.cleaned_data.get('phone', user.phone)
            user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_profile')
    else:
        # Initialize form with current values
        form = UserProfileForm(instance=profile, initial={
            'firstname': user.firstname,
            'lastname': user.lastname,
            'phone': user.phone,
        })
    
    return render(request, 'registration/edit_profile.html', {
        'form': form,
        'user': user,
        'profile': profile,
        'user_active': True,
    })

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
    return user.is_authenticated and user.roles == 'admin' or user.is_superuser

@login_required
@user_passes_test(is_admin)
def list_users(request):
    # Filter users by specific roles as requested
    allowed_roles = [
        'admin', 'chairperson', 'vice_chairperson', 'secretary', 
        'accountant', 'treasurer', 'member', 'active_member',
        'priest', 'catechist', 'coordinator'
    ]
    
    # Base queryset - filter by allowed roles and exclude church members
    # Church members have their own separate management list
    users = User.objects.filter(
        roles__in=allowed_roles
    ).exclude(
        church_member__isnull=False
    ).order_by('-date_joined')
    
    # Pagination - 20 items per page
    from django.core.paginator import Paginator
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare user data
    users_with_profiles = []
    for user in page_obj:
        users_with_profiles.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.firstname,
            'last_name': user.lastname,
            'roles': user.roles,
            'is_active': user.is_active,
            'date_joined': user.date_joined,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'last_login': user.last_login,
        })
    
    context = {
        'page_obj': page_obj,
        'users': users_with_profiles,
    }
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
    # Permission check - raises 403 if user lacks permission
    if not request.user.is_staff:
        raise PermissionDenied("You don't have permission to edit users. Admin privileges required.")
    
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
            editing_user.firstname = first_name
            editing_user.lastname = last_name
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
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'admin'

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
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'admin'

    def form_valid(self, form):
        messages.success(self.request, f'Family "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class FamilyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a family"""
    model = family
    template_name = 'registration/family_confirm_delete.html'
    success_url = reverse_lazy('family_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.roles == 'admin'

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
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'admin'

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
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'admin'

    def form_valid(self, form):
        messages.success(self.request, f'Membership for "{form.instance.user.username}" updated successfully!')
        return super().form_valid(form)


class FamilyMembershipDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete family membership"""
    model = FamilyMembership
    template_name = 'registration/family_membership_confirm_delete.html'
    success_url = reverse_lazy('family_membership_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff or self.request.user.roles == 'admin'

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
    return user.is_authenticated and (user.is_superuser or user.is_staff or user.roles == 'admin')


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
    
    # Pagination - 20 items per page
    paginator = Paginator(priest_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'priests': page_obj,
        'role_filter': role_filter,
        'roles_active': True,
        'PRIEST_ROLE_CHOICES': PRIEST_ROLE_CHOICES,
    }
    return render(request, 'registration/priest_list.html', context)


# =============================================================================
# SACRAMENT MANAGEMENT VIEWS
# =============================================================================

from member.models import MemberSacrament
from .forms import MemberSacramentForm, SacramentVerificationForm


@login_required
def user_sacraments(request, user_id=None):
    """
    Display all sacraments for a user.
    If no user_id provided, shows current user's sacraments.
    """
    if user_id:
        # Permission check - only admins or the user themselves can view
        target_user = get_object_or_404(User, id=user_id)
        if not (request.user.is_staff or request.user.is_superuser or request.user.id == int(user_id)):
            messages.error(request, "You don't have permission to view this user's sacraments.")
            return redirect('home')
    else:
        target_user = request.user
    
    # Get sacraments for the user
    sacraments = MemberSacrament.objects.filter(user=target_user).order_by('-created_at')
    
    # Count by status
    verified_count = sacraments.filter(verification_status='verified').count()
    pending_count = sacraments.filter(verification_status='pending').count()
    rejected_count = sacraments.filter(verification_status='rejected').count()
    
    context = {
        'target_user': target_user,
        'sacraments': sacraments,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'is_own_profile': request.user.id == target_user.id,
        'user_sacraments_active': True,
    }
    return render(request, 'registration/user_sacraments.html', context)


@login_required
def add_user_sacrament(request, user_id):
    """
    Add a sacrament record for a user.
    The sacrament will be saved but marked as pending verification.
    """
    target_user = get_object_or_404(User, id=user_id)
    
    # Permission check
    if not (request.user.is_staff or request.user.is_superuser or request.user.id == int(user_id)):
        messages.error(request, "You don't have permission to add sacraments for this user.")
        return redirect('home')
    
    if request.method == 'POST':
        form = MemberSacramentForm(request.POST, request.FILES, 
                                    user=target_user, 
                                    requested_by=request.user)
        if form.is_valid():
            sacrament = form.save()
            messages.success(request, 
                f'{sacrament.get_sacrament_type_display()} record added successfully. '
                f'It is now pending verification by catechesis staff.')
            
            # Redirect back to user sacraments list
            return redirect('user_sacraments', user_id=user_id)
    else:
        form = MemberSacramentForm(user=target_user, requested_by=request.user)
    
    context = {
        'form': form,
        'target_user': target_user,
        'is_own_profile': request.user.id == target_user.id,
        'adding_sacrament': True,
    }
    return render(request, 'registration/add_sacrament.html', context)


@login_required
def edit_user_sacrament(request, sacrament_id):
    """
    Edit a sacrament record.
    Only allowed if sacrament is still pending (not yet verified).
    """
    sacrament = get_object_or_404(MemberSacrament, id=sacrament_id)
    target_user = sacrament.user or sacrament.member
    
    # Permission check
    if not (request.user.is_staff or request.user.is_superuser or 
            (sacrament.user and request.user.id == sacrament.user.id)):
        messages.error(request, "You don't have permission to edit this sacrament.")
        return redirect('home')
    
    # Can only edit if still pending
    if sacrament.verification_status != 'pending':
        messages.error(request, 
            f"Cannot edit - this sacrament has already been {sacrament.get_verification_status_display().lower()}.")
        return redirect('user_sacraments', user_id=sacrament.user.id if sacrament.user else 0)
    
    if request.method == 'POST':
        form = MemberSacramentForm(request.POST, request.FILES, instance=sacrament)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sacrament record updated successfully.')
            return redirect('user_sacraments', user_id=sacrament.user.id if sacrament.user else 0)
    else:
        form = MemberSacramentForm(instance=sacrament)
    
    context = {
        'form': form,
        'sacrament': sacrament,
        'target_user': target_user,
        'editing': True,
    }
    return render(request, 'registration/edit_sacrament.html', context)


@login_required
def delete_user_sacrament(request, sacrament_id):
    """
    Delete a sacrament record.
    Only allowed if sacrament is still pending.
    """
    sacrament = get_object_or_404(MemberSacrament, id=sacrament_id)
    user_id = sacrament.user.id if sacrament.user else 0
    
    # Permission check
    if not (request.user.is_staff or request.user.is_superuser or 
            (sacrament.user and request.user.id == sacrament.user.id)):
        messages.error(request, "You don't have permission to delete this sacrament.")
        return redirect('home')
    
    # Can only delete if still pending
    if sacrament.verification_status != 'pending':
        messages.error(request, 
            f"Cannot delete - this sacrament has already been {sacrament.get_verification_status_display().lower()}.")
        return redirect('user_sacraments', user_id=user_id)
    
    if request.method == 'POST':
        sacrament_type = sacrament.get_sacrament_type_display()
        sacrament.delete()
        messages.success(request, f'{sacrament_type} record deleted successfully.')
        return redirect('user_sacraments', user_id=user_id)
    
    context = {
        'sacrament': sacrament,
    }
    return render(request, 'registration/delete_sacrament_confirm.html', context)


# =============================================================================
# CATECHESIS VERIFICATION VIEWS
# =============================================================================

def can_verify_sacraments(user):
    """Check if user can verify sacraments (catechist, admin, priest, etc.)"""
    return user.is_authenticated and user.is_approver()


@login_required
@user_passes_test(can_verify_sacraments)
def pending_sacraments_list(request):
    """
    List all sacraments pending verification.
    For catechesis staff to review and verify.
    """
    status_filter = request.GET.get('status', 'pending')
    sacrament_type = request.GET.get('type', '')
    
    sacraments = MemberSacrament.objects.all()
    
    # Apply filters
    if status_filter:
        sacraments = sacraments.filter(verification_status=status_filter)
    if sacrament_type:
        sacraments = sacraments.filter(sacrament_type=sacrament_type)
    
    # Order by oldest first (FIFO for verification)
    sacraments = sacraments.order_by('created_at')
    
    # Count statistics
    pending_count = MemberSacrament.objects.filter(verification_status='pending').count()
    under_review_count = MemberSacrament.objects.filter(verification_status='under_review').count()
    verified_count = MemberSacrament.objects.filter(verification_status='verified').count()
    rejected_count = MemberSacrament.objects.filter(verification_status='rejected').count()
    
    context = {
        'sacraments': sacraments,
        'status_filter': status_filter,
        'sacrament_type': sacrament_type,
        'pending_count': pending_count,
        'under_review_count': under_review_count,
        'verified_count': verified_count,
        'rejected_count': rejected_count,
        'verification_active': True,
        'SACRAMENT_CHOICES': MemberSacrament.SACRAMENT_CHOICES,
    }
    return render(request, 'catechesis/pending_sacraments.html', context)


@login_required
@user_passes_test(can_verify_sacraments)
def verify_sacrament(request, sacrament_id):
    """
    Verify or reject a sacrament record.
    Only accessible to catechesis staff.
    """
    sacrament = get_object_or_404(MemberSacrament, id=sacrament_id)
    
    # Check if user can verify this specific sacrament type
    if not request.user.can_approve_sacrament(sacrament.sacrament_type):
        messages.error(request, 
            f"You don't have permission to verify {sacrament.get_sacrament_type_display()} records.")
        return redirect('pending_sacraments_list')
    
    if request.method == 'POST':
        form = SacramentVerificationForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            notes = form.cleaned_data['notes']
            
            if action == 'verify':
                sacrament.verify(request.user, notes)
                messages.success(request, 
                    f'{sacrament.get_sacrament_type_display()} for '
                    f'{sacrament.user.get_full_name() if sacrament.user else sacrament.member.name} '
                    f'has been verified successfully.')
            else:
                sacrament.reject(request.user, notes)
                messages.warning(request, 
                    f'{sacrament.get_sacrament_type_display()} for '
                    f'{sacrament.user.get_full_name() if sacrament.user else sacrament.member.name} '
                    f'has been rejected. Reason: {notes}')
            
            return redirect('pending_sacraments_list')
    else:
        form = SacramentVerificationForm()
        # Set status to under_review when someone starts reviewing
        if sacrament.verification_status == 'pending':
            sacrament.verification_status = 'under_review'
            sacrament.save()
    
    context = {
        'sacrament': sacrament,
        'form': form,
        'target_person': sacrament.user or sacrament.member,
    }
    return render(request, 'catechesis/verify_sacrament.html', context)


@login_required
@user_passes_test(can_verify_sacraments)
def sacrament_detail(request, sacrament_id):
    """
    View detailed information about a sacrament record.
    For catechesis staff to review before verification.
    """
    sacrament = get_object_or_404(MemberSacrament, id=sacrament_id)
    
    context = {
        'sacrament': sacrament,
        'target_person': sacrament.user or sacrament.member,
        'can_verify': request.user.can_approve_sacrament(sacrament.sacrament_type),
    }
    return render(request, 'catechesis/sacrament_detail.html', context)


# ============================================================================
# CHURCH MEMBER PORTAL VIEWS
# ============================================================================

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.utils import timezone
from .models import ChurchMember, ChurchMemberProfile
from .forms import (
    ChurchMemberRegistrationForm, 
    ChurchMemberVerificationForm,
    ChurchMemberLoginForm,
    ChurchMemberProfileForm,
    ChurchMemberPasswordChangeForm
)
from member.models import Member, Community, Ministry, Committee, MemberSacrament
from events.models import Event, EventRegistration
from finance.models import EventPledge, PledgePayment
from tithe.models import TithePayment


def portal_register(request):
    """Handle church member registration - stores data in session, creates User only after verification"""
    if request.method == 'POST':
        form = ChurchMemberRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Check for duplicate email or username BEFORE sending verification
                email = form.cleaned_data['email']
                username = form.cleaned_data['username']
                
                if User.objects.filter(email=email).exists():
                    messages.error(request, "An account with this email already exists. Please log in or use a different email.")
                    return render(request, 'portal/register.html', {'form': form})
                
                if User.objects.filter(username=username).exists():
                    messages.error(request, "This username is already taken. Please choose a different one.")
                    return render(request, 'portal/register.html', {'form': form})
                
                # Store registration data in session (don't create user yet)
                registration_data = {
                    'username': username,
                    'email': email,
                    'password': form.cleaned_data['password'],  # Will be hashed after verification
                    'firstname': form.cleaned_data['firstname'],
                    'lastname': form.cleaned_data['lastname'],
                    'phone': str(form.cleaned_data['phone']),
                    'member_code': form.cleaned_data.get('member_code'),
                    'found_member_id': form.cleaned_data['found_member'].id if 'found_member' in form.cleaned_data else None,
                    'verification_method': form.cleaned_data['verification_method'],
                }
                
                # Generate verification code and store in session
                import random
                verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                registration_data['verification_code'] = verification_code
                registration_data['code_timestamp'] = timezone.now().isoformat()
                registration_data['code_used'] = False  # Track if code has been used
                
                request.session['pending_registration'] = registration_data
                request.session['resend_count'] = 0
                
                # Send verification code based on chosen method
                verification_method = form.cleaned_data['verification_method']
                phone = str(form.cleaned_data['phone'])
                full_name = f"{form.cleaned_data['firstname']} {form.cleaned_data['lastname']}"
                
                success = False
                if verification_method == 'email':
                    success = send_verification_email_direct(email, full_name, verification_code)
                    if success:
                        messages.success(request, "Verification code sent to your email!")
                    else:
                        messages.warning(request, "Email sending failed. Please try resending or contact admin.")
                        
                elif verification_method == 'sms':
                    success = send_verification_sms_direct(phone, verification_code)
                    if success:
                        messages.success(request, "Verification code sent to your phone via SMS!")
                    else:
                        messages.warning(request, "SMS sending failed. Please try resending or contact admin.")
                        
                else:  # both
                    email_sent = send_verification_email_direct(email, full_name, verification_code)
                    sms_sent = send_verification_sms_direct(phone, verification_code)
                    success = email_sent or sms_sent
                    if success:
                        messages.success(request, "Verification code sent to your email and phone!")
                    else:
                        messages.warning(request, "Verification sending failed. Please try resending or contact admin.")
                
                # Redirect to new verification page (no member_id needed - using session)
                return redirect('portal_verify_session')
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Registration error: {e}")
                messages.error(request, f"Registration failed: {str(e)}")
                return render(request, 'portal/register.html', {'form': form})
    else:
        # Clear any pending registration on fresh load
        if 'pending_registration' in request.session:
            del request.session['pending_registration']
        form = ChurchMemberRegistrationForm()
    
    return render(request, 'portal/register.html', {'form': form})


def portal_verify(request, member_id):
    """Handle verification code entry"""
    church_member = get_object_or_404(ChurchMember, id=member_id)
    
    if church_member.is_portal_active:
        messages.info(request, "Your account is already verified. Please login.")
        return redirect('portal_login')
    
    if request.method == 'POST':
        form = ChurchMemberVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            success, message = church_member.verify_code(code)
            
            if success:
                messages.success(request, f"{message} You can now login.")
                return redirect('portal_login')
            else:
                messages.error(request, message)
    else:
        form = ChurchMemberVerificationForm()
    
    # Check if resend failed (stored in session)
    resend_failed = request.session.pop('resend_failed', False)
    resend_count = request.session.get('resend_count', 0)
    
    # Show admin contact if resend failed or too many attempts
    show_admin_contact = resend_failed or resend_count >= 2
    
    context = {
        'form': form,
        'church_member': church_member,
        'can_resend': True,
        'resend_failed': resend_failed,
        'resend_count': resend_count,
        'show_admin_contact': show_admin_contact,
        'admin_email': settings.CHURCH_ADMIN_EMAIL,
        'admin_phone': settings.CHURCH_ADMIN_PHONE,
    }
    return render(request, 'portal/verify.html', context)


def portal_resend_code(request, member_id):
    """Resend verification code with retry limit and admin contact info"""
    church_member = get_object_or_404(ChurchMember, id=member_id)
    
    if church_member.is_portal_active:
        messages.info(request, "Your account is already verified.")
        return redirect('portal_login')
    
    # Track resend attempts
    resend_key = f'resend_count_{member_id}'
    resend_count = request.session.get(resend_key, 0)
    
    # Limit resends to 3 attempts per session
    if resend_count >= 3:
        messages.error(
            request, 
            "Maximum resend attempts reached. Please contact the church administrator for assistance."
        )
        request.session['resend_failed'] = True
        return redirect('portal_verify', member_id=member_id)
    
    # Resend based on previous method
    success = False
    try:
        if church_member.verification_method == 'email':
            success = church_member.send_verification_email()
            msg = "email" if success else "Failed to send email"
        elif church_member.verification_method == 'sms':
            success = church_member.send_verification_sms()
            msg = "phone" if success else "Failed to send SMS"
        else:
            success = church_member.send_verification_both()
            msg = "email and phone" if success else "Failed to send"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Resend code error: {e}")
        success = False
        msg = "System error occurred"
    
    if success:
        request.session[resend_key] = resend_count + 1
        request.session['resend_count'] = resend_count + 1
        messages.success(request, f"New verification code sent to your {msg}!")
    else:
        request.session['resend_failed'] = True
        messages.error(
            request, 
            f"{msg}. Please contact our church administrator: {settings.CHURCH_ADMIN_EMAIL} or {settings.CHURCH_ADMIN_PHONE}"
        )
    
    return redirect('portal_verify', member_id=member_id)


def portal_login(request):
    """Redirect to unified login page for church members"""
    if request.user.is_authenticated:
        # Only redirect to portal if user has a church_member profile
        if hasattr(request.user, 'church_member'):
            return redirect('portal_dashboard')
        # Otherwise, redirect to staff login
        return redirect('login_user')
    return redirect('login_user')


def portal_logout(request):
    """Handle church member logout using Django auth"""
    auth_logout(request)
    request.session.flush()
    return redirect('login_user')


# Import decorators from decorators module
from users.decorators import portal_login_required, staff_required


def rate_limit_login(request, max_attempts=5, window=300):
    """Rate limiting for login attempts - prevents brute force attacks"""
    ip = request.META.get('REMOTE_ADDR', '')
    key = f"login_attempts_{ip}"
    
    attempts = request.session.get(key, {'count': 0, 'first_attempt': None})
    
    # Check if window has expired
    if attempts['first_attempt']:
        from django.utils import timezone
        import datetime
        first = datetime.datetime.fromisoformat(attempts['first_attempt'])
        if (timezone.now() - first).total_seconds() > window:
            attempts = {'count': 0, 'first_attempt': None}
    
    if attempts['count'] >= max_attempts:
        return False, f"Too many login attempts. Please try again in {window//60} minutes."
    
    # Increment counter
    if not attempts['first_attempt']:
        from django.utils import timezone
        attempts['first_attempt'] = timezone.now().isoformat()
    attempts['count'] += 1
    request.session[key] = attempts
    
    return True, None


@portal_login_required
def portal_dashboard(request):
    """Main dashboard for church members"""
    church_member = request.church_member
    member = church_member.member
    
    context = {
        'church_member': church_member,
        'member': member,
    }
    
    if member:
        # Fetch member's data
        context.update({
            # Community
            'community': member.shepherd,
            'community_members': Member.objects.filter(
                shepherd=member.shepherd,
                active=True
            ).exclude(id=member.id)[:10] if member.shepherd else None,
            
            # Ministry
            'ministry': member.ministry,
            'ministry_events': Event.objects.filter(
                ministries=member.ministry,
                start_date__gte=timezone.now().date(),
                status='PUBLISHED'
            ).order_by('start_date')[:5] if member.ministry else None,
            
            # Committees
            'committees': Committee.objects.filter(member=member),
            
            # Sacraments
            'sacraments': MemberSacrament.objects.filter(
                member=member,
                verification_status='verified'
            ),
            
            # Tithe history (last 12 months)
            'tithe_payments': TithePayment.objects.filter(
                name=member
            ).order_by('-date')[:12],
            
            'total_tithe_this_year': TithePayment.objects.filter(
                name=member,
                date__year=timezone.now().year
            ).aggregate(total=Sum('amount'))['total'] or 0,
            
            # Pledges
            'pledges': EventPledge.objects.filter(
                member=member
            ).select_related('event').order_by('-created_at')[:5],
            
            # Upcoming events
            'upcoming_events': Event.objects.filter(
                start_date__gte=timezone.now().date(),
                status='PUBLISHED',
                is_public=True
            ).order_by('start_date')[:10],
            
            # Event registrations
            'my_event_registrations': EventRegistration.objects.filter(
                user__isnull=True,  # Registered by this portal user
                event__start_date__gte=timezone.now().date()
            ).order_by('event__start_date')[:5],
        })
    else:
        # Unlinked member - limited data
        context.update({
            'upcoming_events': Event.objects.filter(
                start_date__gte=timezone.now().date(),
                status='PUBLISHED',
                is_public=True
            ).order_by('start_date')[:10],
        })
    
    # Church statistics (for all members)
    current_year = timezone.now().year
    
    # Prepare tithe chart data if member exists
    
    tithe_chart_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    tithe_chart_data = [0] * 12
    
    if member:
        monthly_tithes = TithePayment.objects.filter(
            name=member,
            date__year=current_year
        ).values('date__month').annotate(total=Sum('amount'))
        
        for mt in monthly_tithes:
            month_index = mt['date__month'] - 1  # Convert to 0-based index
            if 0 <= month_index < 12:
                tithe_chart_data[month_index] = float(mt['total'])
    
    context.update({
        'total_members': Member.objects.filter(active=True).count(),
        'total_communities': Community.objects.count(),
        'total_ministries': Ministry.objects.count(),
        'total_committees': Committee.objects.count(),
        'tithe_payers': Member.objects.filter(pays_tithe=True, active=True).count(),
        'current_year': current_year,
        'tithe_chart_labels': tithe_chart_labels,
        'tithe_chart_data': tithe_chart_data,
    })
    
    return render(request, 'portal/dashboard.html', context)


class TitheChartJSONView(LoginRequiredMixin, BaseLineChartView):
    """AJAX endpoint for tithe chart data using django-chartjs"""
    
    def get_labels(self):
        """Return month labels for x-axis"""
        return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    def get_providers(self):
        """Return dataset names"""
        return ['Monthly Tithes']
    
    def get_data(self):
        """Return tithe data for the current member"""
        from django.utils import timezone
        from member.models import Member
        
        current_year = timezone.now().year
        data = [0] * 12
        
        # Get church member from request
        if hasattr(self.request, 'church_member'):
            church_member = self.request.church_member
            if church_member and church_member.member:
                member = church_member.member
                monthly_tithes = TithePayment.objects.filter(
                    name=member,
                    date__year=current_year
                ).values('date__month').annotate(total=Sum('amount'))
                
                for mt in monthly_tithes:
                    month_index = mt['date__month'] - 1
                    if 0 <= month_index < 12:
                        data[month_index] = float(mt['total'])
        
        return [data]


@portal_login_required
def portal_profile(request):
    """View and edit church member profile"""
    user = request.user
    church_member = request.church_member
    
    # Get or create ChurchMemberProfile for this user
    church_profile, created = ChurchMemberProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = ChurchMemberProfileForm(request.POST, request.FILES, instance=church_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('portal_profile')
    else:
        form = ChurchMemberProfileForm(instance=church_profile)
    
    return render(request, 'portal/profile.html', {
        'church_member': church_member,
        'form': form,
        'member': church_member.member,
    })


@portal_login_required
def portal_password_change(request):
    """Change password for church members"""
    user = request.user
    
    if request.method == 'POST':
        form = ChurchMemberPasswordChangeForm(user, request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password changed successfully! Please login again.")
            return redirect('portal_logout')
    else:
        form = ChurchMemberPasswordChangeForm(user)
    
    return render(request, 'portal/password_change.html', {
        'form': form,
        'church_member': request.church_member,
    })


@portal_login_required
def portal_events(request):
    """View church events calendar"""
    church_member = request.church_member
    
    events = Event.objects.filter(
        status='PUBLISHED',
        is_public=True
    ).order_by('start_date')
    
    # Filter by month if provided
    month = request.GET.get('month')
    if month:
        events = events.filter(start_date__month=month)
    
    return render(request, 'portal/events.html', {
        'events': events,
        'church_member': church_member,
    })


@portal_login_required
def portal_event_detail(request, event_id):
    """View event details and register"""
    church_member = request.church_member
    event = get_object_or_404(Event, id=event_id, is_public=True)
    
    # Check if already registered
    is_registered = EventRegistration.objects.filter(
        event=event,
        email=church_member.email
    ).exists()
    
    return render(request, 'portal/event_detail.html', {
        'event': event,
        'church_member': church_member,
        'is_registered': is_registered,
    })


@portal_login_required
def portal_tithe_history(request):
    """View tithe payment history"""
    church_member = request.church_member
    member = church_member.member
    
    if not member:
        messages.info(request, "Your account is not linked to a member record. Please contact admin.")
        return redirect('portal_dashboard')
    
    tithe_payments = TithePayment.objects.filter(
        name=member
    ).order_by('-date')
    
    # Calculate yearly totals
    current_year = timezone.now().year
    yearly_totals = {}
    for year in range(current_year-4, current_year+1):
        total = TithePayment.objects.filter(
            name=member,
            date__year=year
        ).aggregate(total=Sum('amount'))['total'] or 0
        yearly_totals[year] = total
    
    return render(request, 'portal/tithe_history.html', {
        'tithe_payments': tithe_payments,
        'yearly_totals': yearly_totals,
        'church_member': church_member,
        'member': member,
    })


@portal_login_required
def portal_pledges(request):
    """View pledge history and status"""
    church_member = request.church_member
    member = church_member.member
    
    if not member:
        messages.info(request, "Your account is not linked to a member record.")
        return redirect('portal_dashboard')
    
    pledges = EventPledge.objects.filter(
        member=member
    ).select_related('event').order_by('-created_at')
    
    # Calculate totals
    total_promised = sum(p.promised_amount for p in pledges)
    total_paid = sum(p.paid_amount for p in pledges)
    total_remaining = total_promised - total_paid
    
    return render(request, 'portal/pledges.html', {
        'pledges': pledges,
        'total_promised': total_promised,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'church_member': church_member,
    })


@portal_login_required
def portal_community(request):
    """View community information"""
    church_member = request.church_member
    member = church_member.member
    
    if not member or not member.shepherd:
        messages.info(request, "Community information not available.")
        return redirect('portal_dashboard')
    
    community = member.shepherd
    community_members = Member.objects.filter(
        shepherd=community,
        active=True
    ).exclude(id=member.id)
    
    community_leaders = community.leaders.all()
    
    return render(request, 'portal/community.html', {
        'community': community,
        'community_members': community_members,
        'community_leaders': community_leaders,
        'church_member': church_member,
        'member': member,
    })


@portal_login_required
def portal_ministry(request):
    """View ministry information"""
    church_member = request.church_member
    member = church_member.member
    
    if not member or not member.ministry:
        messages.info(request, "You are not assigned to any ministry.")
        return redirect('portal_dashboard')
    
    ministry = member.ministry
    ministry_events = Event.objects.filter(
        ministries=ministry,
        start_date__gte=timezone.now().date()
    ).order_by('start_date')
    
    ministry_leaders = ministry.leaders.filter(is_active=True)
    
    return render(request, 'portal/ministry.html', {
        'ministry': ministry,
        'ministry_events': ministry_events,
        'ministry_leaders': ministry_leaders,
        'church_member': church_member,
        'member': member,
    })


@portal_login_required
def portal_sacraments(request):
    """View sacrament records and request new ones"""
    church_member = request.church_member
    member = church_member.member
    
    if not member:
        messages.info(request, "Your account is not linked to a member record.")
        return redirect('portal_dashboard')
    
    sacraments = MemberSacrament.objects.filter(
        member=member
    ).order_by('-date_received')
    
    return render(request, 'portal/sacraments.html', {
        'sacraments': sacraments,
        'church_member': church_member,
        'member': member,
    })


# ============================================================================
# CHURCH MEMBER ACCOUNT MANAGEMENT VIEWS (For Staff)
# ============================================================================

@staff_required
def church_member_management(request):
    """Staff view to manage church member portal accounts"""
    # Get filter status from query params
    filter_status = request.GET.get('status', 'pending')
    search_query = request.GET.get('q', '')
    
    # Base queryset
    queryset = ChurchMember.objects.select_related('user', 'member').all()
    
    # Apply filters
    if filter_status == 'pending':
        queryset = queryset.filter(is_portal_active=False)
    elif filter_status == 'approved':
        queryset = queryset.filter(is_portal_active=True)
    elif filter_status == 'unlinked':
        queryset = queryset.filter(link_status='unlinked')
    # 'all' shows everything
    
    # Apply search
    if search_query:
        queryset = queryset.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__firstname__icontains=search_query) |
            Q(user__lastname__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(member_code__icontains=search_query)
        )
    
    # Order by most recent first
    church_members = queryset.order_by('-created_at')
    
    # Pagination - 20 items per page
    from django.core.paginator import Paginator
    paginator = Paginator(church_members, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get counts
    pending_count = ChurchMember.objects.filter(is_portal_active=False).count()
    approved_count = ChurchMember.objects.filter(is_portal_active=True).count()
    total_count = ChurchMember.objects.count()
    blocked_count = ChurchMember.objects.filter(user__is_active=False).count()
    unlinked_count = ChurchMember.objects.filter(link_status='unlinked').count()
    
    context = {
        'page_obj': page_obj,
        'church_members': page_obj,
        'filter_status': filter_status,
        'search_query': search_query,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'total_count': total_count,
        'blocked_count': blocked_count,
        'unlinked_count': unlinked_count,
    }
    
    return render(request, 'users/church_member_management.html', context)


@staff_required
def church_member_approve(request, member_id):
    """Approve a church member portal account"""
    if request.method == 'POST':
        church_member = get_object_or_404(ChurchMember, id=member_id)
        church_member.is_portal_active = True
        church_member.link_status = 'linked' if church_member.member else 'unlinked'
        church_member.save()
        
        # Also activate the User account
        church_member.user.is_active = True
        church_member.user.save()
        
        messages.success(request, f"Account for {church_member.get_full_name()} has been approved.")
    
    return redirect('church_member_management')


@staff_required
def church_member_block(request, member_id):
    """Block a church member portal account"""
    if request.method == 'POST':
        church_member = get_object_or_404(ChurchMember, id=member_id)
        church_member.is_portal_active = False
        church_member.save()
        
        # Deactivate the User account
        church_member.user.is_active = False
        church_member.user.save()
        
        messages.warning(request, f"Account for {church_member.get_full_name()} has been blocked.")
    
    return redirect('church_member_management')


@staff_required
def church_member_delete(request, member_id):
    """Delete a church member portal account"""
    if request.method == 'POST':
        church_member = get_object_or_404(ChurchMember, id=member_id)
        user = church_member.user
        name = church_member.get_full_name()
        
        # Delete ChurchMember (and profile if exists)
        church_member.delete()
        
        # Delete the User account too
        user.delete()
        
        messages.success(request, f"Account for {name} has been deleted.")
    
    return redirect('church_member_management')


# =============================================================================
# SESSION-BASED VERIFICATION VIEWS (User created only AFTER verification)
# =============================================================================

def send_verification_email_direct(email, full_name, code):
    """Send verification email using Brevo API (more reliable than SMTP)"""
    import logging
    from utils.brevo_email import send_verification_email_brevo

    logger = logging.getLogger(__name__)

    logger.info(f"Sending verification email to {email} via Brevo API")

    try:
        success = send_verification_email_brevo(email, full_name, code)
        if success:
            logger.info(f"Verification email sent successfully to {email}")
        else:
            logger.error(f"Failed to send verification email to {email}")
        return success
    except Exception as e:
        logger.error(f"Brevo API email failed to {email}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def send_verification_sms_direct(phone, code):
    """Send verification SMS directly without ChurchMember model"""
    try:
        from tithe.sms_api.africastalking import SMS
        message = f"Christ The King Parish verification code: {code}. Valid for 30 minutes."
        
        # Format phone number
        if hasattr(phone, 'as_e164'):
            phone = phone.as_e164
        
        SMS.send_sms(str(phone), message)
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Direct SMS send failed: {e}")
        return False


def portal_verify_session(request):
    """Handle verification using session-stored registration data"""
    # Check if we have pending registration
    pending = request.session.get('pending_registration')
    if not pending:
        messages.error(request, "No pending registration found. Please register again.")
        return redirect('portal_register')
    
    # Check if code was already used
    if pending.get('code_used', False):
        messages.error(request, "This verification code has already been used. Please register again.")
        del request.session['pending_registration']
        if 'resend_count' in request.session:
            del request.session['resend_count']
        return redirect('portal_register')
    
    # Check if code expired (30 minutes)
    from datetime import datetime, timedelta
    code_time = datetime.fromisoformat(pending.get('code_timestamp', ''))
    if timezone.now() - code_time > timedelta(minutes=30):
        del request.session['pending_registration']
        messages.error(request, "Verification code expired. Please register again.")
        return redirect('portal_register')
    
    if request.method == 'POST':
        entered_code = request.POST.get('code', '').strip().replace(' ', '')

        # Debug logging (remove in production)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Verification attempt - Entered: '{entered_code}', Stored: '{pending.get('verification_code')}'")

        # Check if code matches and hasn't been used
        if entered_code == pending.get('verification_code') and not pending.get('code_used', False):
            # Mark code as used BEFORE creating user (prevents race conditions)
            pending['code_used'] = True
            request.session['pending_registration'] = pending
            
            # Code verified! Now create the user
            try:
                # Create User
                user = User.objects.create_user(
                    username=pending['username'],
                    email=pending['email'],
                    password=pending['password'],
                    firstname=pending['firstname'],
                    lastname=pending['lastname'],
                    phone=pending['phone']
                )
                user.is_active = True  # Verified!
                user.save()
                
                # Create ChurchMember extension
                church_member = ChurchMember.objects.create(
                    user=user,
                    phone=pending['phone'],
                    member_code=pending.get('member_code'),
                    link_status='unlinked',
                    is_portal_active=True  # Verified!
                )
                
                # Link to member if applicable
                if pending.get('found_member_id'):
                    try:
                        member = Member.objects.get(id=pending['found_member_id'])
                        church_member.member = member
                        church_member.member_code = member.code
                        church_member.link_status = 'linked'
                        church_member.save()
                    except Member.DoesNotExist:
                        pass
                
                # Create profile
                ChurchMemberProfile.objects.create(user=user)
                
                # Clean up session
                del request.session['pending_registration']
                if 'resend_count' in request.session:
                    del request.session['resend_count']
                
                messages.success(request, "Account verified successfully! You can now login.")
                return redirect('portal_login')
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"User creation after verification failed: {e}")
                messages.error(request, "Account creation failed. Please try again or contact admin.")
        else:
            messages.error(request, "Invalid verification code. Please try again.")
    
    # Get resend status
    resend_count = request.session.get('resend_count', 0)
    show_admin_contact = resend_count >= 2
    
    context = {
        'verification_method': pending.get('verification_method', 'email'),
        'email': pending.get('email'),
        'phone': pending.get('phone'),
        'can_resend': True,
        'resend_count': resend_count,
        'show_admin_contact': show_admin_contact,
        'admin_email': settings.CHURCH_ADMIN_EMAIL,
        'admin_phone': settings.CHURCH_ADMIN_PHONE,
    }
    return render(request, 'portal/verify_session.html', context)


def portal_resend_code_session(request):
    """Resend verification code using session data - generates NEW code each time"""
    import random
        
    pending = request.session.get('pending_registration')
    if not pending:
        messages.error(request, "No pending registration found.")
        return redirect('portal_register')
    
    # Track resend attempts
    resend_count = request.session.get('resend_count', 0)
    if resend_count >= 3:
        messages.error(
            request,
            f"Maximum resend attempts reached. Please contact our administrator: {settings.CHURCH_ADMIN_EMAIL} or {settings.CHURCH_ADMIN_PHONE}"
        )
        return redirect('portal_verify_session')
    
    # Generate NEW verification code (invalidates old code)
    new_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    pending['verification_code'] = new_code
    pending['code_timestamp'] = timezone.now().isoformat()
    pending['code_used'] = False  # Mark as unused
    request.session['pending_registration'] = pending
    
    # Resend code
    verification_method = pending.get('verification_method', 'email')
    email = pending.get('email')
    phone = pending.get('phone')
    full_name = f"{pending.get('firstname', '')} {pending.get('lastname', '')}"
    code = new_code  # Use the new code
    
    success = False
    if verification_method == 'email':
        success = send_verification_email_direct(email, full_name, code)
        msg = "email" if success else "Failed to send email"
    elif verification_method == 'sms':
        success = send_verification_sms_direct(phone, code)
        msg = "phone" if success else "Failed to send SMS"
    else:
        email_sent = send_verification_email_direct(email, full_name, code)
        sms_sent = send_verification_sms_direct(phone, code)
        success = email_sent or sms_sent
        msg = "email and phone" if success else "Failed to send"
    
    if success:
        request.session['resend_count'] = resend_count + 1
        messages.success(request, f"New verification code sent to your {msg}!")
    else:
        request.session['resend_count'] = resend_count + 1
        messages.error(
            request,
            f"{msg}. Please contact our church administrator: {settings.CHURCH_ADMIN_EMAIL} or {settings.CHURCH_ADMIN_PHONE}"
        )
    
    return redirect('portal_verify_session')


@staff_required
def church_member_bulk_approve(request):
    """Bulk approve church member accounts"""
    if request.method == 'POST':
        ids = request.POST.get('ids', '')
        if ids:
            id_list = [int(id) for id in ids.split(',') if id.isdigit()]
            members = ChurchMember.objects.filter(id__in=id_list)
            count = members.count()
            
            for church_member in members:
                church_member.is_portal_active = True
                church_member.user.is_active = True
                church_member.save()
                church_member.user.save()
            
            messages.success(request, f"{count} account(s) have been approved.")
    
    return redirect('church_member_management')


@staff_required
def church_member_bulk_block(request):
    """Bulk block church member accounts"""
    if request.method == 'POST':
        ids = request.POST.get('ids', '')
        if ids:
            id_list = [int(id) for id in ids.split(',') if id.isdigit()]
            members = ChurchMember.objects.filter(id__in=id_list)
            count = members.count()
            
            for church_member in members:
                church_member.is_portal_active = False
                church_member.user.is_active = False
                church_member.save()
                church_member.user.save()
            
            messages.warning(request, f"{count} account(s) have been blocked.")
    
    return redirect('church_member_management')


@staff_required
def church_member_bulk_delete(request):
    """Bulk delete church member accounts"""
    if request.method == 'POST':
        ids = request.POST.get('ids', '')
        if ids:
            id_list = [int(id) for id in ids.split(',') if id.isdigit()]
            members = ChurchMember.objects.filter(id__in=id_list)
            count = members.count()
            
            for church_member in members:
                user = church_member.user
                church_member.delete()
                user.delete()
            
            messages.success(request, f"{count} account(s) have been deleted.")
    
    return redirect('church_member_management')


@staff_required
def church_member_manual_link(request, member_id):
    """Manually link a church member account to a Member record"""
    church_member = get_object_or_404(ChurchMember, id=member_id)
    
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        if member_id:
            try:
                member = Member.objects.get(id=member_id, active=True)
                church_member.member = member
                church_member.member_code = member.code
                church_member.link_status = 'linked'
                church_member.save()
                messages.success(request, f"Account linked to {member.name} successfully!")
                return redirect('church_member_management')
            except Member.DoesNotExist:
                messages.error(request, "Member not found.")
        else:
            messages.error(request, "Please select a member.")
    
    # Get all active members for dropdown
    members = Member.objects.filter(active=True).order_by('name')
    
    context = {
        'church_member': church_member,
        'members': members,
    }
    return render(request, 'users/church_member_manual_link.html', context)
