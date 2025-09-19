from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
# Create your views here.
def index(request):
    return render(request, 'index.html')

def handle_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('main')
        else:
            # return render(request, 'login.html', {'error': 'Invalid username or password'})
            return HttpResponse('Invalid credentials! Please try again')    
    return render(request, 'login.html')

def handle_signup(request):
    if request.method == 'POST':
        user = User.objects.create_user(
            username=request.POST.get('username'),
            password = request.POST.get('password'),
            email=request.POST.get('email'),
            first_name=request.POST.get('f_name'),
            last_name=request.POST.get('l_name')
        )
        user.save()
        return redirect('login.html')
    return render(request, 'signup.html')


def main(request):
    return render(request, 'main.html')