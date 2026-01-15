from django.utils import timezone
from enum import member
import os, random
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField

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
    name = models.CharField(max_length=255)
    feast_name = models.TextField(max_length=10, blank=True, null=True)
    feast_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        verbose_name_plural = "Ministries"


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
    
    def __str__(self):
        community_name = self.community.name if self.community else "No Community"
        return f"{self.leader_name} - {self.position} ({self.ministry.name}) - {community_name}"
    
    class Meta:
        unique_together = ['ministry', 'position']  # One position per ministry
        ordering = ['ministry', 'position']

class Community(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class CommunityLeader(models.Model):
    RANK_CHOICES = [
        ('VICE CHAIR', 'Vice Chair'),
        ('SECRETARY', 'Secretary'),
        ('VICE SECRETARY', 'Vice Secretary'),
        ('ACCOUNTANT', 'Accountant'),
        ('CHAIRPERSON', 'Chairperson'),  # Added chairperson
    ]
    
    community_name = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='leaders', null=True)
    name = models.CharField(max_length=250 , null=True)
    #leader = models.OneToOneField("Member", on_delete=models.CASCADE,related_name='supervisor',choices=RANK_CHOICES ,blank=True, null=True)
    leader = models.CharField(max_length=250, null=True, blank=True)
    description = models.TextField(blank=True, null=True )
    feast_name = models.TextField(max_length='10',blank=True, null=True )
    feast_date = models.DateField(blank=True, null=True)
    phone = PhoneNumberField(max_length=255,blank=True, null=True)
    
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

    def new_believer_school(self):
        # return self.get_queryset().filter(new_believer_school=True)
        return self.active().filter(new_believer_school=True)

    def pays_tithe(self):
        # return self.get_queryset().filter(pays_tithe=True)
        return self.active().filter(pays_tithe=True)

    def working(self):
        # return self.get_queryset().filter(working=True)
        return self.active().filter(working=True)

    def schooling(self):
        # return self.get_queryset().filter(schooling=True)
        return self.active().filter(schooling=True)


class Member(models.Model):
    name = models.CharField(max_length=255)
    code = models.TextField(help_text="001PT", null= True)
    active = models.BooleanField(default= True)
    shepherd = models.ForeignKey(Community, on_delete=models.CASCADE, null=True, blank=True)
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, null=True, blank=True)
    telephone =PhoneNumberField(max_length=255, null=True, help_text=' Eg. +255 ')
    location = models.CharField(max_length=255)
    fathers_name = models.CharField(max_length=255, null=True, blank=True)
    mothers_name = models.CharField(max_length=255, null=True, blank=True)
    guardians_name = models.CharField(max_length=255, null=True, blank=True)
    new_believer_school = models.BooleanField()
    pays_tithe = models.BooleanField(default=False)
    working = models.BooleanField(default=False)
    schooling = models.BooleanField(default=False)
    picture = models.ImageField(upload_to=upload_image_path, null=True, blank=True)
    transfered = models.BooleanField(max_length=250, blank=True, null= True)
    transfer_update = models.CharField(max_length=250, null=True, blank=True)

    objects = MemberManager()

    def __str__(self):
        return f'{self.name}'
    
    @property
    def picture_url(self):
        if self.picture and hasattr(self.picture, 'url'):
            return self.picture.url
        return f"{settings.STATIC_URL}images/default-avatar.png"
    


class TestDb(models.Model):
    field = models.CharField(max_length=120)