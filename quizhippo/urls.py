from django.urls import path
from .views import LoginView, RegisterView, LogoutView, GenerateQuizAPI, chat_assistant

urlpatterns = [
    path("login-view/", LoginView.as_view(), name="login-view"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout-view/", LogoutView.as_view(), name="logout-view"),
    path('generate-quiz/', GenerateQuizAPI.as_view(), name='generate_quiz_api'),
    path('chat/', chat_assistant, name='chat-assistant'),
]
