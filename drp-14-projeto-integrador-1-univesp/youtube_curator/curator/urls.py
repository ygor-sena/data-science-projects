from django.urls import path
from . import views

app_name = "curator"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("modulo/<slug:slug>/", views.module_detail, name="module_detail"),
    path("buscar/", views.search, name="search"),
    path("salvar-video/", views.save_video, name="save_video"),
    path("progresso/<int:video_id>/", views.toggle_progress, name="toggle_progress"),
    path("remover/<int:video_id>/", views.remove_video, name="remove_video"),
]
