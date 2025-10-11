from django.urls import path
from .views import (
    LoginView, RegisterView, 
    LogoutView, GenerateQuizAPI, 
    chat_assistant, UpdatePreferencesAPIView, 
    AllQuizzesAPIView, AddQuizToServerView,
    )

urlpatterns = [
    path("login-view/", LoginView.as_view(), name="login-view"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout-view/", LogoutView.as_view(), name="logout-view"),
    path('generate-quiz/', GenerateQuizAPI.as_view(), name='generate_quiz_api'),
    path('chat/', chat_assistant, name='chat-assistant'),
    path("preferences/update/", UpdatePreferencesAPIView.as_view(), name="update-preferences"),
    path('all-quizzes/', AllQuizzesAPIView.as_view(), name='all-quizzes'),
    path("servers/<int:server_id>/add-quiz/", AddQuizToServerView.as_view(), name="add-quiz-to-server"),
]
