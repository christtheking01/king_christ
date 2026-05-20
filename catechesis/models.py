from dataclasses import fields
from enum import unique
from django.db import models
from django.forms import ValidationError
from users.models import User 
from django.conf import settings
from finance.base_models import AuditableModelWithManager
from django.utils import timezone

# Create your models here
class CatechesisMember(AuditableModelWithManager):
    MEMBER_CATEGORY_CHOICES = [
        ('child', 'Child (0-12)'),
        ('teen', 'Teen (13-17)'),
        ('adult', 'Adult (18+)'),
        ('rcia', 'RCIA (Rite of Christian Initiation)'),
        ('special_needs', 'Special Needs'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    RELIGION_CHOICES = [
        ('catholic', 'Catholic'),
        ('christian', 'Christian (Other)'),
        ('other', 'Other'),
        ('none', 'None'),
    ]
    
    # Basic Information
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    member_category = models.CharField(max_length=20, choices=MEMBER_CATEGORY_CHOICES, default='adult')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField()
    place_of_birth = models.CharField(max_length=200, blank=True, null=True, help_text="City/Country of birth for sacrament records")
    nationality = models.CharField(max_length=100, blank=True, null=True)
    
    # Contact Information
    email = models.EmailField(blank=True, null=True, help_text="Member's email (optional for children)")
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField()
    
    # Parent/Guardian Information (Required for minors)
    parent_guardian_name = models.CharField(max_length=200, blank=True, null=True, 
                                            help_text="Full name of parent or legal guardian")
    parent_guardian_phone = models.CharField(max_length=20, blank=True, null=True)
    parent_guardian_email = models.EmailField(blank=True, null=True)
    
    # Father's Information (for sacrament records)
    father_name = models.CharField(max_length=200, blank=True, null=True)
    father_religion = models.CharField(max_length=20, choices=RELIGION_CHOICES, blank=True, null=True)
    
    # Mother's Information (for sacrament records)
    mother_name = models.CharField(max_length=200, blank=True, null=True)
    mother_religion = models.CharField(max_length=20, choices=RELIGION_CHOICES, blank=True, null=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=200, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True, 
                                                     help_text="e.g., Parent, Grandparent, Sibling")
    
    # Medical Information
    medical_notes = models.TextField(blank=True, null=True, 
                                     help_text="Allergies, medical conditions, or special needs")
    
    # Previous Parish (for transfer records)
    previous_parish = models.CharField(max_length=300, blank=True, null=True, 
                                       help_text="Previous parish name and location if applicable")
    
    # Godparent/Sponsor (for Baptism/Confirmation)
    godparent_sponsor_name = models.CharField(max_length=200, blank=True, null=True)
    godparent_sponsor_religion = models.CharField(max_length=20, choices=RELIGION_CHOICES, blank=True, null=True)
    
    # Certificates
    birth_certificate = models.FileField(upload_to='certificates/birth/', null=True, blank=True)
    baptism_certificate = models.FileField(upload_to='certificates/baptism/', null=True, blank=True)
    registration_date = models.DateField(auto_now_add=True)
    
    class Meta:
        ordering = ['-registration_date']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def has_baptism_certificate(self):
        return bool(self.baptism_certificate)
    
    def has_birth_certificate(self):
        return bool(self.birth_certificate)
    
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def is_minor(self):
        return self.age() < 18
    
    def get_primary_contact_email(self):
        """Returns appropriate email for communication"""
        if self.is_minor() and self.parent_guardian_email:
            return self.parent_guardian_email
        return self.email
    
    def get_primary_contact_phone(self):
        """Returns appropriate phone for communication"""
        if self.is_minor() and self.parent_guardian_phone:
            return self.parent_guardian_phone
        return self.phone
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Validate minors have parent/guardian info
        if self.is_minor():
            if not self.parent_guardian_name:
                raise ValidationError("Parent/Guardian name is required for minors.")
            if not self.parent_guardian_phone:
                raise ValidationError("Parent/Guardian phone is required for minors.")
        # Validate adults have email
        if not self.is_minor() and not self.email:
            raise ValidationError("Email is required for adult members.")


class Sacrament(AuditableModelWithManager):
    SACRAMENT_CHOICES = [
        ('baptism', 'Baptism'),
        ('confirmation', 'Confirmation'),
        ('eucharist', 'First Holy Communion'),
        ('reconciliation', 'Reconciliation'),
        ('marriage', 'Marriage'),
        ('holy_orders', 'Holy Orders'),
        ('anointing_sick', 'Anointing of the Sick'),
    ]
    
    name = models.CharField(max_length=50, choices=SACRAMENT_CHOICES, unique=True)
    requires_baptism_certificate = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    min_age = models.IntegerField(null=True, blank=True, help_text="Minimum age required")
    
    def __str__(self):
        return self.get_name_display()


class SacramentRequest(AuditableModelWithManager):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    SACRAMENT_CHOICES = [
        ('baptism', 'Baptism'),
        ('confirmation', 'Confirmation'),
        ('eucharist', 'First Holy Communion'),
        ('reconciliation', 'Reconciliation'),
        ('marriage', 'Marriage'),
        ('holy_orders', 'Holy Orders'),
        ('anointing_sick', 'Anointing of the Sick'),
    ] 
    member = models.ForeignKey(CatechesisMember, on_delete=models.CASCADE, related_name='sacrament_requests')
    sacrament = models.CharField(max_length=50, choices=SACRAMENT_CHOICES,default='baptism')
    request_date = models.DateField(auto_now_add=True)
    scheduled_date = models.DateField(null=True, blank=True, default=None)
    completion_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    
    # Approval tracking
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_requests'
    )
    review_date = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Completion tracking
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_requests'
    )
    
    # Notification tracking
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    sms_sent = models.BooleanField(default=False)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['member', 'sacrament']
        ordering = ['-request_date']
    
    def __str__(self):
        return f"{self.member} - {self.sacrament} ({self.status})"
    
    def clean(self):
        # Check if baptism certificate is required
        # Baptism is the only sacrament that doesn't require baptism certificate
        # All other sacraments require it
        if self.sacrament != 'baptism' and not self.member.has_birth_certificate():
            raise ValidationError(
                f"Birth certificate is required for {self.get_sacrament_display()}. "
                "Please upload a birth certificate before requesting this sacrament."
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CatechesisInstructor(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    ENTRY_TYPE_CHOICES = [
        ('user', 'System User'),
        ('manual', 'Manual Entry'),
    ]
    
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES, default='user')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    qualification = models.CharField(max_length=100,blank=True)
    specilization = models.CharField(max_length=100,blank=True, help_text="eg: Bible, Catechism, etc.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    joined_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-joined_date']
        verbose_name = 'Catechesis Instructor'
        verbose_name_plural = 'Catechesis Instructors'

    @property
    def display_first_name(self):
        return self.user.first_name if self.user else self.first_name

    @property
    def display_last_name(self):
        return self.user.last_name if self.user else self.last_name
        
    @property
    def display_email(self):
        return self.user.email if self.user else self.email
        
    @property
    def display_phone(self):
        return self.user.phone if self.user else self.phone  

    def full_name(self):
        return f"{self.display_first_name} {self.display_last_name}".strip() or "Unknown"
    
    def __str__(self):
        return self.full_name()


class SacramentClass(models.Model):
    """Sacrament preparation classes (Baptism, Confirmation, First Communion, etc.)"""
    SACRAMENT_TYPE_CHOICES = [
        ('BAPTISM', 'Baptism'),
        ('CONFIRMATION', 'Confirmation'),
        ('FIRST_COMMUNION', 'First Communion'),
        ('RCIA', 'RCIA - Rite of Christian Initiation for Adults'),
        ('RECONCILIATION', 'First Reconciliation'),
    ]
    
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200)
    sacrament_type = models.CharField(
        max_length=20,
        choices=SACRAMENT_TYPE_CHOICES
    )
    description = models.TextField(blank=True)
    
    # Schedule
    start_date = models.DateField()
    end_date = models.DateField()
    class_time = models.TimeField(help_text="Regular class time")
    meeting_day = models.CharField(
        max_length=10,
        choices=[
            ('SUNDAY', 'Sunday'),
            ('SATURDAY', 'Saturday'),
            ('WEDNESDAY', 'Wednesday'),
            ('OTHER', 'Other'),
        ],
        default='SUNDAY'
    )
    location = models.CharField(max_length=200, blank=True)
    
    coordinator = models.ForeignKey(
        CatechesisInstructor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coordinated_classes'
    )
    instructors = models.ManyToManyField(
        CatechesisInstructor,
        blank=True,
        related_name='teaching_classes'
    )
    
    max_capacity = models.PositiveIntegerField(default=150)
    
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='UPCOMING'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['sacrament_type', 'status']),
            models.Index(fields=['start_date', 'status']),
        ]
        verbose_name = 'Sacrament Class'
        verbose_name_plural = 'Sacrament Classes'
    
    def __str__(self):
        return f"{self.get_sacrament_type_display()} - {self.name}"
    
    def get_current_enrollment(self):
        return self.enrollments.filter(status='ENROLLED').count()
    
    def has_capacity(self):
        return self.get_current_enrollment() < self.max_capacity
    
    def get_instructor_names(self):
        """Return list of instructor names"""
        instructors = [self.coordinator.full_name()] if self.coordinator else []
        instructors += [i.full_name() for i in self.instructors.all()]
        return instructors

    
