# quizapp/views.py
import re
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from services import generate__quiz, check_short_answer
from processing import fetch_text_from_url, extract_text_from_pdf
from .models import Quiz, Question, Option, QuizAttempt
from constants import (
    LANGUAGES, DEFAULT_LANGUAGE,
    DIFFICULTY_LEVELS, DEFAULT_DIFFICULTY,
    QUESTION_TYPES, DEFAULT_QUESTION_TYPE,
    CHOOSE_OPTIONS, DEFAULT_CHOOSE
)


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
            return HttpResponse('Invalid credentials! Please try again')
    return render(request, 'login.html')

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

def handle_logout(request):
    logout(request)
    return redirect('index')

def main(request):
    quizzes = Quiz.objects.filter(user=request.user)

    return render(
        request,
        'main.html',
        {
            'quizzes': quizzes,

            # languages
            'languages': LANGUAGES,
            'default_language': DEFAULT_LANGUAGE,

            # difficulty levels
            'levels': DIFFICULTY_LEVELS,
            'default_level': DEFAULT_DIFFICULTY,

            # question types
            'question_types': QUESTION_TYPES,
            'default_type': DEFAULT_QUESTION_TYPE,

            # choose options
            'choose_options': CHOOSE_OPTIONS,
            'default_choose': DEFAULT_CHOOSE,
        }
    )

# def all_quizes(request):
#     user = request.user
#     quizzes = Quiz.objects.all()  # show all quizzes

#     # Get all quiz IDs that the user has attempted
#     attempted_quizzes = QuizAttempt.objects.filter(user=user).values_list("quiz_id", flat=True)

#     # Attach attempted flag
#     for quiz in quizzes:
#         quiz.attempted = quiz.id in attempted_quizzes

#     return render(request, 'all-quizes.html', {'quizzes': quizzes})

# def all_quizes(request):
#     user = request.user
#     quizzes = Quiz.objects.filter(user=user) | Quiz.objects.filter(shared_with=user)

#     for quiz in quizzes:
#         attempt = QuizAttempt.objects.filter(user=user, quiz=quiz).first()
#         quiz.attempt = attempt   # attach attempt (or None)
#         quiz.attempted = attempt is not None

#     return render(request, 'all-quizes.html', {'quizzes': quizzes})


def all_quizes(request):
    user = request.user
    quizzes = Quiz.objects.filter(user=user) | Quiz.objects.filter(shared_with=user)

    for quiz in quizzes:
        attempt = QuizAttempt.objects.filter(user=user, quiz=quiz).first()
        quiz.attempt = attempt
        quiz.attempted = attempt is not None

    paginator = Paginator(quizzes, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'all-quizes.html', {'page_obj': page_obj})


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
            quiz.shared_with.add(user_to_share)  # add user to shared list
        except User.DoesNotExist:
            return HttpResponse(f"User '{username}' does not exist!")

        return redirect("all_quizes")

    return redirect("all_quizes")

