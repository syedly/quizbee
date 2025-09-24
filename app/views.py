# quizapp/views.py
import re
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from services import generate__quiz
from .models import Quiz, Question, Option

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

def main(request):
    # show list of quizzes on this page
    quizzes = Quiz.objects.filter(user=request.user)
    return render(request, 'main.html', {'quizzes': quizzes})

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
def generate_quiz(request):
    if request.method == 'POST':
        topic = request.POST.get('topic', 'General')
        language = request.POST.get('language', 'English')
        num_questions = request.POST.get('num_questions', '5')
        difficulty = request.POST.get('difficulty', '1')
        question_preference = request.POST.get('question_preference', 'MIX')

        # Extra fields
        prompt = request.POST.get('prompt', '').strip()
        url = request.POST.get('url', '').strip()
        text = request.POST.get('text', '').strip()
        upload_file = request.FILES.get('file')

        # Decide the source of content
        content_source = None
        if prompt:
            content_source = prompt
        elif url:
            content_source = f"Extract quiz from URL: {url}"
        elif text:
            content_source = text
        elif upload_file:
            file_text = upload_file.read().decode("utf-8", errors="ignore")
            content_source = file_text
        else:
            content_source = topic  # fallback to topic if nothing else

        # Now send everything to your generator
        raw_quiz = generate__quiz(
            topic=topic,
            language=language,
            num_questions=num_questions,
            difficulty=difficulty,
            question_type=question_preference,
            content=content_source  # <-- NEW argument
        )

        parsed_quiz = parse_quiz_response(raw_quiz)

        quiz = Quiz.objects.create(
            topic=parsed_quiz["topic"],
            difficulty=parsed_quiz["difficulty"],
            user=request.user if request.user.is_authenticated else None,
            question_preference=question_preference
        )

        # Save questions
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
