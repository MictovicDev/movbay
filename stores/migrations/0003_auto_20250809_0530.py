from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0002_delete_storefollow'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreFollow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('followed_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('follower', models.ForeignKey(
                    related_name='follows',
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to=settings.AUTH_USER_MODEL
                )),
                ('followed_store', models.ForeignKey(
                    related_name='store_followers',
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to='stores.store'
                )),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=['follower', 'followed_store'], name='unique_store_follow'),
                ],
            },
        ),
    ]