# -----------------------------
# Parser / save helpers
# -----------------------------
def parse_quiz_response(response_text):
    response_text = (response_text or "").strip()

    # Topic + global difficulty
    topic_match = re.search(r"Topic:\s*(.+?)\s*\(Difficulty\s*(\d+)\)", response_text, re.IGNORECASE)
    topic = topic_match.group(1).strip() if topic_match else "Untitled Quiz"
    quiz_difficulty = int(topic_match.group(2)) if topic_match else 1

    # Questions block
    questions_part = ""
    answers_part = ""
    difficulty_part = ""
    if "Questions:" in response_text and "Answers:" in response_text:
        try:
            questions_part = response_text.split("Questions:")[1].split("Answers:")[0].strip()
            answers_part = response_text.split("Answers:")[1]
            if "Question Difficulty Levels:" in answers_part:
                answers_part, difficulty_part = answers_part.split("Question Difficulty Levels:")
                answers_part = answers_part.strip()
                difficulty_part = difficulty_part.strip()
            else:
                answers_part = answers_part.strip()
        except Exception:
            questions_part = ""
            answers_part = ""

    # split question blocks by numbered lines (1., 2., etc.)
    question_blocks = re.split(r"\n\s*\d+\.\s*", questions_part)
    if question_blocks and question_blocks[0].strip() == "":
        question_blocks = question_blocks[1:]

    # parse answers
    answers = re.findall(r"\d+\.\s*(.+)", answers_part) if answers_part else []
    # fallback: sometimes answers are like "1. (b) 4"
    if not answers and answers_part:
        answers = [line.strip() for line in answers_part.splitlines() if line.strip()]

    # parse difficulties per question
    difficulties = {}
    if difficulty_part:
        for line in difficulty_part.splitlines():
            m = re.search(r"Q\s*(\d+)\s*[^0-9]*\s*:?(\d+)", line) or re.search(r"(\d+)\.\s*Q\d+\s*→\s*Difficulty:\s*(\d+)", line)
            if not m:
                m = re.search(r"Q(\d+)\s*→\s*Difficulty:\s*(\d+)", line)
            if m:
                try:
                    q_idx = int(m.group(1))
                    q_diff = int(m.group(2))
                    difficulties[q_idx] = q_diff
                except Exception:
                    pass

    parsed_questions = []
    for idx, q_text in enumerate(question_blocks, start=1):
        text = q_text.strip()
        if not text:
            continue

        # Detect MCQ options within the question block: lines starting with (a), (b) or "a)" style
        mcq_option_pattern = r"(?:\([a-z]\)|[a-z]\))\s*([^\n\r]+)"
        mcq_options = re.findall(mcq_option_pattern, text, flags=re.IGNORECASE)

        # Determine type
        if re.search(r"True or False|True/False|True or false", text, re.IGNORECASE):
            q_type = "TF"
        elif mcq_options:
            q_type = "MCQ"
        elif re.search(r"_{3,}|____|blank", text, re.IGNORECASE):
            q_type = "FILL"
        else:
            q_type = "SHORT"

        # Clean question text: remove option lines if MCQ
        if q_type == "MCQ":
            # split question text and options
            parts = re.split(r"(?:\n|\r\n)", text)
            # keep lines that are not the option lines for question text
            non_option_lines = [p for p in parts if not re.match(r"^\s*(?:\([a-z]\)|[a-z]\))", p, re.IGNORECASE)]
            question_text_clean = " ".join(non_option_lines).strip()
        else:
            question_text_clean = text

        answer_text = ""
        if idx-1 < len(answers):
            answer_text = answers[idx-1].strip()
        parsed_questions.append({
            "text": question_text_clean,
            "raw_text": text,            # raw block (useful for options)
            "type": q_type,
            "answer": answer_text,
            "difficulty": difficulties.get(idx, quiz_difficulty),
            "mcq_options": mcq_options
        })

    return {
        "topic": topic,
        "difficulty": quiz_difficulty,
        "questions": parsed_questions
    }

def save_quiz_to_db(parsed_quiz):
    quiz = Quiz.objects.create(
        topic=parsed_quiz["topic"],
        difficulty=parsed_quiz["difficulty"]
    )

    for q in parsed_quiz["questions"]:
        question = Question.objects.create(
            quiz=quiz,
            text=q["text"],
            question_type=q["type"],
            difficulty=q["difficulty"],
            answer=q["answer"]
        )

        # Save options found by parser (preferred)
        if q["type"] == "MCQ" and q.get("mcq_options"):
            for opt in q["mcq_options"]:
                Option.objects.create(question=question, text=opt.strip())
        else:
            # fallback: try to extract (a) (b) lines from raw_text if any
            opts = re.findall(r"(?:\([a-d]\)|[a-d]\))\s*([^\n\r]+)", q.get("raw_text", ""), flags=re.IGNORECASE)
            for opt in opts:
                Option.objects.create(question=question, text=opt.strip())

    return quiz

# The single generate_quiz view used by the template
# def generate_quiz(request):
#     if request.method == 'POST':
#         topic = request.POST.get('topic', 'General')
#         language = request.POST.get('language', 'English')
#         num_questions = request.POST.get('num_questions', '5')
#         difficulty = request.POST.get('difficulty', '1')
#         question_preference = request.POST.get('question_preference', 'MIX')

#         # Extra fields
#         prompt = request.POST.get('prompt', '').strip()
#         url = request.POST.get('url', '').strip()
#         text = request.POST.get('text', '').strip()
#         upload_file = request.FILES.get('file')

#         # Decide the source of content
#         content_source = None
#         if prompt:
#             content_source = prompt
#         elif url:
#             content_source = content_source = fetch_text_from_url(url)
#         elif text:
#             content_source = text
#         elif upload_file and upload_file.name.endswith(".pdf"):
#             content_source = extract_text_from_pdf(upload_file)
#         else:
#             content_source = topic  # fallback to topic if nothing else

