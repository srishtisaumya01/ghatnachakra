from django.urls import include, path

urlpatterns = [
    path('api/v1/', include('accounts.urls')),
    path('api/v1/', include('quiz.urls')),
]
