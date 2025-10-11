# quizhippo/views.py
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, permissions, parsers
from app.models import Quiz, Question, Option
from rest_framework.decorators import api_view
from processing import (
    fetch_text_from_url,
    extract_text_from_pdf,
    parse_quiz_response,
)
from services import (
    generate__quiz, 
    assistant,
)
from constants import (
    LANGUAGES,
    DEFAULT_LANGUAGE,
    DIFFICULTY_LEVELS,
    DEFAULT_DIFFICULTY,
    QUESTION_TYPES,
    DEFAULT_QUESTION_TYPE,
    CHOOSE_OPTIONS,
    DEFAULT_CHOOSE,
)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", "")

        if not username or not password:
            return Response(
                {"error": "Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "User already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(username=username, password=password, email=email)
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "User registered successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        }, status=status.HTTP_201_CREATED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

class GenerateQuizAPI(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def post(self, request, *args, **kwargs):
        try:
            # Extract input data safely
            topic = request.data.get('topic', 'General')
            language = request.data.get('language', 'English')
            num_questions = int(request.data.get('quiz_count', 5))
            difficulty = int(request.data.get('difficulty', 1))
            question_preference = request.data.get('quiz_type', 'MIX').upper()
            category = request.data.get('category', 'General')
            prompt = request.data.get('input_prompt', '').strip()
            url = request.data.get('input_url', '').strip()
            text = request.data.get('input_text', '').strip()
            upload_file = request.FILES.get('input_pdf')

            # Determine content source
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

            # Generate quiz content (AI or custom logic)
            raw_quiz = generate__quiz(
                topic=topic,
                language=language,
                num_questions=num_questions,
                difficulty=difficulty,
                question_type=question_preference,
                content=content_source,
            )

            parsed_quiz = parse_quiz_response(raw_quiz)

            # Create Quiz instance
            quiz = Quiz.objects.create(
                topic=parsed_quiz.get("topic", topic),
                difficulty=int(parsed_quiz.get("difficulty", difficulty)),
                category=parsed_quiz.get("category", category),
                question_preference=question_preference,
                user=request.user if request.user.is_authenticated else None,
            )

            # Create Questions + Options
            for q in parsed_quiz.get("questions", []):
                question = Question.objects.create(
                    quiz=quiz,
                    text=q["text"],
                    question_type=q["type"].upper(),
                    difficulty=int(q.get("difficulty", difficulty)),
                    answer=q["answer"]
                )

                if q["type"].upper() == "MCQ" and q.get("mcq_options"):
                    for opt in q["mcq_options"]:
                        Option.objects.create(question=question, text=opt.strip())

            # ✅ Use correct related_name ("questions" and "options")
            quiz_data = {
                "id": quiz.id,
                "topic": quiz.topic,
                "difficulty": quiz.difficulty,
                "category": quiz.category,
                "question_preference": quiz.question_preference,
                "questions": [
                    {
                        "id": q.id,
                        "text": q.text,
                        "type": q.question_type,
                        "difficulty": q.difficulty,
                        "answer": q.answer,
                        "options": [o.text for o in q.options.all()],
                    }
                    for q in quiz.questions.all()
                ],
            }

            # Build response
            response_data = {
                "status": "success",
                "message": "Quiz generated successfully.",
                "quiz": quiz_data,
                "meta": {
                    "languages": LANGUAGES,
                    "default_language": DEFAULT_LANGUAGE,
                    "levels": DIFFICULTY_LEVELS,
                    "default_level": DEFAULT_DIFFICULTY,
                    "question_types": QUESTION_TYPES,
                    "default_type": DEFAULT_QUESTION_TYPE,
                    "choose_options": CHOOSE_OPTIONS,
                    "default_choose": DEFAULT_CHOOSE,
                },
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

@api_view(['POST'])
def chat_assistant(request):
    """
    Simple API endpoint to handle chat queries using your assistant function.
    """
    query = request.data.get('query', '').strip()

    if not query:
        return Response(
            {"error": "Query is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        response = assistant(query)
        return Response({"response": response}, status=status.HTTP_200_OK)
    except Exception as e:
        # Optional: log the error before returning response
        print(f"Error in chat_assistant: {e}")
        return Response(
            {"error": "Something went wrong while processing your request."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
