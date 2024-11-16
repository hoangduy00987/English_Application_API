
from django.urls import path,include
from .views import *

urlpatterns = [
    path('user/', include('api.login.urls')),
    path('vocabulary/', include('api.vocabulary.urls')),
    path('activity/', include('api.activity.urls')),
    path('listening/', include('api.listening.urls')),
]
