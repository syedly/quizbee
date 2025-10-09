from django.urls import path
from .views import LoginView, RegisterView

urlpatterns = [
    path("login-view/", LoginView.as_view(), name="login-view"),
    path("register/", RegisterView.as_view(), name="register"),

]