class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('ENROLLED','Enrolled'),
        ('COMPLETED','Completed'),
        ('DROPPED','Dropped'),
        ('TRANSFERRED','Transferred')
    ]

    catechesis_member = models.ForeignKey(CatechesisMember, on_delete=models.CASCADE,related_name = 'enrollments')
    # Made temporarily nullable to fix migration - should be required after data cleanup
    sacrament_class = models.ForeignKey(SacramentClass, on_delete=models.CASCADE, related_name='enrollments', null=True, blank=True)
    status = models.CharField(max_length=15, choices = STATUS_CHOICES, default='ENROLLED')
    enrolled_date = models.DateField(auto_now_add=True)
    completed_date = models.DateField(null=True, blank=True)
    request_source = models.CharField(max_length=100, blank = 'True', help_text="eg .. Baptism, Confirmation Request .")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # unique_together removed temporarily - re-add after data cleanup
        ordering = ['-enrolled_date']
        indexes = [
            models.Index(fields = ['catechesis_member','status']),
            models.Index(fields = ['sacrament_class','status']),
        ]
        verbose_name = 'class Enrollment'
        verbose_name_plural = 'class Enrollment'

    def __str__(self):
        class_name = self.sacrament_class.name if self.sacrament_class else "No Class"
        return f"{self.catechesis_member} - {class_name}"
        
    def mark_completed(self):
            self.status = 'COMPLETED'
            self.completion_date = timezone.now().date()
            self.save()
        
    @classmethod
    def auto_enroll(cls, catechesis_member, sacrament_type, request_source=''):
        active_class = SacramentClass.objects.filter(sacrament_type=sacrament_type, status='ACTIVE').order_by('start_date').first()
        if not active_class:
            active_class = SacramentClass.objects.filter(sacrament_type=sacrament_type, status='UPCOMING').order_by('start_date').first()

        if active_class and active_class.has_capacity():
            enrollment, created = cls.objects.get_or_create(
                catechesis_member=catechesis_member,
                sacrament_class=active_class,
                defaults={
                    'status': 'ENROLLED',
                    'request_source': request_source
                }
            )
            return enrollment, created

        return None, False

