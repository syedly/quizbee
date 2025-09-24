# quizapp/models.py
from django.db import models
from django.contrib.auth.models import User

class Quiz(models.Model):
    QUESTION_PREFERENCES = [
        ('SHORT', 'Short Questions'),
        ('TF', 'True/False'),
        ('MCQ', 'Multiple Choice'),
        ('FILL', 'Fill in the Blank'),
        ('MIX', 'Mix'),
    ]

    topic = models.CharField(max_length=200)
    difficulty = models.IntegerField(default=1)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="quizzes")
    question_preference = models.CharField(max_length=10, choices=QUESTION_PREFERENCES, default="MIX")

    def __str__(self):
        return f"{self.topic} (Difficulty {self.difficulty})"



class Question(models.Model):
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice'),
        ('TF', 'True/False'),
        ('SHORT', 'Short Answer'),
        ('FILL', 'Fill in the Blank'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES)
    difficulty = models.IntegerField(default=1)
    answer = models.CharField(max_length=200)
    user_answer = models.CharField(max_length=1020, null=True, blank=True)

    def __str__(self):
        return self.text


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=200)

    def __str__(self):
        return self.text
