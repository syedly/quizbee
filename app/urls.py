from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.handle_login, name='login'),
    path('signup/', views.handle_signup, name='signup'),
    path('main/', views.main, name='main'),
    path('generate_quiz/', views.generate_quiz, name='generate_quiz'),
    path('all_quizes/', views.all_quizes, name='all_quizes'),
    path("quiz_detail/<int:quiz_id>/", views.quiz_detail, name="quiz_detail"),
    path("quiz/<int:quiz_id>/", views.quiz_take, name="quiz_take"),
    path("quiz/result/<int:attempt_id>/", views.quiz_result, name="quiz_result"),
    path('logout/', views.handle_logout, name='logout'),
    path('delete_quiz/<int:quiz_id>/', views.delete_quiz, name='delete_quiz'),
    path("quiz/<int:quiz_id>/share/", views.share_quiz, name="share_quiz"),
    path('retake_quiz/<int:quiz_id>/', views.retake_quiz, name='retake_quiz'),
    path('settings/', views.settings, name='settings'),
    path("quiz/<int:quiz_id>/is-public/", views.is_public, name="is_public"),

]
