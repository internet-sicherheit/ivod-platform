from django.db import models
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404

# Create your models here.
class Datasource(models.Model):
    source = models.URLField()
    scope_path = models.CharField(max_length=256)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner','scope_path'],name='datasource_unique_user_scope_path'),
        ]

class Chart(models.Model):

    VISIBILITY_PRIVATE = 0
    VISIBILITY_SHARED = 1
    VISIBILITY_SEMI_PUBLIC = 2
    VISIBILITY_PUBLIC = 3

    chart_name = models.CharField(max_length=256)
    scope_path = models.CharField(max_length=256)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    original_datasource = models.ForeignKey(Datasource, on_delete=models.DO_NOTHING, blank=True, null=True)
    #TODO: config in file or in db?
    config = models.CharField(max_length=8192)
    downloadable = models.BooleanField(default=False)
    visibility = models.IntegerField(default=VISIBILITY_PRIVATE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner','scope_path'],name='chart_unique_user_scope_path'),
        ]

class EnhancedUser(models.Model):
    #TODO: Better name
    #TODO: Make auth_user private key
    auth_user = models.ForeignKey(User, on_delete=models.CASCADE)
    datasources_shared_with_user = models.ManyToManyField(Datasource)
    charts_shared_with_user = models.ManyToManyField(Chart)

class EnhancedGroup(models.Model):
    auth_group = models.ForeignKey(Group, on_delete=models.CASCADE)
    datasources_shared_with_group = models.ManyToManyField(Datasource)
    charts_shared_with_group = models.ManyToManyField(Chart)
