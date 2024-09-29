
from django.urls import path,include
from .views import *

urlpatterns = [
    path('user/', include('api.login.urls')),
]
