from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..submodels.models_activity import Streak, LearningActivity
from .serializers import *

class UserStreakView(APIView):
    serializer_class = UserStreakSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            streak = Streak.objects.get(user=user)
            serializer = self.serializer_class(streak)
            return Response(serializer.data)
        except Exception as error:
            print("get_user_streak_error:", error)
            return Response({
                "error": str(error)
            }, status=status.HTTP_400_BAD_REQUEST)

class CompleteActivityView(APIView):
    serializer_class = LearningActivitySerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(request)
                return Response({
                    "message": "Activity completed and streak updated."
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("complete_activity_error:", error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
