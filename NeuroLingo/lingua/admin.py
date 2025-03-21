from django.contrib import admin
from .models import Student, Entity, Phrase, Lesson, StudentProgress

admin.site.register(Student)
admin.site.register(Entity)
admin.site.register(Phrase)
admin.site.register(Lesson)
admin.site.register(StudentProgress)