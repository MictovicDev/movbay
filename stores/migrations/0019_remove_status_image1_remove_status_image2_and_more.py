# Generated by Django 5.2 on 2025-06-07 14:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0018_statusimage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='status',
            name='image1',
        ),
        migrations.RemoveField(
            model_name='status',
            name='image2',
        ),
        migrations.RemoveField(
            model_name='status',
            name='image3',
        ),
        migrations.RemoveField(
            model_name='status',
            name='image4',
        ),
    ]
