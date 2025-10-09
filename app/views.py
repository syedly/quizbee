# quizapp/views.py
import re
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from services import generate__quiz, check_short_answer, assistant, check_multiple_choice
from processing import fetch_text_from_url, extract_text_from_pdf, incorrect_answer, parse_quiz_response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Max
from django.db.models import Avg
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import (
    Quiz, Question, 
    Option, QuizAttempt, 
    UserProfile, QuizRating, 
    Server, ServerQuiz
)
from constants import (
    LANGUAGES, DEFAULT_LANGUAGE,
    DIFFICULTY_LEVELS, DEFAULT_DIFFICULTY,
    QUESTION_TYPES, DEFAULT_QUESTION_TYPE,
    CHOOSE_OPTIONS, DEFAULT_CHOOSE, QUIZ_CATEGORIES
)

def index(request):
    return render(request, 'index.html')

def delete_account(request):
    user = request.user
    user.delete()
    return redirect("index")

def handle_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('main')
        else:
            return HttpResponse('Invalid credentials! Please try again')
    return render(request, 'login.html')

def profile(request):
    servers = Server.objects.filter(created_by=request.user)
    quizzes_created = Quiz.objects.filter(user=request.user).count()
    quizzes_completed = QuizAttempt.objects.filter(user=request.user).count()
    best_score = QuizAttempt.objects.filter(user=request.user).aggregate(
        Max('score')
    )['score__max'] or 0

    # ✅ Fetch attempts for quizzes in the user's servers
    server_quizzes = ServerQuiz.objects.filter(server__in=servers).values_list('quiz', flat=True)
    attempts = QuizAttempt.objects.filter(quiz__in=server_quizzes).select_related('user', 'quiz')

    return render(request, 'profile.html', {
        'servers': servers,
        'attempts': attempts,  # ✅ added context
        'quizzes_created': quizzes_created,
        'quizzes_completed': quizzes_completed,
        'best_score': f"{best_score}%",
    })

def change_username_or_email(request):
    if request.method == "POST":
        new_username = request.POST.get("new_username", "").strip()
        new_email = request.POST.get("new_email", "").strip()
        profile_image = request.FILES.get("profile_image")  # 👈 Handle image

        # Update username
        if new_username:
            if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
                return HttpResponse("Username already taken!", status=400)
            request.user.username = new_username

        if new_email:
            if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                return HttpResponse("Email already in use!", status=400)
            request.user.email = new_email

        request.user.save()

        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if profile_image:
            profile.avatar = profile_image
            profile.save()

        return HttpResponse("Profile updated successfully.")

    return redirect("settings")

def handle_signup(request):
    if request.method == 'POST':
        user = User.objects.create_user(
            username=request.POST.get('username'),
            password=request.POST.get('password'),
            email=request.POST.get('email'),
            first_name=request.POST.get('f_name'),
            last_name=request.POST.get('l_name')
        )
        user.save()
        return redirect('login')
    return render(request, 'signup.html')

@csrf_exempt
def chat_assistant(request):
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        if query:
            response = assistant(query)
            return JsonResponse({"response": response})
    return JsonResponse({"error": "Invalid request"}, status=400)

def handle_logout(request):
    logout(request)
    return redirect('index')

def settings(request):
    return render(request, 'settings.html')

def is_public(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, user=request.user)
    if request.method == "POST":
        is_public = request.POST.get("is_public") == "on"
        quiz.is_public = is_public
        quiz.save()
        return redirect("all_quizes")

def main(request):
    quizzes = Quiz.objects.filter(user=request.user)

    return render(
        request,
        'main.html',
        {
            'quizzes': quizzes,

            'languages': LANGUAGES,
            'default_language': DEFAULT_LANGUAGE,

            'levels': DIFFICULTY_LEVELS,
            'default_level': DEFAULT_DIFFICULTY,

            'question_types': QUESTION_TYPES,
            'default_type': DEFAULT_QUESTION_TYPE,

            'choose_options': CHOOSE_OPTIONS,
            'default_choose': DEFAULT_CHOOSE,
        }
    )

def all_quizes(request):
    user = request.user
    quizzes = (Quiz.objects.filter(user=user) | Quiz.objects.filter(shared_with=user)).distinct()

    for quiz in quizzes:
        attempt = QuizAttempt.objects.filter(user=user, quiz=quiz).first()
        quiz.attempt = attempt
        quiz.attempted = attempt is not None

    paginator = Paginator(quizzes, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'all-quizes.html', {'page_obj': page_obj})


def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_new_password")

        if not request.user.check_password(current_password):
            return HttpResponse("Current password is incorrect!", status=400)

        if new_password != confirm_password:
            return HttpResponse("New passwords do not match!", status=400)

        request.user.set_password(new_password)
        request.user.save()

        return HttpResponse("Password changed successfully. Please log in again.")

    return redirect("settings")

def delete_server(request, server_id):
    server = get_object_or_404(Server, id=server_id)
    if request.user == server.created_by:
        server.delete()
    return redirect("profile")

