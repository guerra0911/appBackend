# Generated by Django 5.0.4 on 2024-06-28 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_remove_bracket_finals_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bracket',
            name='team_size',
            field=models.IntegerField(default=16),
        ),
    ]
