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
        
        if not username:
            raise ValueError("Superuser must have a username")
        
        if not email:
            raise ValueError("Superuser must have an email address")
        
        if not password:
            raise ValueError("Superuser must have a password")
        
        return self.create_user(email=email, username=username, password=password, **extra_fields)
    
    def create_user_as_admin(self, admin_user, email=None, username=None, password= None, **extra_fields):
        """only allows adm/super to create users"""
        if not admin_user.is_authenticated:
            raise ValueError("Only admin/superuser can create users")
        if not(admin_user.is_staff or admin_user.is_superuser):
            raise ValueError("Only admin/superuser can create users")
        
        return self.create_user(email=email, username=username, password=password, **extra_fields)
        

class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('chairperson', 'Chairperson'),
        ('vice_chairperson', 'Vice Chairperson'),
        ('secretary', 'Secretary'),
        ('accountant', 'Accountant'),
        ('treasurer', 'Treasurer'),
        ('member', 'Member'),
        ('active_member', 'Active Member'),
        ('priest', 'Priest'),
        ('catechist', 'Catechist'),
        ('coordinator', 'Coordinator'),
        ('liturgical', 'Liturgical'),
        ('evangelization', 'Evangelization'),
        ('youth', 'Youth'),
        ('choir', 'Choir'),
        ('reader', 'Reader'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sw', 'Swahili'),
    ]

    APPROVER_ROLES = ('admin', 'priest', 'chairperson', 'secretary', 'catechist')

    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    firstname = models.CharField(max_length=30, null=True, blank=True)
    lastname = models.CharField(max_length=30, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    roles = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en',
                                          help_text="User's preferred language for the interface")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    force_password_change = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    pos_pin = models.CharField(max_length=4, blank=True, null=True, help_text="4-digit PIN for POS access")

    objects = ManagerUser()

    USERNAME_FIELD = 'username' # primary identifier for django auth
    REQUIRED_FIELDS = ['email']     # required when creating superuser

    def __str__(self):
       return self.username if self.username else self.email
    
    def clean(self):
        if not self.email and not self.username:
            raise ValueError("Both email and username must be provided.")
        return super().clean()
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.firstname} {self.lastname}".strip()
    
    def short_name(self):
        return self.firstname if self.firstname else self.email
    
    def has_role(self, role):
        return self.roles == role
    
    def is_approver(self):
        """Check if user can approve sacrament requests"""
        return self.roles in self.APPROVER_ROLES or self.is_superuser or self.is_staff
    
    def can_approve_sacrament(self, sacrament_name):
        """Check if user can approve a specific sacrament type"""
        # Must be an approver first
        if not self.is_approver():
            return False
        
        # Catechists cannot approve Marriage or Holy Orders
        if self.roles == 'catechist' and sacrament_name in ['marriage', 'holy_orders']:
            return False
        
        return True



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


