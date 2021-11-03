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


class ShareableModel(models.Model):

    class Meta:
        abstract = True

    VISIBILITY_PRIVATE = 0
    VISIBILITY_SHARED = 1
    VISIBILITY_SEMI_PUBLIC = 2
    VISIBILITY_PUBLIC = 3

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="%(class)s_owner")
    visibility = models.IntegerField(default=VISIBILITY_PRIVATE)

    shared_users = models.ManyToManyField(User)
    shared_groups = models.ManyToManyField(ShareGroup)


class Datasource(ShareableModel):
    source = models.URLField()
    creation_time = models.DateTimeField(auto_now_add=True)
    modification_time = models.DateTimeField(auto_now=True)
    datasource_name = models.CharField(max_length=256)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'datasource_name'],name='datasource_unique_user_datasource_name'),
        ]

class Chart(ShareableModel):

    chart_type = models.CharField(max_length=256)
    chart_name = models.CharField(max_length=256)
    creation_time = models.DateTimeField(auto_now_add=True)
    modification_time = models.DateTimeField(auto_now=True)
    original_datasource = models.ForeignKey(Datasource, on_delete=models.SET_NULL, blank=True, null=True)
    downloadable = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'chart_name'],name='chart_unique_user_scope_path'),
        ]

class Dashboard(ShareableModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    creation_time = models.DateTimeField(auto_now_add=True)
    modification_time = models.DateTimeField(auto_now=True)
    config = models.CharField(max_length=1024*16) #TODO: Adequate limit?

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='dashboard_unique_user_scope_path'),
        ]