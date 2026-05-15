from django.db import models
from django.utils import timezone
from users.models import User


class AuditableModel(models.Model):
    """Abstract base model with audit fields and soft delete"""
    
    # Audit fields
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='%(class)s_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_modified'
    )
    modified_at = models.DateTimeField(auto_now=True)
    
    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted'
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def soft_delete(self, user=None):
        """Soft delete the instance"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def restore(self, user=None):
        """Restore a soft-deleted instance"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def hard_delete(self):
        """Permanent delete"""
        super().delete()


class AuditableManager(models.Manager):
    """Manager that excludes soft-deleted records by default"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def all_with_deleted(self):
        """Return all records including soft-deleted"""
        return super().get_queryset()
    
    def deleted(self):
        """Return only soft-deleted records"""
        return super().get_queryset().filter(is_deleted=True)


class AuditableModelWithManager(AuditableModel):
    """Auditable model with default manager excluding soft-deleted records"""
    
    objects = AuditableManager()
    all_objects = models.Manager()  # Access to all records including deleted
    
    class Meta:
        abstract = True
