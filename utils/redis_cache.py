"""
Redis Cache Utilities for Christ The King Church Management System

This module provides convenient functions for caching frequently accessed data.
"""

import json
import hashlib
from functools import wraps
from django.core.cache import cache
from django.conf import settings


def generate_cache_key(prefix, *args, **kwargs):
    """Generate a unique cache key from prefix and arguments."""
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    key_string = "|".join(key_parts)
    
    # Create MD5 hash for consistent length
    return hashlib.md5(key_string.encode()).hexdigest()


def cache_queryset(timeout=300):
    """
    Decorator to cache queryset results.
    
    Usage:
        @cache_queryset(timeout=600)
        def get_active_members():
            return Member.objects.active()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = generate_cache_key(
                func.__name__,
                *args,
                **kwargs
            )
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            return result
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """Invalidate all cache keys matching a pattern."""
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(pattern)
    else:
        # Fallback for non-Redis backends
        # This is less efficient but works
        pass


def clear_member_cache():
    """Clear all member-related cache when member data changes."""
    cache.delete_pattern("*member*")
    cache.delete_pattern("*shepherd*")


# Church Management Specific Cache Helpers

def cache_member_count(timeout=300):
    """Cache the total member count."""
    from member.models import Member
    
    key = 'church:stats:member_count'
    count = cache.get(key)
    
    if count is None:
        count = Member.objects.active().count()
        cache.set(key, count, timeout=timeout)
    
    return count


def cache_tithe_summary(month, year, timeout=3600):
    """Cache tithe summary for a specific month."""
    from finance.models import TithePayment
    from django.db.models import Sum, Count
    
    key = f'church:tithe_summary:{year}:{month}'
    summary = cache.get(key)
    
    if summary is None:
        payments = TithePayment.objects.filter(
            date__year=year,
            date__month=month
        )
        
        summary = {
            'total_amount': payments.aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_payments': payments.count(),
            'unique_payers': payments.values('name').distinct().count(),
        }
        cache.set(key, summary, timeout=timeout)
    
    return summary


def cache_community_stats(community_id, timeout=600):
    """Cache statistics for a specific community/shepherd."""
    from member.models import Member, Community
    
    key = f'church:community_stats:{community_id}'
    stats = cache.get(key)
    
    if stats is None:
        try:
            community = Community.objects.get(id=community_id)
            members = Member.objects.filter(shepherd=community)
            
            stats = {
                'community_name': community.name,
                'member_count': members.count(),
                'tithe_payers': members.filter(pays_tithe=True).count(),
                'new_believers': members.filter(gender='female').count(),
                'working_members': members.filter(working=True).count(),
                'schooling_members': members.filter(schooling=True).count(),
            }
            cache.set(key, stats, timeout=timeout)
        except Community.DoesNotExist:
            return None
    
    return stats


def get_cached_dashboard_stats(timeout=3600):
    """Get cached dashboard statistics."""
    from django.utils import timezone
    from member.models import Member
    from finance.models import TithePayment, Offering
    from django.db.models import Sum
    
    today = timezone.now().date()
    cache_key = f'dashboard_stats:{today}'
    
    stats = cache.get(cache_key)
    if stats is None:
        current_month = today.month
        current_year = today.year
        
        stats = {
            # Member stats
            'total_members': Member.objects.active().count(),
            'total_communities': Member.objects.values('shepherd').distinct().count(),
            
            # Tithe stats
            'month_tithe_total': TithePayment.objects.filter(
                date__month=current_month,
                date__year=current_year
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            
            'year_tithe_total': TithePayment.objects.filter(
                date__year=current_year
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            
            # Offering stats
            'month_offering_total': Offering.objects.filter(
                date__month=current_month,
                date__year=current_year
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            
            # Category stats
            'tithe_payers': Member.objects.pays_tithe().count(),
            'new_believers': Member.objects.filter(gender='female').count(),
            'working_members': Member.objects.working().count(),
            'schooling_members': Member.objects.schooling().count(),
        }
        
        cache.set(cache_key, stats, timeout=timeout)
    
    return stats


# Manual Cache Management

def refresh_all_stats():
    """Force refresh all statistics (use after bulk data import)."""
    # Delete all stats cache keys
    for key in [
        'church:stats:member_count',
        'dashboard_stats:*',
        'church:tithe_summary:*',
        'church:community_stats:*',
    ]:
        invalidate_cache_pattern(key)


def warm_cache():
    """
    Pre-populate cache with common queries.
    Call this on application startup or after cache clear.
    """
    print("Warming up cache...")
    
    # Cache member count
    cache_member_count()
    
    # Cache dashboard stats
    get_cached_dashboard_stats()
    
    print("Cache warm-up complete!")
