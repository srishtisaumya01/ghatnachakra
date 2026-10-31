from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.HealthView.as_view()),
    path('stats/', views.PublicStatsView.as_view()),
    path('data/<path:path>', views.DataView.as_view()),
    path('crop/', views.CropView.as_view()),
    path('attempts/', views.AttemptListView.as_view()),
    path('attempts/<int:pk>/', views.AttemptDetailView.as_view()),
    path('qstats/', views.QuestionStatsView.as_view()),
]
