# Generated by Django 5.2 on 2025-07-18 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0072_alter_ordertracking_arriving_soon_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordertracking',
            name='completed',
            field=models.BooleanField(default=False, null=True),
        ),
    ]
