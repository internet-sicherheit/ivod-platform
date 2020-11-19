from rest_framework import serializers
from .models import *
from base64 import b64decode
from uuid import uuid4
from pathlib import Path
from django.contrib.auth.models import AnonymousUser


class UserField(serializers.Field):

    def to_internal_value(self, data):
        user = User.objects.get(pk=data)
        if not user:
            raise serializers.ValidationError("No such user")
        return user

    def to_representation(self, value):
        return value.id

class DatasourceField(serializers.Field):

    def to_representation(self, value):
        return value.id

    def to_internal_value(self, data):
        datasource = Datasource.objects.get(pk=data)
        if not datasource:
            raise serializers.ValidationError("No such datasource")
        return datasource

class ChartSerializer(serializers.Serializer):

    chart_name = serializers.CharField(max_length=256)
    scope_path = serializers.CharField(max_length=256)
    owner = UserField(required=False)
    datasource = DatasourceField(required=False)
    # TODO: config in file or in db?
    config = serializers.CharField(max_length=8192)
    downloadable = serializers.BooleanField(default=False)
    visibility = serializers.IntegerField(default=Chart.VISIBILITY_PRIVATE)
    id = serializers.IntegerField(required=False)

    def validate(self, data):
        if 'chart_name' not in data:
            raise serializers.ValidationError("No chart name specified")
        if 'scope_path' not in data:
            raise serializers.ValidationError("No scope_path specified")
        if 'owner' not in data:
            raise serializers.ValidationError("No owner specified specified")
        if 'config' not in data:
            raise serializers.ValidationError("No config specified specified")
        return data

    def create(self, validated_data):
        if 'datasource' not in validated_data:
            raise serializers.ValidationError("Datasource is required for chart creation")
        user = self.context['request'].user
        chart = Chart.objects.create(
            chart_name=validated_data['chart_name'],
            scope_path=validated_data['scope_path'],
            owner=user,
            original_datasource=validated_data['datasource'],
            config=validated_data['config'],
            downloadable=validated_data.get('downloadable',False),
            visibility=validated_data.get('downloadable', Chart.VISIBILITY_PRIVATE)
        )
        return chart


class DatasourceSerializer(serializers.Serializer):
    scope_path = serializers.CharField(max_length=256)
    url = serializers.URLField(required=False)
    data = serializers.CharField(required=False)
    id = serializers.IntegerField(required=False)
    owner = UserField(required=False)

    def validate(self, data):
        if 'scope_path' not in data:
            raise serializers.ValidationError("No scope_path specified")
        if 'url' not in data and 'data' not in data:
            raise serializers.ValidationError("Neither data nor url specified")
        if 'owner' not in data:
            raise serializers.ValidationError("No owner specified specified")
        return data

    def create(self, validated_data):
        user = self.context['request'].user

        if 'url' in validated_data:
            datasource = Datasource.objects.create(source=validated_data['url'], scope_path=validated_data['scope_path'], owner=user)
        else:
            data = b64decode(validated_data['data'])
            #FIXME: Read base path from config
            file_path = Path(__file__).resolve().parent.parent.joinpath("datasources").joinpath(uuid4().hex)
            with file_path.open("w") as file:
                file.write(data.decode('utf-8'))
            datasource = Datasource.objects.create(source=file_path, scope_path=validated_data['scope_path'], owner=user)
        return datasource

class EnhancedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnhancedUser
        fields = '__all__'

class EnhancedGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnhancedGroup
        fields = '__all__'
