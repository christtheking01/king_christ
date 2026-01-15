from django.db import models
from django.contrib.auth.models import User,Group
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import json
from datetime import timedelta

from member.models import upload_image_path


class ManagerUser(BaseUserManager):
    def create_user(self, email=None, username=None, password=None, **extra_fields):
        if not email and not username:
            raise ValueError("Users must have an email address and username")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email=None, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if not email and not username:
            raise ValueError("Superuser must have an email address or username")
        
        return self.create_user(email=email, username=username, password=password, **extra_fields)
    
    def create_user_as_admin(self, admin_user, email=None, username=None, password= None, **extra_fields):
        """only allows adm/super to create users"""
        if not admin_user.is_authenticated:
            raise ValueError("Only admin/superuser can create users")
        if not(admin_user.is_staff or admin_user.is_superuser):
            raise ValueError("Only admin/superuser can create users")
        
        return self.create_user(email=email, username=username, password=password, **extra_fields)
        

class User(AbstractBaseUser, PermissionsMixin):
    roles =[
        ('admin','Admin'),
        ('Chairperson','Chairperson'),
        ('Secretary','Secretary'),
        ('Accountant','Accountant'),
        ('Member','Member'),
    ]
    username = models.CharField(max_length=255, blank=True, unique=True)
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    firstname = models.CharField(max_length=30, null=True, blank=True)
    lastname = models.CharField(max_length=30, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    roles = models.CharField(max_length=50, choices=roles, default='Member')
    date_joined = models.DateTimeField(default=timezone.now)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    phone = models.CharField(max_length=15, blank=True, null=True)
    force_password_change = models.BooleanField(default=True)
    objects = ManagerUser()

    USERNAME_FIELD = 'username' # primary identifier for django auth
    REQUIRED_FIELDS = []     # required when creating superuser

    def __str__(self):
       return self.username if self.username else self.email
    
    def clean(self):
        if not self.email and not self.username:
            raise ValueError("Both email and username must be provided.")
        return super().clean()
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def full_name(self):
        return f"{self.firstname} {self.lastname}".strip()
    
    def short_name(self):
        return self.firstname if self.firstname else self.email



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    telephone = models.PositiveIntegerField(blank=True, null=True)
    whatsapp_line = models.PositiveIntegerField(blank=True, null=True)
    facebook_link = models.CharField(max_length=255, blank=True, null=True)
    twitter_link = models.CharField(max_length=255, blank=True, null=True)
    instagram_link = models.CharField(max_length=255, blank=True, null=True)
    picture = models.ImageField(upload_to=upload_image_path, blank=True, null=True)

    def __str__(self):
        return self.user.username
