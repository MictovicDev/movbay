# Generated by Django 5.2 on 2025-07-18 17:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0073_ordertracking_completed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='amount',
            field=models.PositiveBigIntegerField(blank=True, default=0, null=True),
        ),
    ]
