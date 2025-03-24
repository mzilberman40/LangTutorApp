from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from lingua.models import Student, Entity, Phrase, Lesson, StudentProgress
from lingua.serializers import StudentSerializer, EntitySerializer, PhraseSerializer, LessonSerializer, StudentProgressSerializer


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Entity, Phrase
from .serializers import PhraseSerializer

import random

# Placeholder AI function
def generate_phrases_for_entity(entity_text, count):
    templates = [
        "I like {}.",
        "Do you have any {}?",
        "This is a {}.",
        "I bought a new {}.",
        "The {} is on the table."
    ]
    return [template.format(entity_text) for template in random.sample(templates, min(count, len(templates)))]


class GeneratePhrasesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student_id = request.data.get("student_id")
        num_phrases = int(request.data.get("num_phrases_per_entity", 3))

        entities = Entity.objects.filter(student_id=student_id)
        phrases_created = []

        for entity in entities:
            examples = generate_phrases_for_entity(entity.text_native, num_phrases)
            for native_phrase in examples:
                phrase = Phrase.objects.create(
                    entity=entity,
                    text_native=native_phrase,
                    text_target=f"<translated:{native_phrase}>"  # placeholder target
                )
                phrases_created.append(phrase)

        return Response({"generated": len(phrases_created)}, status=status.HTTP_201_CREATED)



@extend_schema_view(
    list=extend_schema(
        summary="List students",
        description="Get all students (auth required)",
        tags=["Students"],
        auth=["Bearer"]
    ),
    create=extend_schema(
        summary="Create student",
        description="Register a new student (auth required)",
        tags=["Students"],
        auth=["Bearer"]
    )
)
class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(
    tags=["Entities"],
    summary="List or create entities",
    description="An entity is a word or base expression used to generate phrases."
)
class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


@extend_schema(
    tags=["Phrases"],
    summary="List or create phrases",
    description="Phrases are generated or manually added and linked to entities."
)
class PhraseViewSet(viewsets.ModelViewSet):
    queryset = Phrase.objects.all()
    serializer_class = PhraseSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(
    tags=["Lessons"],
    summary="List or create lessons",
    description="Lessons are collections of phrases grouped into audio learning files."
)
class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(
    tags=["Progress"],
    summary="Track or update student progress",
    description="Tracks repetition count, recall accuracy, and last reviewed time."
)
class StudentProgressViewSet(viewsets.ModelViewSet):
    queryset = StudentProgress.objects.all()
    serializer_class = StudentProgressSerializer
    permission_classes = [IsAuthenticated]
