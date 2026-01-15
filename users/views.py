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
from django.views.generic import CreateView, ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import PasswordChangeView
from .forms import AdminUserCreationForm, AdminUserEditForm, FirstTimePasswordChangeForm, UserForm, SignupForm
from .models import UserProfile,User

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
    


def user_profile(request):
    # SLTGhana = 030 223 1886
    template = "registration/user_profile.html"
    profile = UserProfile.objects.get_or_create(user=request.user)
    try:
        shepherd = CommunityLeader.objects.get(name=request.user.username)
        members = CommunityLeader.member_set.active()
        # import pdb; pdb.set_trace()
    except:
        shepherd = None
        members = None
    # import pdb; pdb.set_trace()
    context = {"profile": profile, "members": members, "shepherd": shepherd}
    return render(request, template, context)

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
            messages.success(request, f'User {user.username} created successfully! They will be required to change their password on first login.')
            return redirect('list_users')
    else:
        form = AdminUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})


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
