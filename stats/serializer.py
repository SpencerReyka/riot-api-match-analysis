from rest_framework import serializers
from stats.django_models import RiotAccount


class RiotAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiotAccount
        fields = '__all__'