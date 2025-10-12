# quizhippo/views.py
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, permissions, parsers
from django.db.models import Avg
from app.models import (
    Quiz, Question, 
    Option, UserProfile, 
    QuizAttempt, ServerQuiz, 
    Server
)
from rest_framework.pagination import PageNumberPagination
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
    QUIZ_CATEGORIES,
)
from .serializers import (
    UserProfileSerializer, QuizSerializer, QuizAttemptSerializer,
    QuestionSerializer, OptionSerializer, QuizRatingSerializer,
    ServerSerializer, ServerQuizSerializer
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

class UpdatePreferencesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Update user preferences (e.g. light mode).
        """
        light_mode = request.data.get("light_mode")

        if light_mode is None:
            return Response(
                {"error": "Missing field 'light_mode'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert "true"/"false" or "on"/"off" to boolean
        light_mode_bool = str(light_mode).lower() in ["true", "on", "1"]

        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.light_mode = light_mode_bool
        profile.save()

        return Response(
            {
                "message": "Preferences updated successfully",
                "light_mode": profile.light_mode
            },
            status=status.HTTP_200_OK
        )
    
    def get(self, request):
        """
        Retrieve current user preferences.
        """
        try:
            profile = UserProfile.objects.get(user=request.user)
            return Response(
                {"light_mode": profile.light_mode},
                status=status.HTTP_200_OK
            )
        except UserProfile.DoesNotExist:
            # If no profile exists yet, assume default False
            return Response(
                {"light_mode": False},
                status=status.HTTP_200_OK
            )

class QuizPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50

class AllQuizzesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        quizzes = (Quiz.objects.filter(user=user) | Quiz.objects.filter(shared_with=user)).distinct()

        # Paginate
        paginator = QuizPagination()
        page = paginator.paginate_queryset(quizzes, request)
        serializer = QuizSerializer(page, many=True, context={'request': request})

        return paginator.get_paginated_response(serializer.data)
    
class CheckQuizAttempt(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get all quizzes
        all_quizzes = Quiz.objects.all()

        # Get IDs of quizzes attempted by the user
        attempted_ids = QuizAttempt.objects.filter(user=user).values_list("quiz_id", flat=True)

        # Separate attempted and not attempted
        attempted = Quiz.objects.filter(id__in=attempted_ids)
        not_attempted = Quiz.objects.exclude(id__in=attempted_ids)

        # Build clean JSON response
        data = {
            "attempted": [
                {
                    "id": quiz.id,
                    "title": quiz.topic,
                    
                }
                for quiz in attempted
            ],
            "not_attempted": [
                {
                    "id": quiz.id,
                    "title": quiz.topic,
                    
                }
                for quiz in not_attempted
            ],
        }

        return Response(data, status=status.HTTP_200_OK)
    
class DeleteAccount(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user

        # Invalidate tokens before deleting
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass  # If token invalid, just ignore

        username = user.username
        user.delete()
        return Response(
            {"message": f"User '{username}' deleted successfully."},
            status=status.HTTP_200_OK
        )
    
class ChangePassword(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response(
                {"error": "Both old and new passwords are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(old_password):
            return Response(
                {"error": "Incorrect current password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK
        )
    
class DeleteQuiz(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, quiz_id):
        user = request.user
        quiz = get_object_or_404(Quiz, id=quiz_id, user=user)
        quiz.delete()
        return Response(
            {"message": "Quiz deleted successfully."},
            status=status.HTTP_200_OK
        )

class QuizVisibilityAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, quiz_id):
        """
        Toggle quiz visibility (public/private)
        """
        quiz = get_object_or_404(Quiz, id=quiz_id, user=request.user)
        is_public = request.data.get("is_public")

        # Validate input
        if is_public is None:
            return Response(
                {"error": "Missing field 'is_public'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert to boolean safely
        quiz.is_public = str(is_public).lower() in ["true", "1", "yes", "on"]
        quiz.save()

        return Response(
            {
                "message": f"Quiz visibility updated successfully!",
                "quiz_id": quiz.id,
                "is_public": quiz.is_public
            },
            status=status.HTTP_200_OK
        )

class ExploreQuizzesAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, filter_type=None):
        quizzes = Quiz.objects.filter(is_public=True).annotate(
            avg_rating=Avg('ratings__rating')
        )

        category = request.GET.get("category")
        difficulty = request.GET.get("difficulty")

        # Apply category filter
        if category:
            quizzes = quizzes.filter(category__iexact=category)

        # Apply difficulty filter
        if difficulty:
            quizzes = quizzes.filter(difficulty=difficulty)

        # Apply "trending" filter
        if filter_type == "trending":
            quizzes = quizzes.filter(avg_rating__gt=3.5)
            active_filter = "trending"
        else:
            active_filter = "explore"

        # Prepare response data
        data = [
            {
                "id": quiz.id,
                "title": quiz.topic,
                "category": quiz.category,
                "difficulty": quiz.difficulty,
                "is_public": quiz.is_public,
                "avg_rating": quiz.avg_rating or 0,
                "created_by": quiz.user.username,
            }
            for quiz in quizzes
        ]

        return Response(
            {
                "active_filter": active_filter,
                "categories": QUIZ_CATEGORIES,
                "difficulty_levels": DIFFICULTY_LEVELS,
                "selected_category": category,
                "selected_difficulty": difficulty,
                "results": data,
            },
            status=status.HTTP_200_OK
        )
