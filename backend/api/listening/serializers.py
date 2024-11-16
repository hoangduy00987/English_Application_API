from rest_framework import serializers
from ..submodels.models_listening import *


class ListeningTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListeningTopic
        fields = ['id', 'name', 'image']

class UserListeningTopicSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = ListeningTopic
        fields = ['id', 'name', 'image', 'is_completed']
    
    def get_is_completed(self, obj):
        user = self.context['request'].user
        user_topic_progress = UserListeningTopicProgress.objects.filter(user=user, listening_topic=obj.id).first()
        if user_topic_progress:
            return True
        return False

class ListeningExerciseSerializer(serializers.ModelSerializer):
    audio_file = serializers.SerializerMethodField()

    class Meta:
        model = ListeningExercise
        fields = ['id', 'name', 'audio_file', 'transcript']
    
    def get_audio_file(self, obj):
        request = self.context.get('request')
        if obj.audio_file:
            return request.build_absolute_uri(obj.audio_file.url)
        return None

class UserListeningExerciseResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserListeningExerciseResult
        fields = ['id', 'listening_exercise', 'is_done', 'retries_count']

class UserListeningExerciseManagerSerializer(serializers.ModelSerializer):
    exercise_id = serializers.IntegerField(required=True)
    class Meta:
        model = UserListeningExerciseResult
        fields = ['id', 'exercise_id']
    
    def save(self, request):
        try:
            exercise_id = self.validated_data['exercise_id']
            exercise = ListeningExercise.objects.get(pk=exercise_id)
            return UserListeningExerciseResult.objects.create(
                user=request.user,
                listening_exercise=exercise,
                is_done=True
            )
        except Exception as error:
            print("UserListeningExerciseManagerSerializer_save_error:", error)
            return None
