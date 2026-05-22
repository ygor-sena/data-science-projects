import pytest
from unittest.mock import patch, MagicMock
from curator.services.youtube import (
    search_videos,
    YouTubeAPIError,
    _parse_iso8601_duration,
    _fetch_durations,
)


class TestParseDuration:
    def test_full_duration(self):
        assert _parse_iso8601_duration("PT1H2M3S") == "1:02:03"

    def test_minutes_seconds(self):
        assert _parse_iso8601_duration("PT5M30S") == "5:30"

    def test_seconds_only(self):
        assert _parse_iso8601_duration("PT45S") == "0:45"

    def test_hours_only(self):
        assert _parse_iso8601_duration("PT2H") == "2:00:00"

    def test_empty_string(self):
        assert _parse_iso8601_duration("") == ""

    def test_none_value(self):
        assert _parse_iso8601_duration(None) == ""


class TestFetchDurations:
    def test_returns_duration_map(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {"id": "abc", "contentDetails": {"duration": "PT5M30S"}},
                {"id": "xyz", "contentDetails": {"duration": "PT1H"}},
            ]
        }
        with patch("curator.services.youtube.requests.get", return_value=mock_resp):
            result = _fetch_durations("fake_key", "abc,xyz")
        assert result == {"abc": "5:30", "xyz": "1:00:00"}

    def test_returns_empty_dict_on_request_error(self):
        import requests as req_lib
        with patch(
            "curator.services.youtube.requests.get",
            side_effect=req_lib.RequestException("timeout"),
        ):
            result = _fetch_durations("fake_key", "abc")
        assert result == {}


class TestSearchVideos:
    def test_raises_when_api_key_missing(self, settings):
        settings.YOUTUBE_API_KEY = ""
        with pytest.raises(YouTubeAPIError, match="YOUTUBE_API_KEY"):
            search_videos("queijo mineiro")

    def test_returns_empty_list_when_no_items(self, settings):
        settings.YOUTUBE_API_KEY = "fake_key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"items": []}
        with patch("curator.services.youtube.requests.get", return_value=mock_resp):
            result = search_videos("termo sem resultado")
        assert result == []

    def test_returns_structured_results(self, settings):
        settings.YOUTUBE_API_KEY = "fake_key"

        search_response = MagicMock()
        search_response.json.return_value = {
            "items": [
                {
                    "id": {"videoId": "vid001"},
                    "snippet": {
                        "title": "Queijo Mineiro: Guia Completo",
                        "description": "Tudo sobre queijo artesanal.",
                        "channelTitle": "Canal Gastronomia",
                        "thumbnails": {
                            "medium": {"url": "https://img.youtube.com/vi/vid001/mqdefault.jpg"}
                        },
                    },
                }
            ]
        }

        duration_response = MagicMock()
        duration_response.json.return_value = {
            "items": [{"id": "vid001", "contentDetails": {"duration": "PT8M15S"}}]
        }

        with patch(
            "curator.services.youtube.requests.get",
            side_effect=[search_response, duration_response],
        ):
            results = search_videos("queijo mineiro")

        assert len(results) == 1
        assert results[0]["youtube_id"] == "vid001"
        assert results[0]["title"] == "Queijo Mineiro: Guia Completo"
        assert results[0]["channel_name"] == "Canal Gastronomia"
        assert results[0]["duration"] == "8:15"

    def test_raises_on_http_error(self, settings):
        import requests as req_lib
        settings.YOUTUBE_API_KEY = "fake_key"
        with patch(
            "curator.services.youtube.requests.get",
            side_effect=req_lib.RequestException("network error"),
        ):
            with pytest.raises(YouTubeAPIError, match="Erro ao buscar vídeos"):
                search_videos("qualquer coisa")

    def test_uses_medium_thumbnail_with_fallback(self, settings):
        settings.YOUTUBE_API_KEY = "fake_key"

        search_response = MagicMock()
        search_response.json.return_value = {
            "items": [
                {
                    "id": {"videoId": "vid002"},
                    "snippet": {
                        "title": "Vídeo sem thumbnail medium",
                        "description": "",
                        "channelTitle": "Canal",
                        "thumbnails": {
                            "default": {"url": "https://img.youtube.com/vi/vid002/default.jpg"}
                        },
                    },
                }
            ]
        }
        duration_response = MagicMock()
        duration_response.json.return_value = {"items": []}

        with patch(
            "curator.services.youtube.requests.get",
            side_effect=[search_response, duration_response],
        ):
            results = search_videos("algo")

        assert results[0]["thumbnail_url"] == "https://img.youtube.com/vi/vid002/default.jpg"
