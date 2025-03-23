from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Student, Entity, Phrase, Lesson, StudentProgress

class StudentAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email', 'native_language', 'target_language', 'proficiency_level')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'native_language', 'target_language', 'proficiency_level'),
        }),
    )
    list_display = ('username', 'email', 'native_language', 'target_language', 'proficiency_level', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('username',)

# Register your custom user model
admin.site.register(Student, StudentAdmin)

# Register other models
admin.site.register(Entity)
admin.site.register(Phrase)
admin.site.register(Lesson)
admin.site.register(StudentProgress)
