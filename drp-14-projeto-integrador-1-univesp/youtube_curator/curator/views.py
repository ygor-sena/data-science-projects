from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from .models import TrainingModule, CuratedVideo, UserProgress
from .services.youtube import search_videos, YouTubeAPIError


@login_required
def dashboard(request):
    modules = TrainingModule.objects.prefetch_related("videos").filter(
        created_by=request.user
    )
    module_stats = []
    for module in modules:
        total = module.videos.count()
        watched = UserProgress.objects.filter(
            user=request.user, video__module=module, watched=True
        ).count()
        module_stats.append(
            {"module": module, "total": total, "watched": watched}
        )
    return render(request, "curator/dashboard.html", {"module_stats": module_stats})


@login_required
def module_detail(request, slug):
    module = get_object_or_404(TrainingModule, slug=slug, created_by=request.user)
    videos = module.videos.all()

    progress_map = {
        p.video_id: p
        for p in UserProgress.objects.filter(user=request.user, video__module=module)
    }

    video_list = []
    for video in videos:
        progress = progress_map.get(video.id)
        video_list.append({"video": video, "watched": progress.watched if progress else False})

    return render(
        request,
        "curator/module_detail.html",
        {"module": module, "video_list": video_list},
    )


@login_required
def search(request):
    modules = TrainingModule.objects.filter(created_by=request.user)
    results = []
    query = request.GET.get("q", "").strip()
    module_slug = request.GET.get("module", "")
    selected_module = None

    if module_slug:
        selected_module = modules.filter(slug=module_slug).first()

    if query:
        try:
            results = search_videos(query)
        except YouTubeAPIError as exc:
            messages.error(request, str(exc))

    return render(
        request,
        "curator/search.html",
        {
            "query": query,
            "results": results,
            "modules": modules,
            "selected_module": selected_module,
        },
    )


@login_required
def save_video(request):
    if request.method != "POST":
        return redirect("curator:search")

    youtube_id = request.POST.get("youtube_id", "").strip()
    module_slug = request.POST.get("module_slug", "").strip()

    if not youtube_id or not module_slug:
        messages.error(request, "Dados inválidos para salvar o vídeo.")
        return redirect("curator:search")

    module = get_object_or_404(TrainingModule, slug=module_slug, created_by=request.user)

    _, created = CuratedVideo.objects.get_or_create(
        youtube_id=youtube_id,
        module=module,
        defaults={
            "title": request.POST.get("title", "")[:300],
            "description": request.POST.get("description", ""),
            "thumbnail_url": request.POST.get("thumbnail_url", ""),
            "channel_name": request.POST.get("channel_name", "")[:200],
            "duration": request.POST.get("duration", "")[:20],
            "added_by": request.user,
        },
    )

    if created:
        messages.success(
            request,
            f'Vídeo adicionado ao módulo "{module.name}" com sucesso!',
        )
    else:
        messages.info(request, "Este vídeo já está neste módulo.")

    return redirect("curator:module_detail", slug=module_slug)


@login_required
def toggle_progress(request, video_id):
    if request.method != "POST":
        return redirect("curator:dashboard")

    video = get_object_or_404(CuratedVideo, pk=video_id)
    progress, _ = UserProgress.objects.get_or_create(
        user=request.user, video=video
    )
    progress.watched = not progress.watched
    progress.watched_at = timezone.now() if progress.watched else None
    progress.save()

    return redirect(request.POST.get("next", "curator:dashboard"))


@login_required
def remove_video(request, video_id):
    if request.method != "POST":
        return redirect("curator:dashboard")

    video = get_object_or_404(CuratedVideo, pk=video_id, module__created_by=request.user)
    module_slug = video.module.slug
    video.delete()
    messages.success(request, "Vídeo removido da playlist.")
    return redirect("curator:module_detail", slug=module_slug)
