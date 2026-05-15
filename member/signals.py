from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CommunityLeader, Member


@receiver(post_save, sender=CommunityLeader)
def create_member_from_community_leader(sender, instance, created, **kwargs):
    """
    Automatically create a Member when a CommunityLeader is created.
    The leader will be linked to their community via the shepherd field.
    """
    if created and instance.name:
        # Check if a member with this name already exists
        existing_member = Member.objects.filter(
            name__iexact=instance.name.strip()
        ).first()

        if existing_member:
            # If member exists but has no community, update their community
            if not existing_member.shepherd and instance.community_name:
                existing_member.shepherd = instance.community_name
                if instance.phone:
                    existing_member.telephone = instance.phone
                existing_member.save()
        else:
            # Create new member from community leader
            Member.objects.create(
                name=instance.name.strip(),
                shepherd=instance.community_name,
                telephone=instance.phone if instance.phone else None,
                location=instance.community_name.name if instance.community_name else '',
                active=True
            )
