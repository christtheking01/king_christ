from django.utils import timezone
from enum import Enum
import os, random
from django.conf import settings
from django.core.exceptions import ValidationError
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone

from django.db import models


def filename_ext(filepath):
    file_base = os.path.basename(filepath)
    filename, ext = os.path.splitext(file_base)
    return filename, ext


def upload_image_path(instance, filename):
    new_filename = random.randint(1, 9498594795)
    name, ext = filename_ext(filename)
    final_filename = "{new_filename}{ext}".format(new_filename=new_filename, ext=ext)
    return "pictures/{new_filename}/{final_filename}".format(new_filename=new_filename, final_filename=final_filename)


class Ministry(models.Model):
    name = models.CharField(max_length=255, unique=True)
    feast_name = models.CharField(max_length=100, blank=True, null=True)
    feast_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        verbose_name_plural = "Ministries"
        ordering = ['name']


class MinistryLeader(models.Model):
    RANK_CHOICES = [
        ('CHAIR PERSON', 'Chair Person'),
        ('VICE CHAIR', 'Vice Chair'),
        ('SECRETARY', 'Secretary'),
        ('VICE SECRETARY', 'Vice Secretary'),
        ('ACCOUNTANT', 'Accountant'),
        ('COORDINATOR', 'Coordinator')
    ]
    
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, 
                                related_name='leaders')
    member = models.ForeignKey("Member", on_delete=models.CASCADE,
                                related_name='ministry_leaders',
                                null=True, blank=True,
                                help_text='Select a member to autopopulate details')
    leader_name = models.CharField(max_length=250)
    position = models.CharField(max_length=30, choices=RANK_CHOICES)
    community = models.ForeignKey("Community", verbose_name="Community", 
                                 on_delete=models.CASCADE, 
                                 related_name="ministry_leaders", 
                                 null=True, blank=True)
    phone = PhoneNumberField(max_length=255, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    appointed_date = models.DateField(null=True, blank=True)
    
    def clean(self):
        super().clean()
        if self.member:
            self.leader_name = self.member.name
            if self.member.telephone and not self.phone:
                self.phone = self.member.telephone
            if self.member.shepherd and not self.community:
                self.community = self.member.shepherd

    def __str__(self):
        community_name = self.community.name if self.community else "No Community"
        leader_name = self.member.name if self.member else self.leader_name
        return f"{leader_name} - {self.position} ({self.ministry.name}) - {community_name}"
    
    class Meta:
        unique_together = ['ministry', 'position']  # One position per ministry
        ordering = ['ministry', 'position']

class Community(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_members(self):
        """Return all members belonging to this community"""
        return Member.objects.filter(shepherd=self, active=True)

    def get_members_count(self):
        """Return count of active members in this community"""
        return Member.objects.filter(shepherd=self, active=True).count()

    def __str__(self):
        return self.name


class Zone(models.Model):
    name = models.CharField(max_length=255, unique=True)
    leader_name = models.CharField(max_length=250, blank=True, null=True)
    leader_phone = PhoneNumberField(max_length=255, blank=True, null=True)
    leader_email = models.EmailField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_communities(self):
        """Return all communities in this zone"""
        return Community.objects.filter(community_zones__zone=self)

    def get_communities_count(self):
        """Return count of communities in this zone"""
        return CommunityZone.objects.filter(zone=self).count()

    def get_total_members(self):
        """Return total members across all communities in this zone"""
        communities = self.get_communities()
        return Member.objects.filter(shepherd__in=communities, active=True).count()

    class Meta:
        verbose_name_plural = "Zones"
        ordering = ['name']


class CommunityZone(models.Model):
    """Links communities to zones (Many-to-Many with extra fields)"""
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='community_zones')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='community_zones')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['zone', 'community']
        verbose_name = "Community Zone Assignment"
        verbose_name_plural = "Community Zone Assignments"

    def __str__(self):
        return f"{self.community.name} → {self.zone.name}"


