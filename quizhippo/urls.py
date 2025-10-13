from django.urls import path
from .views import (
    LoginView, RegisterView, 
    LogoutView, GenerateQuizAPI, 
    chat_assistant, UpdatePreferencesAPIView, 
    AllQuizzesAPIView, CheckQuizAttempt,
    DeleteAccount, QuizVisibilityAPI,
    ChangePassword, DeleteQuiz,
    ExploreQuizzesAPI, ChangeUsernameOrEmailAPIView,
    RateQuizAPI, AddToMyQuizAPI,
    ProfileAPIView, ShareQuizAPIView
    )

urlpatterns = [
    path("login-view/", LoginView.as_view(), name="login-view"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout-view/", LogoutView.as_view(), name="logout-view"),
    path('generate-quiz/', GenerateQuizAPI.as_view(), name='generate-quiz'),
    path('chat/', chat_assistant, name='chat-assistant'),
    path("preferences/update/", UpdatePreferencesAPIView.as_view(), name="update-preferences"),
    path('all-quizzes/', AllQuizzesAPIView.as_view(), name='all-quizzes'),
    path("delete-account/", DeleteAccount.as_view(), name="delete-account"),
    path("change-pwd/", ChangePassword.as_view(), name="change-pwd"),
    path("quiz/<int:quiz_id>/delete/", DeleteQuiz.as_view(), name="delete_quiz"),
    path("quiz/attempts/", CheckQuizAttempt.as_view(), name="check_quiz_attempts"),
    path("quiz/<int:quiz_id>/visibility/", QuizVisibilityAPI.as_view(), name="quiz_visibility"),
    path("explore/", ExploreQuizzesAPI.as_view(), name="explore_quizzes"),
    path("explore/<str:filter_type>/", ExploreQuizzesAPI.as_view(), name="explore_quizzes_filtered"),
    path("update-profile/", ChangeUsernameOrEmailAPIView.as_view(), name="update_profile"),
    path("quizzes/<int:quiz_id>/rate/", RateQuizAPI.as_view(), name="rate-quiz"),
    path("quizzes/<int:quiz_id>/save/", AddToMyQuizAPI.as_view(), name="add-to-my-quiz"),
    path('profile/', ProfileAPIView.as_view(), name='profile-api'),
    path('share-quiz/<int:quiz_id>/', ShareQuizAPIView.as_view(), name='share-quiz'),
]
