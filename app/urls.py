from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.handle_login, name='login'),
    path('signup/', views.handle_signup, name='signup'),
    path('main/', views.main, name='main'),
    path('generate_quiz/', views.generate_quiz, name='generate_quiz'),
    path('all_quizes/', views.all_quizes, name='all_quizes'),
]
