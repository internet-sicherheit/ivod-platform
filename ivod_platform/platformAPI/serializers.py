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
        read_only_fields = ['chart_type', 'id', 'owner', 'original_datasource']
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
        extra_kwargs = {
            'source': {'required': False, 'read_only': True},
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
            datasource = Datasource.objects.create(source=validated_data['url'], datasource_name=validated_data['datasource_name'], owner=user)
        else:
            data = b64decode(validated_data['data'])
            file_path = get_datasource_base_path().joinpath(uuid4().hex)
            with file_path.open("w") as file:
                file.write(data.decode('utf-8'))
            datasource = Datasource.objects.create(source=file_path, datasource_name=validated_data['datasource_name'], owner=user)
        return datasource

    def update(self, instance, validated_data):
        instance.datasource_name = validated_data.get('datasource_name', instance.datasource_name)
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
