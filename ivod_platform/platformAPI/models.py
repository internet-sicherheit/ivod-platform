from django.db import models
from django.contrib.auth.models import User, Group

# Create your models here.
class Datasource(models.Model):
    source = models.URLField()
    scope_path = models.CharField(max_length=256)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)

class Chart(models.Model):

    VISIBILITY_PRIVATE = 0
    VISIBILITY_SHARED = 1
    VISIBILITY_SEMI_PUBLIC = 2
    VISIBILITY_PUBLIC = 3

    chart_name = models.CharField(max_length=256)
    scope_path = models.CharField(max_length=256)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    #TODO: config in file or in db?
    config = models.CharField(max_length=8192)
    downloadable = models.BooleanField(default=False)
    visibility = models.IntegerField(default=VISIBILITY_PRIVATE)

class EnhancedUser(models.Model):
    #TODO: Better name
    auth_user = models.ForeignKey(User, on_delete=models.CASCADE)
    datasources_shared_with_user = models.ManyToManyField(Datasource, blank=True)
    charts_shared_with_user = models.ManyToManyField(Chart, blank=True)

class EnhancedGroup(models.Model):
    auth_group = models.ForeignKey(Group, on_delete=models.CASCADE)
    datasources_shared_with_group = models.ManyToManyField(Datasource, blank=True)
    charts_shared_with_group = models.ManyToManyField(Chart, blank=True)