import pytest
from django.urls import reverse
from curator.models import CuratedVideo, UserProgress


@pytest.mark.django_db
class TestAuthRedirect:
    def test_dashboard_redirects_anonymous(self, client):
        resp = client.get(reverse("curator:dashboard"))
        assert resp.status_code == 302
        assert "/accounts/login/" in resp["Location"]

    def test_search_redirects_anonymous(self, client):
        resp = client.get(reverse("curator:search"))
        assert resp.status_code == 302

    def test_module_detail_redirects_anonymous(self, client, module):
        resp = client.get(reverse("curator:module_detail", kwargs={"slug": module.slug}))
        assert resp.status_code == 302


@pytest.mark.django_db
class TestDashboard:
    def test_dashboard_renders_for_authenticated_user(self, client, user, module):
        client.force_login(user)
        resp = client.get(reverse("curator:dashboard"))
        assert resp.status_code == 200
        assert module.name.encode() in resp.content

    def test_dashboard_does_not_show_other_users_modules(self, client, staff_user, module):
        client.force_login(staff_user)
        resp = client.get(reverse("curator:dashboard"))
        assert resp.status_code == 200
        assert module.name.encode() not in resp.content

    def test_dashboard_shows_progress(self, client, user, module, video):
        from django.utils import timezone
        UserProgress.objects.create(user=user, video=video, watched=True, watched_at=timezone.now())
        client.force_login(user)
        resp = client.get(reverse("curator:dashboard"))
        assert resp.status_code == 200


@pytest.mark.django_db
class TestModuleDetail:
    def test_module_detail_renders_videos(self, client, user, module, video):
        client.force_login(user)
        resp = client.get(reverse("curator:module_detail", kwargs={"slug": module.slug}))
        assert resp.status_code == 200
        assert video.title.encode() in resp.content

    def test_module_detail_404_for_unknown_slug(self, client, user):
        client.force_login(user)
        resp = client.get(reverse("curator:module_detail", kwargs={"slug": "nao-existe"}))
        assert resp.status_code == 404

    def test_module_detail_404_for_non_owner(self, client, staff_user, module):
        client.force_login(staff_user)
        resp = client.get(reverse("curator:module_detail", kwargs={"slug": module.slug}))
        assert resp.status_code == 404


@pytest.mark.django_db
class TestSearch:
    def test_search_page_renders_without_query(self, client, user):
        client.force_login(user)
        resp = client.get(reverse("curator:search"))
        assert resp.status_code == 200

    def test_search_with_missing_api_key_shows_error(self, client, user, settings):
        settings.YOUTUBE_API_KEY = ""
        client.force_login(user)
        resp = client.get(reverse("curator:search"), {"q": "queijo mineiro"})
        assert resp.status_code == 200
        assert "YOUTUBE_API_KEY" in resp.content.decode()


@pytest.mark.django_db
class TestSaveVideo:
    def test_save_video_creates_curated_video(self, client, user, module):
        client.force_login(user)
        resp = client.post(
            reverse("curator:save_video"),
            {
                "youtube_id": "xyz123abc",
                "title": "Vídeo de Teste",
                "description": "Descrição",
                "thumbnail_url": "https://img.youtube.com/vi/xyz123abc/mqdefault.jpg",
                "channel_name": "Canal Teste",
                "duration": "3:45",
                "module_slug": module.slug,
            },
        )
        assert resp.status_code == 302
        assert CuratedVideo.objects.filter(youtube_id="xyz123abc").exists()

    def test_save_video_duplicate_does_not_create_second(self, client, user, module, video):
        client.force_login(user)
        client.post(
            reverse("curator:save_video"),
            {
                "youtube_id": video.youtube_id,
                "title": video.title,
                "description": "",
                "thumbnail_url": video.thumbnail_url,
                "channel_name": video.channel_name,
                "duration": video.duration,
                "module_slug": module.slug,
            },
        )
        assert CuratedVideo.objects.filter(youtube_id=video.youtube_id).count() == 1

    def test_save_video_get_redirects(self, client, user):
        client.force_login(user)
        resp = client.get(reverse("curator:save_video"))
        assert resp.status_code == 302

    def test_save_video_missing_data_shows_error(self, client, user):
        client.force_login(user)
        resp = client.post(reverse("curator:save_video"), {"youtube_id": "", "module_slug": ""})
        assert resp.status_code == 302


@pytest.mark.django_db
class TestToggleProgress:
    def test_toggle_marks_as_watched(self, client, user, video, module):
        client.force_login(user)
        client.post(
            reverse("curator:toggle_progress", kwargs={"video_id": video.id}),
            {"next": reverse("curator:module_detail", kwargs={"slug": module.slug})},
        )
        progress = UserProgress.objects.get(user=user, video=video)
        assert progress.watched is True
        assert progress.watched_at is not None

    def test_toggle_unmarks_watched(self, client, user, video, module):
        from django.utils import timezone
        UserProgress.objects.create(user=user, video=video, watched=True, watched_at=timezone.now())
        client.force_login(user)
        client.post(
            reverse("curator:toggle_progress", kwargs={"video_id": video.id}),
            {"next": reverse("curator:module_detail", kwargs={"slug": module.slug})},
        )
        progress = UserProgress.objects.get(user=user, video=video)
        assert progress.watched is False
        assert progress.watched_at is None

    def test_toggle_get_redirects(self, client, user, video):
        client.force_login(user)
        resp = client.get(reverse("curator:toggle_progress", kwargs={"video_id": video.id}))
        assert resp.status_code == 302


@pytest.mark.django_db
class TestRemoveVideo:
    def test_owner_can_remove_video(self, client, user, video, module):
        client.force_login(user)
        resp = client.post(reverse("curator:remove_video", kwargs={"video_id": video.id}))
        assert resp.status_code == 302
        assert not CuratedVideo.objects.filter(pk=video.id).exists()

    def test_non_owner_gets_404_on_remove(self, client, staff_user, video, module):
        client.force_login(staff_user)
        resp = client.post(reverse("curator:remove_video", kwargs={"video_id": video.id}))
        assert resp.status_code == 404

    def test_owner_sees_remove_button(self, client, user, video, module):
        client.force_login(user)
        resp = client.get(reverse("curator:module_detail", kwargs={"slug": module.slug}))
        remove_url = reverse("curator:remove_video", kwargs={"video_id": video.id})
        assert remove_url.encode() in resp.content