class ClassAttendance(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('EXCUSED', 'Excused'),
        ('LATE', 'Late'),
    ]

    sacrament_class = models.ForeignKey(SacramentClass,on_delete = models.CASCADE,related_name = 'attendance_sessions')
    class_date = models.DateField()
    enrollment = models.ForeignKey(Enrollment,on_delete = models.CASCADE, related_name = 'attendance_records')
    status = models.CharField(max_length = 10, choices = STATUS_CHOICES,default = 'ABSENT')
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    recorded_at = models.DateTimeField(auto_now_add = True)
    
    class Meta:
        # Prevent duplicate attendance records
        unique_together = ['sacrament_class', 'class_date', 'enrollment']
        ordering = ['-class_date', 'enrollment__catechesis_member__last_name']
        indexes = [
            models.Index(fields=['sacrament_class', 'class_date']),
            models.Index(fields=['enrollment', 'class_date']),
        ]
        verbose_name = 'Class Attendance'
        verbose_name_plural = 'Class Attendance Records'
    
    def __str__(self):
        member_name = self.enrollment.catechesis_member
        return f"{member_name} - {self.class_date} - {self.get_status_display()}"
    
    @property
    def catechesis_member(self):
        return self.enrollment.catechesis_member
    
    @classmethod
    def mark_attendance(cls, sacrament_class, class_date, enrollment, status, recorded_by=None, notes=''):
        attendance, created = cls.objects.update_or_create(
            sacrament_class=sacrament_class,
            class_date=class_date,
            enrollment=enrollment,
            defaults={
                'status': status,
                'notes': notes,
                'recorded_by': recorded_by
            }
        )
        return attendance
    
    @classmethod
    def get_class_attendance_stats(cls, sacrament_class, class_date):
        attendances = cls.objects.filter(
            sacrament_class=sacrament_class,
            class_date=class_date
        )
        
        total = attendances.count()
        if total == 0:
            return None
        
        return {
            'total_enrolled': total,
            'present': attendances.filter(status='PRESENT').count(),
            'absent': attendances.filter(status='ABSENT').count(),
            'excused': attendances.filter(status='EXCUSED').count(),
            'late': attendances.filter(status='LATE').count(),
        }

