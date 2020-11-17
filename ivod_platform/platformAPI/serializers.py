from  rest_framework.serializers import ModelSerializer
from .models import *

class ChartSerializer(ModelSerializer):
    class Meta:
        model = Chart
        fields = '__all__'

class DatasourceSerializer(ModelSerializer):
    class Meta:
        model = Datasource
        fields = '__all__'

class EnhancedUserSerializer(ModelSerializer):
    class Meta:
        model = EnhancedUser
        fields = '__all__'

class EnhancedGroupSerializer(ModelSerializer):
    class Meta:
        model = EnhancedGroup
        fields = '__all__'
