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
        read_only_fields = ['chart_name', 'id', 'owner', 'original_datasource']
        extra_kwargs = {
            'config': {'required': False},
            'downloadable': {'required': False},
            'visibility': {'required': False},
            'scope_path': {'required': False},
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
        if 'datasource' not in data:
            raise serializers.ValidationError("Datasource is required for chart creation")
        if 'chart_name' not in data:
            raise serializers.ValidationError("Chart type must be given")
        if 'scope_path' not in data:
            raise serializers.ValidationError("Scope path must be given")
        if self.context['request'].user == None or type(self.context['request'].user) == AnonymousUser:
            raise serializers.ValidationError("Only users may create Charts")

        # FIXME: Read base path from config
        supported = get_chart_types_for_datasource(data["datasource"])
        if data["chart_name"] not in supported:
            raise serializers.ValidationError(f"Chart type not supported for this datasource. Supported types are: {supported}")
        return data

    def create(self, validated_data):
        validated_data = self.validate_create(validated_data)
        user = self.context['request'].user
        # TODO: How to handle shares during creation? Ignore and keep sharing a separate action?
        chart = Chart.objects.create(
            chart_name=validated_data['chart_name'],
            scope_path=validated_data['scope_path'],
            owner=user,
            original_datasource=validated_data['datasource'],
            downloadable=validated_data.get('downloadable',False),
            visibility=validated_data.get('visibility', Chart.VISIBILITY_PRIVATE)
        )
        try:
            base_path = get_chart_base_path()
            base_path.mkdir(exist_ok=True)
            generate_chart(datasource=validated_data["datasource"], chart_id=chart.id, chart_type=validated_data["chart_name"], output_path=base_path.joinpath(f"{chart.id}"), request=self.context['request'], config=validated_data["config"])
        except Exception as e:
            # Remove stale db entry and reraise exception
            chart.delete()
            raise e
        return chart

    def update(self, instance, validated_data):
        instance.scope_path = validated_data.get('scope_path', instance.scope_path)
        instance.downloadable = validated_data.get('downloadable', instance.downloadable)
        instance.visibility = validated_data.get('visibility', instance.visibility)

        base_path = get_chart_base_path()
        base_path.mkdir(exist_ok=True)
        modify_chart(chart_id=instance.id, output_path=base_path.joinpath(f"{instance.id}"), request=self.context['request'], config=validated_data.get('config',None))

        instance.save()
        return instance


class DatasourceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Datasource
        fields = '__all__'
        extra_kwargs = {
            'source': {'required': False, 'read_only': True},
            'owner': {'required': False, 'read_only': True},
            'scope_path': {'required': False},
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
        if 'scope_path' not in data:
            raise serializers.ValidationError("No scope_path specified")
        if 'url' not in data and 'data' not in data:
            raise serializers.ValidationError("Neither data nor url specified")
        if 'url' in data and 'data' in data:
            raise serializers.ValidationError("data and url must not be used together")
        if 'url' in data:
            #TODO: Validate URL here
            pass
        else:
            #TODO: Validate actual data here:
            pass
        if self.context['request'].user == None or type(self.context['request'].user) == AnonymousUser:
            raise serializers.ValidationError("Only users may create Charts")
        return data

    def create(self, validated_data):
        validated_data = self.validate_create(validated_data)
        user = self.context['request'].user
        #TODO: How to handle shares during creation? Ignore and keep sharing a separate action?
        if 'url' in validated_data:
            datasource = Datasource.objects.create(source=validated_data['url'], scope_path=validated_data['scope_path'], owner=user)
        else:
            data = b64decode(validated_data['data'])
            file_path = get_datasource_base_path().joinpath(uuid4().hex)
            with file_path.open("w") as file:
                file.write(data.decode('utf-8'))
            datasource = Datasource.objects.create(source=file_path, scope_path=validated_data['scope_path'], owner=user)
        return datasource

    def update(self, instance, validated_data):
        instance.scope_path = validated_data.get('scope_path', instance.scope_path)
        instance.save()
        return instance

class EnhancedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnhancedUser
        fields = '__all__'

class EnhancedGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnhancedGroup
        fields = '__all__'
