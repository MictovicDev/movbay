# Generated by Django 5.2 on 2025-07-18 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0071_ordertracking_driver'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ordertracking',
            name='arriving_soon',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='ordertracking',
            name='new',
            field=models.BooleanField(default=True),
        ),
    ]
