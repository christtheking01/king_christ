from django.db import models
from django.utils import timezone
from datetime import timedelta


class AnalyticsCache(models.Model):
    """Cache analytics data for faster loading"""
    key = models.CharField(max_length=100, unique=True)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.key} - {self.created_at}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @classmethod
    def get_or_create(cls, key, data_func, ttl_hours=24):
        """Get cached data or create new"""
        try:
            cache = cls.objects.get(key=key)
            if not cache.is_expired:
                return cache.data
        except cls.DoesNotExist:
            pass
        except Exception:
            # If cache table doesn't exist or other DB error, skip caching
            return data_func()
        
        # Generate new data
        data = data_func()
        
        # Try to save to cache, but don't fail if it doesn't work
        try:
            cls.objects.update_or_create(
                key=key,
                defaults={
                    'data': data,
                    'expires_at': timezone.now() + timedelta(hours=ttl_hours)
                }
            )
        except Exception:
            # If caching fails, just return the data
            pass
        
        return data