def show_members(request, server_id):
    server = get_object_or_404(Server, id=server_id)
    members = server.members.all()
    return render(request, 'profile.html', {'server': server, 'members': members})


def show_server_quiz_results(request, server_id):
    # Get server created by the current user (only server owner can view)
    server = get_object_or_404(Server, id=server_id, created_by=request.user)

    # Get quizzes assigned to this server
    server_quizzes = ServerQuiz.objects.filter(server=server).select_related('quiz')

    # Get all members of the server
    members = server.members.all()

    # Create a structured data dictionary
    results_data = []

    for sq in server_quizzes:
        quiz = sq.quiz

        # Get attempts made by members for this quiz
        attempts = QuizAttempt.objects.filter(quiz=quiz, user__in=members).select_related('user')

        # Append quiz + attempts info
        results_data.append({
            "quiz": quiz,
            "attempts": attempts
        })

    return render(request, "server_results.html", {
        "server": server,
        "results_data": results_data,
    })


def delete_quiz(request, **kwargs):
    quiz_id = kwargs.get("quiz_id")
    user = request.user
    quiz = get_object_or_404(Quiz, id=quiz_id, user=user)
    quiz.delete()
    return redirect("all_quizes")

def share_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, user=request.user)

    if request.method == "POST":
        username = request.POST.get("username")
        try:
            user_to_share = User.objects.get(username=username)
            quiz.shared_with.add(user_to_share) 
        except User.DoesNotExist:
            return HttpResponse(f"User '{username}' does not exist!")

        return redirect("all_quizes")

    return redirect("all_quizes")

def generate_quiz(request):
    if request.method == 'POST':
        topic = request.POST.get('topic', 'General')
        language = request.POST.get('language', 'English')
        num_questions = int(request.POST.get('quiz_count', 5))
        difficulty = request.POST.get('difficulty', '1')
        question_preference = request.POST.get('quiz_type', 'MIX').upper()
        category = request.POST.get('category', 'General')  # ✅ new field
        prompt = request.POST.get('input_prompt', '').strip()
        url = request.POST.get('input_url', '').strip()
        text = request.POST.get('input_text', '').strip()
        upload_file = request.FILES.get('input_pdf')

        # Detect source
        if prompt:
            content_source = prompt
        elif url:
            content_source = fetch_text_from_url(url)
        elif text:
            content_source = text
        elif upload_file and upload_file.name.endswith(".pdf"):
            content_source = extract_text_from_pdf(upload_file)
        else:
            content_source = topic

        raw_quiz = generate__quiz(
            topic=topic,
            language=language,
            num_questions=num_questions,
            difficulty=difficulty,
            question_type=question_preference,
            content=content_source
        )

        parsed_quiz = parse_quiz_response(raw_quiz)

        quiz = Quiz.objects.create(
            topic=parsed_quiz.get("topic", topic),
            difficulty=parsed_quiz.get("difficulty", difficulty),
            category=parsed_quiz.get("category", "General"),
            question_preference=question_preference,  # ✅ keep user’s choice
            user=request.user if request.user.is_authenticated else None,
        )

        for q in parsed_quiz["questions"]:
            question = Question.objects.create(
                quiz=quiz,
                text=q["text"],
                question_type=q["type"].upper(),
                difficulty=q["difficulty"],
                answer=q["answer"]
            )

            if q["type"].upper() == "MCQ" and q.get("mcq_options"):
                for opt in q["mcq_options"]:
                    Option.objects.create(question=question, text=opt.strip())

        quizzes = Quiz.objects.all().order_by('-id')[:20]
        context = {

            'languages': LANGUAGES,
            'default_language': DEFAULT_LANGUAGE,

            'levels': DIFFICULTY_LEVELS,
            'default_level': DEFAULT_DIFFICULTY,

            'question_types': QUESTION_TYPES,
            'default_type': DEFAULT_QUESTION_TYPE,

            'choose_options': CHOOSE_OPTIONS,
            'default_choose': DEFAULT_CHOOSE,
        }
        return render(request, 'main.html', {'quizzes': quizzes, 'created_quiz': quiz, **context})

    return redirect('main')

def quiz_detail(request, quiz_id):
    quiz  = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    return render(request, 'quiz-detail.html', {'quiz': quiz, 'questions': questions}) 


def quiz_take(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()

    if request.method == "POST":
        marks = 0
        user_answers = {}

        for question in questions:
            user_answer = request.POST.get(str(question.id))  
            user_answers[str(question.id)] = user_answer

            if question.question_type == "SHORT":
                if user_answer and check_short_answer(user_answer, question.answer):
                    marks += 1
            if question.question_type == "MCQ":
                if user_answer and check_multiple_choice(user_answer, question.answer):
                    marks += 1
            if user_answer and user_answer.strip().lower() == question.answer.strip().lower():
                marks += 1

        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score=marks,
            answers=user_answers
        )

        return redirect("quiz_result", attempt_id=attempt.id)

    return render(request, "quiz-take.html", {"quiz": quiz, "questions": questions})