class ZoneLeader(models.Model):
    """Leaders for zones with positions (Chair, Vice Chair, etc.)"""
    POSITION_CHOICES = [
        ('CHAIRPERSON', 'Chairperson'),
        ('VICE CHAIR', 'Vice Chair'),
        ('SECRETARY', 'Secretary'),
        ('VICE SECRETARY', 'Vice Secretary'),
        ('ACCOUNTANT', 'Accountant'),
        ('COORDINATOR', 'Coordinator'),
        ('MEMBER', 'Member'),
    ]
    
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='leaders')
    name = models.CharField(max_length=250)
    position = models.CharField(max_length=30, choices=POSITION_CHOICES)
    phone = PhoneNumberField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    appointed_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['zone', 'position']  # One position per zone
        ordering = ['zone', 'position']
        verbose_name = "Zone Leader"
        verbose_name_plural = "Zone Leaders"
    
    def __str__(self):
        return f"{self.name} - {self.position} ({self.zone.name})"
    
    def save(self, *args, **kwargs):
        # Auto-create/update member record for this leader
        from django.db.models import Q
        
        # Get communities in this zone
        zone_communities = self.zone.get_communities()
        
        # Try to find existing member with same name in zone communities
        member = None
        for community in zone_communities:
            try:
                member = Member.objects.filter(
                    Q(name__iexact=self.name) | 
                    Q(name__icontains=self.name),
                    shepherd=community,
                    active=True
                ).first()
                if member:
                    break
            except:
                continue
        
        # Create member if not found
        if not member and zone_communities.exists():
            # Use first community as default
            first_community = zone_communities.first()
            member = Member.objects.create(
                name=self.name,
                shepherd=first_community,
                telephone=self.phone,
                active=True,
                location=self.zone.name
            )
        elif member:
            # Update member phone if changed
            if self.phone and not member.telephone:
                member.telephone = self.phone
                member.save(update_fields=['telephone'])
        
        super().save(*args, **kwargs)


class CommunityLeader(models.Model):
    RANK_CHOICES = [
        ('VICE CHAIR', 'Vice Chair'),
        ('SECRETARY', 'Secretary'),
        ('VICE SECRETARY', 'Vice Secretary'),
        ('ACCOUNTANT', 'Accountant'),
        ('CHAIRPERSON', 'Chairperson'),
    ]
    
    community_name = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='leaders', null=True)
    name = models.CharField(max_length=250, null=True)
    leader = models.CharField(max_length=250, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    feast_name = models.TextField(max_length=10, blank=True, null=True)
    feast_date = models.DateField(blank=True, null=True)
    phone = PhoneNumberField(max_length=255, blank=True, null=True)
    
    class Meta:
        unique_together = ['community_name', 'leader']  # One position per community
        ordering = ['community_name', 'leader']
        verbose_name = "Community Leader"
        verbose_name_plural = "Community Leaders"
    
    def __str__(self):
        return f"{self.leader} {self.feast_date} {self.feast_name} ({self.community_name.name})"


class Committee(models.Model):
    Position = [
        ('VICE CHAIR', 'Vice Chair'),
        ('SECRETARY', 'Secretary'),
        ('VICE SECRETARY', 'Vice Secretary'),
        ('ACCOUNTANT', 'Accountant'),
        ('CHAIRPERSON', 'Chairperson'),
        ('MEMBER','Member')
    ]

    Commitee_name = models.CharField(max_length=250, blank=False, null=True)
    position = models.CharField(max_length=50, choices=Position, null=True, blank=True)
    member = models.ForeignKey("Member", verbose_name="commitee_names", on_delete=models.CASCADE)
    description = models.CharField (max_length=50, help_text ='Write the Functions of your commitee ', blank=True, null=True)
    phone = PhoneNumberField(max_length=255, null=True, blank=True, help_text=' Eg. +255 ')

    def __str__(self):
        return f'{self.Commitee_name}'
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Ministry.objects.filter(name=name).exists():
            if not self.instance or self.instance.name != name:
                raise ("A ministry with this name already exists.")
        return name


class MemberManager(models.Manager):
    def get_by_id(self, id):
        qs = self.get_queryset().filter(id=id)
        if qs.count() == 1:
            return qs.first()
        return None

    def active(self):
        qs = self.get_queryset().filter(active=True)
        return qs

    def deleted(self):
        return self.get_queryset().filter(active=False)

    def by_gender(self, gender):
        return self.active().filter(gender=gender)

    def pays_tithe(self):
        # return self.get_queryset().filter(pays_tithe=True)
        return self.active().filter(pays_tithe=True)

    def working(self):
        # return self.get_queryset().filter(working=True)
        return self.active().filter(working=True)

    def schooling(self):
        # return self.get_queryset().filter(schooling=True)
        return self.active().filter(schooling=True)

    def elders(self):
        """Filter members who are elders"""
        return self.active().filter(membership_category='elder')

    def youth(self):
        """Filter members who are youth"""
        return self.active().filter(membership_category='youth')

    def children(self):
        """Filter members who are children"""
        return self.active().filter(membership_category='child')

    def by_membership_category(self, category):
        """Filter members by membership category (elder, youth, child)"""
        return self.active().filter(membership_category=category)


class Member(models.Model):
    MEMBERSHIP_CATEGORY_CHOICES = [
        ('elder', 'Elder'),
        ('youth', 'Youth'),
        ('child', 'Child'),
    ]
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, help_text="001PT", null=True, blank=True)
    active = models.BooleanField(default=True)
    shepherd = models.ForeignKey(Community, on_delete=models.CASCADE, null=True, blank=True, related_name='members')
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, null=True, blank=True, related_name='members')
    telephone = PhoneNumberField(max_length=255, null=True, blank=True, help_text=' Eg. +255 ')
    location = models.CharField(max_length=255, blank=True, null=True)
    fathers_name = models.CharField(max_length=255, null=True, blank=True)
    mothers_name = models.CharField(max_length=255, null=True, blank=True)
    guardians_name = models.CharField(max_length=255, null=True, blank=True)
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    pays_tithe = models.BooleanField(default=False)
    working = models.BooleanField(default=False)
    schooling = models.BooleanField(default=False)
    picture = models.ImageField(upload_to=upload_image_path, null=True, blank=True)
    transfered = models.BooleanField(default=False)
    transfer_update = models.CharField(max_length=250, null=True, blank=True)
    membership_category = models.CharField(max_length=10, choices=MEMBERSHIP_CATEGORY_CHOICES, null=True, blank=True, help_text="Distinguishes between Elders, Youth, and Children")

    objects = MemberManager()

    def __str__(self):
        return f'{self.name}'
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Members'

    @property
    def picture_url(self):
        if self.picture and hasattr(self.picture, 'url'):
            return self.picture.url
        return f"{settings.STATIC_URL}images/default-avatar.png"
    


