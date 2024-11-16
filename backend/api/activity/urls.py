from django.urls import path
from .views import *

urlpatterns = [
    path('get_user_streak/', UserStreakView.as_view(), name='get_user_streak'),
    path('complete_learning_activity/', CompleteActivityView.as_view(), name='complete_learning_activity'),
]
