# Generated by Django 5.0.4 on 2024-06-28 02:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0015_bracket_tournament'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bracket',
            name='tournament',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brackets', to='api.tournament'),
        ),
    ]
