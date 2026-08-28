from rest_framework import serializers


class CourseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=200)
    credits = serializers.IntegerField()