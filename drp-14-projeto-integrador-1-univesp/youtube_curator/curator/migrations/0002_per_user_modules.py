from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("curator", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # TrainingModule: drop global slug unique, add created_by, add composite unique
        migrations.AlterField(
            model_name="trainingmodule",
            name="slug",
            field=models.SlugField(),
        ),
        migrations.AddField(
            model_name="trainingmodule",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="modules",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="trainingmodule",
            unique_together={("created_by", "slug")},
        ),
        # CuratedVideo: drop global youtube_id unique, add per-module unique
        migrations.AlterField(
            model_name="curatedvideo",
            name="youtube_id",
            field=models.CharField(max_length=20),
        ),
        migrations.AlterUniqueTogether(
            name="curatedvideo",
            unique_together={("youtube_id", "module")},
        ),
    ]