def quiz_result(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id)
    quiz = attempt.quiz

    incorrect = incorrect_answer(quiz, attempt)

    return render(request, "quiz-result.html", {
        "attempt": attempt,
        "quiz": quiz,
        "incorrect": incorrect,
    })

# def quiz_result(request, attempt_id):
#     attempt = get_object_or_404(QuizAttempt, id=attempt_id)
#     quiz = attempt.quiz
#     return render(request, "quiz-result.html", {"attempt": attempt, "quiz": quiz})

def quiz_list(request):
    user = request.user
    quizzes = Quiz.objects.all()

    attempted_quizzes = QuizAttempt.objects.filter(user=user).values_list("quiz_id", flat=True)

    for quiz in quizzes:
        quiz.attempted = quiz.id in attempted_quizzes 

    return render(request, "quiz_list.html", {"quizzes": quizzes})

def retake_quiz(request, quiz_id):
    user = request.user
    quiz = get_object_or_404(Quiz, id=quiz_id)

    attempt, created = QuizAttempt.objects.get_or_create(user=user, quiz=quiz)

    if request.method == "POST":
        questions = quiz.questions.all()
        marks = 0
        user_answers = {}

        for question in questions:
            user_answer = request.POST.get(str(question.id))
            user_answers[str(question.id)] = user_answer

            if question.question_type == "SHORT":
                if user_answer and check_short_answer(user_answer, question.answer):
                    marks += 1
            elif user_answer and user_answer.strip().lower() == question.answer.strip().lower():
                marks += 1

        attempt.score = marks
        attempt.answers = user_answers
        attempt.save()

        return redirect("quiz_result", attempt_id=attempt.id)
    return render(request, "quiz-take.html", {"quiz": quiz, "questions": quiz.questions.all()})

def explore(request, filter_type=None):
    quizzes = Quiz.objects.filter(is_public=True).annotate(
        avg_rating=Avg('ratings__rating')
    )

    category = request.GET.get("category")
    difficulty = request.GET.get("difficulty")

    # Apply category and difficulty filters
    if category:
        quizzes = quizzes.filter(category__iexact=category)
    if difficulty:
        quizzes = quizzes.filter(difficulty=difficulty)

    # 👇 Apply "Trending" filter if selected
    if filter_type == "trending":
        quizzes = quizzes.filter(avg_rating__gt=3.5)
        active_filter = "trending"
    else:
        active_filter = "explore"

    return render(request, "explore.html", {
        "quizzes": quizzes,
        "categories": QUIZ_CATEGORIES,
        "difficulty_levels": DIFFICULTY_LEVELS,
        "selected_category": category,
        "selected_difficulty": difficulty,
        "active_filter": active_filter,
    })

def rate_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.method == "POST":
        rating_value = int(request.POST.get("rating", 0))

        if 1 <= rating_value <= 5:
            QuizRating.objects.update_or_create(
                quiz=quiz,
                user=request.user,
                defaults={"rating": rating_value},
            )

    return redirect("explore")

def add_to_my_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    if request.user in quiz.shared_with.all():
        pass
    else:
        quiz.shared_with.add(request.user)
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def server_list(request):
    user_servers = request.user.joined_servers.all()
    return render(request, 'server_list.html', {'servers': user_servers})

@login_required
def create_server(request):
    if request.method == "POST":
        name = request.POST.get("name")
        desc = request.POST.get("description")
        server = Server.objects.create(name=name, description=desc, created_by=request.user)
        server.members.add(request.user)
        messages.success(request, f"Server '{name}' created successfully! Code: {server.code}")
        return redirect("server_list")
    return render(request, 'create_server.html')

@login_required
def join_server(request):
    if request.method == "POST":
        code = request.POST.get("code").strip().upper()
        try:
            server = Server.objects.get(code=code)
            server.members.add(request.user)
            messages.success(request, f"Joined {server.name} successfully!")
            return redirect("server_detail", server.id)
        except Server.DoesNotExist:
            messages.error(request, "Invalid code!")
    return redirect("server_list")

@login_required
def server_detail(request, server_id):
    quizes = Quiz.objects.filter(user=request.user)  
    attempted_quiz = QuizAttempt.objects.filter(user=request.user).values_list("quiz_id", flat=True)
    server = get_object_or_404(Server, id=server_id)
    quizzes = server.quizzes.all()
    return render(request, 'server_detail.html', {'server': server, 'quizzes': quizzes, 'quizes': quizes, 'attempted_quiz': attempted_quiz})

def add_quiz_to_server(request, server_id):
    server = get_object_or_404(Server, id=server_id)

    if request.user != server.created_by:
        return redirect("server_detail", server_id=server.id)

    if request.method == "POST":
        quiz_id = request.POST.get("quiz_id")
        quiz = get_object_or_404(Quiz, id=quiz_id)
        ServerQuiz.objects.create(server=server, quiz=quiz)
        return redirect("server_detail", server_id=server.id)

def update_prefrences(request):
    if request.method == "POST":
        light_mode = request.POST.get("light_mode") == "on"

        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.light_mode = light_mode
        profile.save()

        return redirect("settings")
    return redirect("settings")
