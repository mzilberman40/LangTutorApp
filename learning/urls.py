from django.urls import path
from .views import StudyWordView

urlpatterns = [
    path("study-words/", StudyWordView.as_view(), name="study-words"),
    # path("generate-phrases/", GeneratePhrasesView.as_view(), name="generate-phrases"),
    # path("task-status/<uuid:task_id>/", TaskStatusView.as_view(), name="task-status"),
]
