from rest_framework import serializers
from .models import *
from base64 import b64decode
from uuid import uuid4
from pathlib import Path
from django.contrib.auth.models import AnonymousUser

class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = '__all__'

class DatasourceSerializer(serializers.Serializer):
    scope_path = serializers.CharField(max_length=256)
    url = serializers.URLField(required=False)
    data = serializers.CharField(required=False)

    def validate(self, data):
        if 'scope_path' not in data:
            raise serializers.ValidationError("No scope_path specified")
        if 'url' not in data and 'data' not in data:
            raise serializers.ValidationError("Neither data nor url specified")
        if type(self.context['request'].user) == AnonymousUser:
            raise serializers.ValidationError("No Owner specified, this should have been caught before")
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
