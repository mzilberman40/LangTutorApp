from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from lingua.views import StudentViewSet, EntityViewSet, PhraseViewSet, LessonViewSet, StudentProgressViewSet

router = DefaultRouter()
router.register(r'students', StudentViewSet)
router.register(r'entities', EntityViewSet)
router.register(r'phrases', PhraseViewSet)
router.register(r'lessons', LessonViewSet)
router.register(r'student-progress', StudentProgressViewSet)


urlpatterns = [
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]