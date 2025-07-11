# Generated by Django 5.2 on 2025-06-14 19:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0028_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(blank=True, choices=[('new', 'New_Orders'), ('processing', 'Processing'), ('out_for_delivery', 'Out_for_delivery'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='new', max_length=250, null=True),
        ),
    ]
