from django.db import models
from django.contrib.auth.models import AbstractUser, Permission, Group


# Custom User model
class Student(AbstractUser):
    native_language = models.CharField(max_length=50)
    target_language = models.CharField(max_length=50)
    proficiency_level = models.CharField(max_length=10, choices=[("A1", "A1"), ("A2", "A2"), ("B1", "B1"), ("B2", "B2"), ("C1", "C1"), ("C2", "C2")])
    groups = models.ManyToManyField(Group, related_name="student_groups")
    user_permissions = models.ManyToManyField(Permission, related_name="student_permissions")


# Entities (words/phrases)
class Entity(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="entities")
    text_native = models.CharField(max_length=255)
    text_target = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

# Phrases generated from entities
class Phrase(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="phrases")
    text_native = models.CharField(max_length=255)
    text_target = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

# Lessons that contain multiple phrases
class Lesson(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    phrases = models.ManyToManyField(Phrase, related_name="lessons")
    created_at = models.DateTimeField(auto_now_add=True)

# Tracking user progress
class StudentProgress(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="progress")
    phrase = models.ForeignKey(Phrase, on_delete=models.CASCADE)
    recall_accuracy = models.FloatField(default=0.0)
    repetition_count = models.IntegerField(default=0)
    last_reviewed = models.DateTimeField(auto_now=True)
