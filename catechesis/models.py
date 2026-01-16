from django.db import models
from django.forms import ValidationError
from users.models import User 

from christ_king_church.christ_king_church import settings

# Create your models here
class CatechesisMember(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    birth_certificate = models.FileField(upload_to='certificates/birth/', null=True, blank=True)
    baptism_certificate = models.FileField(upload_to='certificates/baptism/', null=True, blank=True)
    registration_date = models.DateField(auto_now_add=True)
    
    class Meta:
        ordering = ['-registration_date']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def has_baptism_certificate(self):
        return bool(self.baptism_certificate)


class Sacrament(models.Model):
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


class SacramentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    member = models.ForeignKey(CatechesisMember, on_delete=models.CASCADE, related_name='sacrament_requests')
    sacrament = models.ForeignKey(Sacrament, on_delete=models.CASCADE)
    request_date = models.DateField(auto_now_add=True)
    scheduled_date = models.DateField(null=True, blank=True)
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
    
    class Meta:
        unique_together = ['member', 'sacrament']
        ordering = ['-request_date']
    
    def __str__(self):
        return f"{self.member} - {self.sacrament} ({self.status})"
    
    def clean(self):
        # Check if baptism certificate is required
        if self.sacrament.requires_baptism_certificate and not self.CatechesisMember.has_baptism_certificate():
            raise ValidationError(
                f"Birth certificate is required for {self.sacrament}. "
                "Please upload a birth certificate before requesting this sacrament."
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
