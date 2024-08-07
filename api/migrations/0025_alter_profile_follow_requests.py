# Generated by Django 5.0.4 on 2024-07-07 02:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0024_profile_follow_requests'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='follow_requests',
            field=models.ManyToManyField(blank=True, related_name='requested_by', to='api.profile'),
        ),
    ]