class MemberSacrament(models.Model):
    """Track sacrament records for members/users with catechesis verification"""
    
    SACRAMENT_CHOICES = [
        ('baptism', 'Baptism'),
        ('confirmation', 'Confirmation'),
        ('eucharist', 'First Holy Communion'),
        ('reconciliation', 'Reconciliation'),
        ('marriage', 'Marriage'),
        ('holy_orders', 'Holy Orders'),
        ('anointing_sick', 'Anointing of the Sick'),
    ]
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('under_review', 'Under Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    # Link to Member (for member records) or directly to User
    member = models.ForeignKey(Member, on_delete=models.CASCADE, null=True, blank=True, related_name='sacraments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='sacrament_records')
    
    # Sacrament details
    sacrament_type = models.CharField(max_length=50, choices=SACRAMENT_CHOICES)
    date_received = models.DateField(null=True, blank=True, help_text="Date when sacrament was received")
    place_received = models.CharField(max_length=255, blank=True, null=True, help_text="Parish/Church where sacrament was received")
    minister_name = models.CharField(max_length=255, blank=True, null=True, help_text="Priest/Deacon who administered the sacrament")
    
    # Verification fields
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_sacraments'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, null=True, help_text="Notes from catechesis verification")
    
    # Documents
    certificate_file = models.FileField(upload_to='sacrament_certificates/', null=True, blank=True)
    supporting_document = models.FileField(upload_to='sacrament_documents/', null=True, blank=True)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_sacraments'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Member Sacrament"
        verbose_name_plural = "Member Sacraments"
        unique_together = ['member', 'user', 'sacrament_type']
    
    def __str__(self):
        person = self.member.name if self.member else (self.user.get_full_name() or self.user.username)
        return f"{person} - {self.get_sacrament_type_display()} ({self.get_verification_status_display()})"
    
    def is_verified(self):
        return self.verification_status == 'verified'
    
    def is_pending(self):
        return self.verification_status == 'pending'
    
    def can_verify(self, user):
        """Check if given user can verify this sacrament"""
        from users.models import User
        if isinstance(user, User):
            return user.is_approver()
        return False
    
    def verify(self, verified_by, notes=""):
        """Mark sacrament as verified by catechesis staff"""
        self.verification_status = 'verified'
        self.verified_by = verified_by
        self.verification_date = timezone.now()
        self.verification_notes = notes
        self.save()
    
    def reject(self, rejected_by, reason=""):
        """Reject sacrament verification"""
        from django.utils import timezone
        self.verification_status = 'rejected'
        self.verified_by = rejected_by
        self.verification_date = timezone.now()
        self.verification_notes = reason
        self.save()


class TestDb(models.Model):
    field = models.CharField(max_length=120)