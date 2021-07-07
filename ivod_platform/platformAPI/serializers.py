from rest_framework import serializers
from .models import *
from base64 import b64decode
from uuid import uuid4
from pathlib import Path
from django.contrib.auth.models import AnonymousUser

from .util import *

class ChartSerializer(serializers.ModelSerializer):

    #FIXME: Dont always generate JS, copy to a static dir; check folder structure; might need to touch output manager again

    class Meta:
        model = Chart
        fields = '__all__'
        read_only_fields = ['chart_type', 'id', 'owner', 'original_datasource', 'creation_time', 'modification_time']
        extra_kwargs = {
            'config': {'required': False},
            'downloadable': {'required': False},
            'visibility': {'required': False},
            'chart_name': {'required': False},
            'owner': {'required': False, 'read_only': True},
            'shared_users': {'required': False, 'write_only': True},
            'shared_groups': {'required': False, 'write_only': True}
        }

    def validate(self, data):
        unvalidated_data = self.context['request'].data
        unvalidated_data.update(data)
        if 'datasource' in unvalidated_data and type(unvalidated_data['datasource']) != Datasource:
            unvalidated_data['datasource'] = Datasource.objects.get(id=unvalidated_data['datasource'])
        return unvalidated_data

    def validate_create(self, data):
        """Validation step required on creation only."""

        if 'datasource' not in data:
            raise serializers.ValidationError("Datasource is required for chart creation")
        if 'chart_type' not in data:
            raise serializers.ValidationError("Chart type must be given")
        if 'chart_name' not in data:
            raise serializers.ValidationError("Chart name must be given")
        if self.context['request'].user == None or type(self.context['request'].user) == AnonymousUser:
            raise serializers.ValidationError("Only users may create Charts")

        supported = get_chart_types_for_datasource(data["datasource"])
        if data["chart_type"] not in supported:
            raise serializers.ValidationError(f"Chart type not supported for this datasource. Supported types are: {supported}")
        return data

    def create(self, validated_data):
        validated_data = self.validate_create(validated_data)
        user = self.context['request'].user
        # TODO: How to handle shares during creation? Ignore and keep sharing a separate action?
        chart = Chart.objects.create(
            chart_type=validated_data['chart_type'],
            chart_name=validated_data['chart_name'],
            owner=user,
            original_datasource=validated_data['datasource'],
            downloadable=validated_data.get('downloadable',False),
            visibility=validated_data.get('visibility', Chart.VISIBILITY_PRIVATE)
        )
        try:
            generate_chart(datasource=validated_data["datasource"], chart_id=chart.id, chart_type=validated_data["chart_type"], request=self.context['request'], config=validated_data["config"])
        except Exception as e:
            # Try to erase file system artifacts
            try:
                get_chart_base_path().joinpath(str(chart.id)).rmdir()
            except:
                pass
            # Remove stale db entry and reraise exception
            chart.delete()
            raise e
        return chart

    def update(self, instance, validated_data):
        instance.chart_name = validated_data.get('chart_name', instance.chart_name)
        instance.downloadable = validated_data.get('downloadable', instance.downloadable)
        instance.visibility = validated_data.get('visibility', instance.visibility)

        # TODO: Could there be a case where modification fails halfway through?
        # Especially file access is not atomic, keep a backup and restore from that?
        modify_chart(chart_id=instance.id, request=self.context['request'], config=validated_data.get('config',None))

        instance.save()
        return instance


class DatasourceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Datasource
        fields = '__all__'
        read_only_fields = ['creation_time', 'modification_time']
        extra_kwargs = {
            'source': {'required': False, 'write_only': True},
            'owner': {'required': False, 'read_only': True},
            'datasource_name': {'required': False},
            'shared_users': {'required': False, 'write_only': True},
            'shared_groups': {'required': False, 'write_only': True}
        }

    def validate(self, data):
        unvalidated_data = self.context['request'].data
        unvalidated_data.update(data)
        if 'source' in unvalidated_data:
            unvalidated_data.pop('source')
        return unvalidated_data

    def validate_create(self, data):
        """Validation step required on creation only."""

        if 'datasource_name' not in data:
            raise serializers.ValidationError("No datasource_name specified")
        if 'url' not in data and 'data' not in data:
            raise serializers.ValidationError("Neither data nor url specified")
        if 'url' in data and 'data' in data:
            raise serializers.ValidationError("data and url must not be used together")
        if 'url' in data:
            #TODO: Validate URL here
            pass

        #TODO: Validate actual data here

        if self.context['request'].user == None or type(self.context['request'].user) == AnonymousUser:
            raise serializers.ValidationError("Only users may create Charts")
        return data

    def create(self, validated_data):
        validated_data = self.validate_create(validated_data)
        user = self.context['request'].user
        #TODO: How to handle shares during creation? Ignore and keep sharing a separate action?
        if 'url' in validated_data:
            datasource = Datasource.objects.create(source=validated_data['url'], datasource_name=validated_data['datasource_name'], owner=user)
        else:
            data = b64decode(validated_data['data'])
            file_path = get_datasource_base_path().joinpath(uuid4().hex)
            with file_path.open("w") as file:
                file.write(data.decode('utf-8'))
            # TODO: Handle Database exceptions better (especially violated constraints)
            datasource = Datasource.objects.create(source=file_path, datasource_name=validated_data['datasource_name'], owner=user)
        return datasource

    def update(self, instance, validated_data):
        instance.datasource_name = validated_data.get('datasource_name', instance.datasource_name)
        instance.save()
        return instance

class ShareGroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShareGroup
        fields = '__all__'
        read_only_fields = ['owner','name']
        extra_kwargs = {
            'group_admins': {'required': False},
            'group_members': {'required': False},
            'is_public': {'required': False}
        }

    def validate(self, data):
        unvalidated_data = self.context['request'].data
        unvalidated_data.update(data)
        # Owner will be set by the requesting user. If it is set, remove it
        if 'owner' in unvalidated_data:
            unvalidated_data.pop('owner')
        return unvalidated_data

    def validate_create(self, data):
        """Validation step required on creation only."""

        if 'name' not in data:
            raise ValueError("No group name chosen.")
        if 'is_public' not in data:
            data['is_public'] = False
        if 'group_admins' not in data:
            data['group_admins'] = []
        if 'group_members' not in data:
            data['group_members'] = []
        if self.context['request'].user == None or type(self.context['request'].user) == AnonymousUser:
            raise serializers.ValidationError("Only users may create Groups")
        return data

    def create(self, validated_data):
        validated_data = self.validate_create(validated_data)
        user = self.context['request'].user
        #TODO: How to handle shares during creation? Ignore and keep sharing a separate action?
        group = ShareGroup.objects.create(owner=user,
                                          name=validated_data["name"],
                                          is_public=validated_data["is_public"])
        group.group_admins.set(validated_data["group_admins"])
        group.group_members.set(validated_data["group_members"])
        return group

    def update(self, instance, validated_data):
        instance.is_public = validated_data.get('is_public', instance.is_public)
        instance.group_admins = validated_data.get('group_admins', instance.group_admins)
        instance.group_members = validated_data.get('group_members', instance.group_members)
        instance.save()
        return instance

class EnhancedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnhancedUser
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField('get_first_name')
    last_name = serializers.SerializerMethodField('get_last_name')
    public_profile = serializers.SerializerMethodField('get_public_profile')
    real_name = serializers.SerializerMethodField('get_real_name')

    def get_additional_data(self, instance):
        return instance.additional_user_data.all()[0]

    def get_first_name(self, instance):
        additional_data = self.get_additional_data(instance)
        if self.context['request'].user == instance or additional_data.real_name:
            return instance.first_name
        else:
            return None

    def get_last_name(self, instance):
        additional_data = self.get_additional_data(instance)
        if self.context['request'].user == instance or additional_data.real_name:
            return instance.last_name
        else:
            return None

    def get_public_profile(self, instance):
        additional_data = self.get_additional_data(instance)
        return additional_data.public_profile

    def get_real_name(self, instance):
        additional_data = self.get_additional_data(instance)
        return additional_data.real_name

    class Meta:
        model = User
        fields = ('username', 'email', 'id', 'first_name', 'last_name', 'public_profile', 'real_name')
        read_only_fields = ['id']
        extra_kwargs = {
            'password': {'required': False, 'write_only':True},
            'username': {'required': False},
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'public_profile': {'required': False},
            'real_name': {'required': False},
        }

    def validate(self, data):
        unvalidated_data = self.context['request'].data
        unvalidated_data.update(data)
        # Owner will be set by the requesting user. If it is set, remove it
        if 'owner' in unvalidated_data:
            unvalidated_data.pop('owner')
        return unvalidated_data

    def validate_create(self, data):
        """Validation step required on creation only."""
        if 'username' not in data:
            raise ValueError("Username required")
        if 'password' not in data:
            raise ValueError("Passwort required")
        return data

    def create(self, validated_data):
        validated_data = self.validate_create(validated_data)
        user = User.objects.create_user(username=validated_data['username'], password=validated_data['username'], email=validated_data.get('email'))
        user.first_name = validated_data.get('first_name', "")
        user.last_name = validated_data.get('last_name', "")
        return user

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.username = validated_data.get('username', instance.username)
        additional_user_data = instance.additional_user_data.all()[0]
        additional_user_data.public_profile = validated_data.get('public_profile', additional_user_data.public_profile)
        additional_user_data.real_name = validated_data.get('real_name', additional_user_data.public_profile)
        #FIXME: How to do cascading saves, this is a potential threat to data integrity if only one save() is successful without rollback
        additional_user_data.save()
        instance.save()
        return instance