#         # Now send everything to your generator
#         raw_quiz = generate__quiz(
#             topic=topic,
#             language=language,
#             num_questions=num_questions,
#             difficulty=difficulty,
#             question_type=question_preference,
#             content=content_source  # <-- NEW argument
#         )

#         parsed_quiz = parse_quiz_response(raw_quiz)

#         quiz = Quiz.objects.create(
#             topic=parsed_quiz["topic"],
#             difficulty=parsed_quiz["difficulty"],
#             user=request.user if request.user.is_authenticated else None,
#             question_preference=question_preference
#         )

#         # Save questions
#         for q in parsed_quiz["questions"]:
#             question = Question.objects.create(
#                 quiz=quiz,
#                 text=q["text"],
#                 question_type=q["type"],
#                 difficulty=q["difficulty"],
#                 answer=q["answer"]
#             )
#             if q["type"] == "MCQ" and q.get("mcq_options"):
#                 for opt in q["mcq_options"]:
#                     Option.objects.create(question=question, text=opt.strip())

#         quizzes = Quiz.objects.all().order_by('-id')[:20]
#         return render(request, 'main.html', {'quizzes': quizzes, 'created_quiz': quiz})

#     return redirect('main')
def generate_quiz(request):
    if request.method == 'POST':
        # Basic settings
        topic = request.POST.get('topic', 'General')
        language = request.POST.get('language', 'English')
        num_questions = request.POST.get('quiz_count', '5')   # template uses quiz_count
        difficulty = request.POST.get('difficulty', '1')
        question_preference = request.POST.get('quiz_type', 'MIX')  # template uses quiz_type

        # Extra fields (align with template names)
        prompt = request.POST.get('input_prompt', '').strip()
        url = request.POST.get('input_url', '').strip()
        text = request.POST.get('input_text', '').strip()
        upload_file = request.FILES.get('input_pdf')   # template uses input_pdf

        # Decide the source of content
        content_source = None
        if prompt:
            content_source = prompt
        elif url:
            content_source = fetch_text_from_url(url)
        elif text:
            content_source = text
        elif upload_file and upload_file.name.endswith(".pdf"):
            content_source = extract_text_from_pdf(upload_file)
        else:
            content_source = topic  # fallback if nothing else

        # Call generator
        raw_quiz = generate__quiz(
            topic=topic,
            language=language,
            num_questions=num_questions,
            difficulty=difficulty,
            question_type=question_preference,
            content=content_source
        )

        parsed_quiz = parse_quiz_response(raw_quiz)

        # Save quiz
        quiz = Quiz.objects.create(
            topic=parsed_quiz["topic"],
            difficulty=parsed_quiz["difficulty"],
            user=request.user if request.user.is_authenticated else None,
            question_preference=question_preference
        )

        # Save questions + options
        for q in parsed_quiz["questions"]:
            question = Question.objects.create(
                quiz=quiz,
                text=q["text"],
                question_type=q["type"],
                difficulty=q["difficulty"],
                answer=q["answer"]
            )
            if q["type"] == "MCQ" and q.get("mcq_options"):
                for opt in q["mcq_options"]:
                    Option.objects.create(question=question, text=opt.strip())

        quizzes = Quiz.objects.all().order_by('-id')[:20]
        return render(request, 'main.html', {'quizzes': quizzes, 'created_quiz': quiz})

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
            user_answer = request.POST.get(str(question.id))  # input name = question.id
            user_answers[str(question.id)] = user_answer

            if question.question_type == "SHORT":
                if user_answer and check_short_answer(user_answer, question.answer):
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
    return render(request, "quiz-result.html", {"attempt": attempt, "quiz": quiz})

def quiz_list(request):
    user = request.user
    quizzes = Quiz.objects.all()

    # Mark which quizzes the user has attempted
    attempted_quizzes = QuizAttempt.objects.filter(user=user).values_list("quiz_id", flat=True)

    for quiz in quizzes:
        quiz.attempted = quiz.id in attempted_quizzes  # add a custom attribute

    return render(request, "quiz_list.html", {"quizzes": quizzes})

def retake_quiz(request, quiz_id):
    user = request.user
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Always fetch the existing attempt (one per user+quiz)
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

        # ✅ Update the existing attempt instead of creating new
        attempt.score = marks
        attempt.answers = user_answers
        attempt.save()

        return redirect("quiz_result", attempt_id=attempt.id)

    return render(request, "quiz-take.html", {"quiz": quiz, "questions": quiz.questions.all()})

