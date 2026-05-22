from django.db import models
from django.contrib.auth.models import User


class TrainingModule(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField()
    description = models.TextField()
    default_keywords = models.CharField(
        max_length=500,
        help_text="Palavras-chave separadas por vírgula usadas na busca padrão",
    )
    icon = models.CharField(max_length=50, default="bi-play-circle")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="modules",
    )

    class Meta:
        ordering = ["id"]
        unique_together = (("created_by", "slug"),)
        verbose_name = "Módulo de Treinamento"
        verbose_name_plural = "Módulos de Treinamento"

    def __str__(self):
        return self.name


class CuratedVideo(models.Model):
    youtube_id = models.CharField(max_length=20)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField()
    channel_name = models.CharField(max_length=200)
    duration = models.CharField(max_length=20, blank=True)
    module = models.ForeignKey(
        TrainingModule, on_delete=models.CASCADE, related_name="videos"
    )
    added_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="curated_videos"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = (("youtube_id", "module"),)
        verbose_name = "Vídeo Curado"
        verbose_name_plural = "Vídeos Curados"

    def __str__(self):
        return self.title

    @property
    def youtube_url(self):
        return f"https://www.youtube.com/watch?v={self.youtube_id}"

    @property
    def embed_url(self):
        return f"https://www.youtube.com/embed/{self.youtube_id}"


class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progress")
    video = models.ForeignKey(
        CuratedVideo, on_delete=models.CASCADE, related_name="progress"
    )
    watched = models.BooleanField(default=False)
    watched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "video")
        verbose_name = "Progresso do Usuário"
        verbose_name_plural = "Progresso dos Usuários"

    def __str__(self):
        status = "assistido" if self.watched else "pendente"
        return f"{self.user.username} — {self.video.title[:40]} ({status})"
