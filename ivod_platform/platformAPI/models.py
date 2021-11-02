from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    real_name = models.BooleanField(default=False)
    public_profile = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    creation_time = models.DateTimeField(auto_now_add=True)

class ShareGroup(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_owner")
    name = models.CharField(max_length=256)
    group_admins = models.ManyToManyField(User, related_name="group_admins", blank=True,)
    group_members = models.ManyToManyField(User, related_name="group_members", blank=True,)
    is_public = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='group_unique_user_scope_path'),
        ]

# Create your models here.
class Datasource(models.Model):
    source = models.URLField()
    creation_time = models.DateTimeField(auto_now_add=True)
    modification_time = models.DateTimeField(auto_now=True)
    datasource_name = models.CharField(max_length=256)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="datasource_owner")

    shared_users = models.ManyToManyField(User, related_name="datasource_shared_users")
    shared_groups = models.ManyToManyField(ShareGroup, related_name="datasource_shared_groups")
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'datasource_name'],name='datasource_unique_user_datasource_name'),
        ]

class Chart(models.Model):

    VISIBILITY_PRIVATE = 0
    VISIBILITY_SHARED = 1
    VISIBILITY_SEMI_PUBLIC = 2
    VISIBILITY_PUBLIC = 3

    chart_type = models.CharField(max_length=256)
    chart_name = models.CharField(max_length=256)
    creation_time = models.DateTimeField(auto_now_add=True)
    modification_time = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chart_owner")
    original_datasource = models.ForeignKey(Datasource, on_delete=models.SET_NULL, blank=True, null=True)
    downloadable = models.BooleanField(default=False)
    visibility = models.IntegerField(default=VISIBILITY_PRIVATE)

    shared_users = models.ManyToManyField(User, related_name="chart_shared_users")
    shared_groups = models.ManyToManyField(ShareGroup, related_name="chart_shared_groups")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'chart_name'],name='chart_unique_user_scope_path'),
        ]