from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet
from django.views.generic import TemplateView

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('projects/', TemplateView.as_view(template_name='projects/list.html'), name='project-list'),
    path('projects/new/', TemplateView.as_view(template_name='projects/form.html'), name='project-create'),
    path('projects/<uuid:pk>/', TemplateView.as_view(template_name='projects/detail.html'), name='project-detail'),
]
