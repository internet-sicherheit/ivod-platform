from rest_framework import serializers
from .models import *
from base64 import b64decode
from uuid import uuid4
from pathlib import Path
from django.contrib.auth.models import AnonymousUser

# class UserField(serializers.Field):
#
#     def to_internal_value(self, data):
#         user = User.objects.get(pk=data)
#         if not user:
#             raise serializers.ValidationError("No such user")
#         return user
#
#     def to_representation(self, value):
#         return value.id
#
# class DatasourceField(serializers.Field):
#
#     def to_representation(self, value):
#         return value.id
#
#     def to_internal_value(self, data):
#         datasource = Datasource.objects.get(pk=data)
#         if not datasource:
#             raise serializers.ValidationError("No such datasource")
#         return datasource

class ChartSerializer(serializers.ModelSerializer):

    class Meta:
        model = Chart
        fields = '__all__'
        read_only_fields = ['chart_name', 'id', 'owner', 'original_datasource']
        extra_kwargs = {
            'config': {'required': False},
            'downloadable': {'required': False},
            'visibility': {'required': False},
            'scope_path': {'required': False},
            'shared_users': {'required': False},
            'shared_groups': {'required': False}
        }

    def validate(self, data):
        unvalidated_data = self.context['request'].data
        unvalidated_data.update(data)
        if 'datasource' in unvalidated_data and type(unvalidated_data['datasource']) != Datasource:
            unvalidated_data['datasource'] = Datasource.objects.get(id=unvalidated_data['datasource'])
        return unvalidated_data

    def validate_create(self, data):
        if 'datasource' not in data:
            raise serializers.ValidationError("Datasource is required for chart creation")
        if 'chart_name' not in data:
            raise serializers.ValidationError("Chart type must be given")
        if self.context['request'].user == None or type(self.context['request'].user) == AnonymousUser:
            raise serializers.ValidationError("Only users may create Charts")
        return data

    def create(self, validated_data):
        validated_data = self.validate_create(validated_data)
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

    def update(self, instance, validated_data):
        instance.scope_path = validated_data.get('scope_path', instance.scope_path)
        instance.config = validated_data.get('config', instance.config)
        instance.downloadable = validated_data.get('downloadable', instance.downloadable)
        instance.visibility = validated_data.get('visibility', instance.visibility)
        instance.save()
        return instance


class DatasourceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Datasource
        fields = '__all__'
        extra_kwargs = {
            'source': {'required': False},
            'owner': {'required': False},
            'shared_users': {'required': False},
            'shared_groups': {'required': False}
        }

    def validate(self, data):
        unvalidated_data = self.context['request'].data
        unvalidated_data.update(data)
        if 'source' in unvalidated_data:
            unvalidated_data.pop('source')
        if 'url' in unvalidated_data:
            #TODO: Validate URL here
            pass
        if 'data' in unvalidated_data:
            #TODO: Validate actual data here:
            pass
        return unvalidated_data

    def validate_create(self, data):
        if 'scope_path' not in data:
            raise serializers.ValidationError("No scope_path specified")
        if 'url' not in data and 'data' not in data:
            raise serializers.ValidationError("Neither data nor url specified")
        if self.context['request'].user == None or type(self.context['request'].user) == AnonymousUser:
            raise serializers.ValidationError("Only users may create Charts")
        return data

    def create(self, validated_data):
        validated_data = self.validate_create(validated_data)
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