class family(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def head_family(self):
        membership = self.membership_set_filter(role = "head").select_related("user").first()
        return membership.user if membership else None

    def member_count(self):
        return self.membership_set.count()
    
    class Meta:
        verbose_name = "Family"
        verbose_name_plural = "Families"

class FamilyMembership(models.Model):
    ROLE_CHOICES = [
        ('head', 'Head'),
        ('member', 'Member'),
    ]
    user = models.OneToOneField(  # one user can only belong to one family
        User,
        on_delete=models.CASCADE,
        related_name='family_membership'
    )
    family = models.ForeignKey(
        family,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.family.name} ({self.role})"

    def is_head(self):
        return self.role == 'head'

    class Meta:
        verbose_name_plural = "Family Memberships"


class ChurchMember(models.Model):
    """Portal extension for church members - links to User model via OneToOneField"""
    
    LINK_STATUS_CHOICES = [
        ('unlinked', 'Unlinked - Admin Approval Required'),
        ('pending_verification', 'Pending Code Verification'),
        ('linked', 'Linked - Active'),
        ('rejected', 'Rejected'),
    ]
    
    VERIFICATION_METHOD_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('both', 'Both Email & SMS'),
    ]
    
    # Link to the main User auth model
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='church_member',
        help_text="The User account this portal profile belongs to"
    )
    
    # Phone number for verification (may differ from User.phone)
    phone = models.CharField(max_length=15, help_text="Phone for SMS verification")
    
    # Member linking to church Member record
    member_code = models.CharField(max_length=50, blank=True, null=True, 
                                    help_text="Enter your member code if you have one")
    member = models.OneToOneField(
        'member.Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='portal_account'
    )
    
    # Portal status fields
    link_status = models.CharField(
        max_length=20,
        choices=LINK_STATUS_CHOICES,
        default='unlinked'
    )
    is_portal_active = models.BooleanField(default=False, 
                                           help_text="Portal access activated after verification")
    
    # Verification fields
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    verification_method = models.CharField(
        max_length=10,
        choices=VERIFICATION_METHOD_CHOICES,
        default='email'
    )
    code_attempts = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Church Member Portal Profile"
        verbose_name_plural = "Church Member Portal Profiles"
    
    def __str__(self):
        return f"Portal: {self.user.username} ({self.user.email})"
    
    def get_full_name(self):
        """Get full name from User or linked Member"""
        if self.user.firstname and self.user.lastname:
            return f"{self.user.firstname} {self.user.lastname}"
        if self.member:
            return self.member.name
        return self.user.username
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def username(self):
        return self.user.username
    
    @property
    def is_verified(self):
        return self.is_portal_active
    
    @property
    def date_joined(self):
        return self.created_at
    
    @property
    def last_login(self):
        return self.user.last_login
    
    def generate_verification_code(self):
        """Generate a 6-digit verification code"""
        import random
        code = str(random.randint(100000, 999999))
        self.verification_code = code
        self.verification_sent_at = timezone.now()
        self.code_attempts = 0
        self.save(update_fields=['verification_code', 'verification_sent_at', 'code_attempts'])
        return code
    
    def verify_code(self, code):
        """Verify the entered code and activate portal access"""
        # Clean the entered code - remove whitespace
        code = str(code).strip().replace(' ', '') if code else ''

        if not self.verification_code:
            return False, "No verification code sent"

        # Check if code expired (30 minutes)
        if self.verification_sent_at:
            if timezone.now() > self.verification_sent_at + timedelta(minutes=30):
                return False, "Verification code expired"

        # Check attempts
        if self.code_attempts >= 5:
            return False, "Too many attempts. Request new code."

        self.code_attempts += 1
        self.save(update_fields=['code_attempts'])

        stored_code = str(self.verification_code).strip()
        if stored_code == code:
            # Success - activate portal access
            self.is_portal_active = True
            self.link_status = 'linked' if self.member else 'unlinked'
            self.verification_code = None
            self.save(update_fields=['is_portal_active', 'link_status', 'verification_code'])
            
            # Also activate the User account
            if not self.user.is_active:
                self.user.is_active = True
                self.user.save(update_fields=['is_active'])
            
            return True, "Verification successful"
        
        return False, "Invalid verification code"
    
    def link_to_member(self, member):
        """Link this portal account to a Member record"""
        self.member = member
        self.member_code = member.code
        self.link_status = 'linked'
        self.save(update_fields=['member', 'member_code', 'link_status'])
    
    def send_verification_email(self):
        """Send verification code via email - optimized with timeout"""
        import socket
        # Set socket timeout for faster failures (5 seconds)
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5)
        
        code = self.generate_verification_code()
        self.verification_method = 'email'
        self.save(update_fields=['verification_method'])
        
        subject = 'Christ King Church - Verification Code'
        message = f"""
        Hello {self.get_full_name()},
        
        Your verification code for Christ King Church Member Portal is: {code}
        
        This code will expire in 30 minutes.
        
        If you did not request this code, please ignore this email.
        
        God bless you,
        Christ King Church
        """
        
        try:
            # Use fail_silently=True to prevent blocking on SMTP errors
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL or 'noreply@christkingchurch.org',
                [self.user.email],
                fail_silently=True,  # Changed to True for faster response
            )
            # Log success for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Verification email sent to {self.user.email}")
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Email sending failed: {e}")
            return False
        finally:
            # Restore original timeout
            socket.setdefaulttimeout(original_timeout)
    
    def send_verification_sms(self):
        """Send verification code via SMS"""
        code = self.generate_verification_code()
        self.verification_method = 'sms'
        self.save(update_fields=['verification_method'])
        
        try:
            # Using existing Africa's Talking integration
            from tithe.sms_api.africastalking import SMS
            message = f"Christ King Church verification code: {code}. Valid for 30 minutes."
            
            # Format phone number
            phone = self.phone
            if hasattr(phone, 'as_e164'):
                phone = phone.as_e164
            
            SMS.send_sms(str(phone), message)
            return True
        except Exception as e:
            print(f"SMS sending failed: {e}")
            return False
    
    def send_verification_both(self):
        """Send verification code via both email and SMS"""
        code = self.generate_verification_code()
        self.verification_method = 'both'
        self.save(update_fields=['verification_method'])
        
        email_sent = self.send_verification_email()
        sms_sent = self.send_verification_sms()
        
        return email_sent or sms_sent  # Return True if at least one succeeded


class ChurchMemberProfile(models.Model):
    """Extended profile information for church member portal users"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='church_profile'
    )
    
    # Address
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Emergency contact
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Preferences
    receive_email_notifications = models.BooleanField(default=True)
    receive_sms_notifications = models.BooleanField(default=True)
    
    # Profile picture (portal-specific)
    profile_picture = models.ImageField(
        upload_to=upload_image_path,
        blank=True,
        null=True
    )
    
    # Bio
    bio = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Church Member Profile"
        verbose_name_plural = "Church Member Profiles"
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    @property
    def church_member(self):
        """Convenience accessor to get the ChurchMember"""
        return getattr(self.user, 'church_member', None)

