from rest_framework import serializers
from .models import Word


class StudyWordSerializer(serializers.Serializer):
    language = serializers.CharField(max_length=20, default="en_GB")
    words = serializers.ListField(
        child=serializers.CharField(max_length=100), min_length=1
    )

    def create(self, validated_data):
        lang = validated_data["language"]
        created = []
        for text in validated_data["words"]:
            word, _ = Word.objects.get_or_create(
                text=text.lower().strip(), language=lang
            )
            created.append(word)
        return created
