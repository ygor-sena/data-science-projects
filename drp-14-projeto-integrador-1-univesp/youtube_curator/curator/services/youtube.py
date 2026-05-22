import re
import requests
from django.conf import settings

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeAPIError(Exception):
    pass


def _parse_iso8601_duration(duration: str) -> str:
    """Convert ISO 8601 duration (PT1H2M3S) to human-readable (1:02:03)."""
    match = re.match(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or ""
    )
    if not match:
        return ""
    hours, minutes, seconds = (int(v or 0) for v in match.groups())
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def search_videos(query: str, max_results: int = 10, language: str = "pt") -> list[dict]:
    """
    Search YouTube for videos matching *query*.

    Returns a list of dicts with keys:
        youtube_id, title, description, thumbnail_url, channel_name, duration
    """
    api_key = settings.YOUTUBE_API_KEY
    if not api_key:
        raise YouTubeAPIError("YOUTUBE_API_KEY não configurada nas variáveis de ambiente.")

    search_params = {
        "key": api_key,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": max_results,
        "relevanceLanguage": language,
        "safeSearch": "moderate",
        "videoEmbeddable": "true",
    }

    try:
        resp = requests.get(SEARCH_URL, params=search_params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise YouTubeAPIError(f"Erro ao buscar vídeos: {exc}") from exc

    items = resp.json().get("items", [])
    if not items:
        return []

    video_ids = ",".join(item["id"]["videoId"] for item in items)
    duration_map = _fetch_durations(api_key, video_ids)

    results = []
    for item in items:
        vid_id = item["id"]["videoId"]
        snippet = item["snippet"]
        thumbnails = snippet.get("thumbnails", {})
        thumb = (
            thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )
        results.append(
            {
                "youtube_id": vid_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "thumbnail_url": thumb,
                "channel_name": snippet.get("channelTitle", ""),
                "duration": duration_map.get(vid_id, ""),
            }
        )
    return results


def _fetch_durations(api_key: str, video_ids: str) -> dict[str, str]:
    """Fetch content details to get video durations."""
    try:
        resp = requests.get(
            VIDEOS_URL,
            params={"key": api_key, "id": video_ids, "part": "contentDetails"},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return {}

    return {
        item["id"]: _parse_iso8601_duration(
            item.get("contentDetails", {}).get("duration", "")
        )
        for item in resp.json().get("items", [])
    }