class SacramentRecord(models.Model):
    """Records of received sacraments (Baptism, Confirmation, First Communion, etc.)"""
    SACRAMENT_CHOICES = [
        ('BAPTISM', 'Baptism'),
        ('CONFIRMATION', 'Confirmation'),
        ('FIRST_COMMUNION', 'First Communion'),
        ('FIRST_RECONCILIATION', 'First Reconciliation'),
        ('RCIA_COMPLETION', 'RCIA Completion'),
    ]
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('POSTPONED', 'Postponed'),
    ]
    
    # The catechesis member receiving the sacrament
    catechesis_member = models.ForeignKey(
        CatechesisMember,
        on_delete=models.CASCADE,
        related_name='sacrament_records'
    )
    
    # Type of sacrament
    sacrament_type = models.CharField(
        max_length=25,
        choices=SACRAMENT_CHOICES
    )
    
    # Status
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='SCHEDULED'
    )
    
    # Ceremony details
    ceremony_date = models.DateField()
    ceremony_time = models.TimeField(null=True, blank=True)
    location = models.CharField(
        max_length=200,
        default='Christ The King Parish'
    )
    
    # The class they completed (if applicable)
    completed_class = models.ForeignKey(
        SacramentClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sacraments_conferred'
    )
    
    # Minister/Priest who performed the sacrament
    minister_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of priest/deacon who performed the sacrament"
    )
    
    # Godparents/Sponsors (for Baptism/Confirmation)
    godparent_1_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Godparent/Sponsor 1'
    )
    godparent_2_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Godparent/Sponsor 2'
    )
    
    # Certificate
    certificate_number = models.CharField(
        max_length=50,
        blank=True,
        unique=True
    )
    certificate_issued = models.BooleanField(default=False)
    certificate_date = models.DateField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Record keeping
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # One record per sacrament type per person
        unique_together = ['catechesis_member', 'sacrament_type']
        ordering = ['-ceremony_date']
        indexes = [
            models.Index(fields=['sacrament_type', 'ceremony_date']),
            models.Index(fields=['catechesis_member', 'status']),
            models.Index(fields=['certificate_number']),
        ]
        verbose_name = 'Sacrament Record'
        verbose_name_plural = 'Sacrament Records'
    
    def __str__(self):
        return f"{self.catechesis_member} - {self.get_sacrament_type_display()} - {self.ceremony_date}"
    
    def issue_certificate(self, certificate_number, date=None):
        """Mark certificate as issued"""
        from django.utils import timezone
        self.certificate_number = certificate_number
        self.certificate_issued = True
        self.certificate_date = date or timezone.now().date()
        self.save()
    
    def mark_completed(self, ceremony_date=None):
        """Mark sacrament as completed"""
        from django.utils import timezone
        self.status = 'COMPLETED'
        if ceremony_date:
            self.ceremony_date = ceremony_date
        self.save()
    
    @classmethod
    def get_member_sacraments(cls, catechesis_member):
        """Get all sacraments for a member"""
        return cls.objects.filter(catechesis_member=catechesis_member)
    
    @classmethod
    def has_received(cls, catechesis_member, sacrament_type):
        """Check if member has received a specific sacrament"""
        return cls.objects.filter(
            catechesis_member=catechesis_member,
            sacrament_type=sacrament_type,
            status='COMPLETED'
        ).exists()

