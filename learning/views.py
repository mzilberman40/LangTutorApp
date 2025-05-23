import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import StudyWordSerializer

logger = logging.getLogger(__name__)


class StudyWordView(APIView):
    """POST /api/study-words/
    Accepts a list of studied words and stores them in the database.

    Example:
    {
        "language": "en_GB",
        "words": ["outshine", "brilliant"]
    }

    Returns:
    {
        "added": ["outshine", "brilliant"]
    }
    """

    def post(self, request, *args, **kwargs):
        serializer = StudyWordSerializer(data=request.data)
        if serializer.is_valid():
            words = serializer.save()
            logger.info("Added %d studied words", len(words))
            return Response(
                {"added": [w.text for w in words]}, status=status.HTTP_201_CREATED
            )
        logger.warning("Invalid study word payload: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
