import pytest
from django.utils import timezone
from curator.models import TrainingModule, CuratedVideo, UserProgress


@pytest.mark.django_db
class TestTrainingModule:
    def test_str_returns_name(self, module):
        assert str(module) == "Técnicas de Venda"

    def test_default_ordering_by_id(self, db):
        m1 = TrainingModule.objects.create(
            name="A", slug="a", description="", default_keywords=""
        )
        m2 = TrainingModule.objects.create(
            name="B", slug="b", description="", default_keywords=""
        )
        modules = list(TrainingModule.objects.all())
        assert modules.index(m1) < modules.index(m2)

    def test_slug_unique_per_user(self, module, user, db):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            TrainingModule.objects.create(
                name="Duplicate", slug="tecnicas-venda", description="", default_keywords="",
                created_by=user,
            )

    def test_same_slug_allowed_for_different_users(self, module, staff_user, db):
        other = TrainingModule.objects.create(
            name="Técnicas de Venda", slug="tecnicas-venda", description="", default_keywords="",
            created_by=staff_user,
        )
        assert other.pk is not None


@pytest.mark.django_db
class TestCuratedVideo:
    def test_str_returns_title(self, video):
        assert str(video) == "Como Vender Queijo Mineiro"

    def test_youtube_url_property(self, video):
        assert video.youtube_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_embed_url_property(self, video):
        assert video.embed_url == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_youtube_id_is_unique(self, video, module, user, db):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            CuratedVideo.objects.create(
                youtube_id="dQw4w9WgXcQ",
                title="Duplicado",
                thumbnail_url="http://example.com/thumb.jpg",
                channel_name="Canal",
                module=module,
                added_by=user,
            )

    def test_ordering_newest_first(self, module, user, db):
        v1 = CuratedVideo.objects.create(
            youtube_id="aaa",
            title="Primeiro",
            thumbnail_url="http://img.com/a.jpg",
            channel_name="C",
            module=module,
            added_by=user,
        )
        v2 = CuratedVideo.objects.create(
            youtube_id="bbb",
            title="Segundo",
            thumbnail_url="http://img.com/b.jpg",
            channel_name="C",
            module=module,
            added_by=user,
        )
        videos = list(module.videos.all())
        assert videos[0] == v2
        assert videos[1] == v1


@pytest.mark.django_db
class TestUserProgress:
    def test_str_watched(self, video, user, db):
        progress = UserProgress.objects.create(
            user=user, video=video, watched=True, watched_at=timezone.now()
        )
        assert "assistido" in str(progress)

    def test_str_pending(self, video, user, db):
        progress = UserProgress.objects.create(user=user, video=video, watched=False)
        assert "pendente" in str(progress)

    def test_unique_together_user_video(self, video, user, db):
        from django.db import IntegrityError
        UserProgress.objects.create(user=user, video=video)
        with pytest.raises(IntegrityError):
            UserProgress.objects.create(user=user, video=video)
