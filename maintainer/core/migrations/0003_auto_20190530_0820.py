# Generated by Django 2.2 on 2019-05-30 08:20

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_data_sample_projects'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='metric',
            name='authors',
        ),
        migrations.RemoveField(
            model_name='metric',
            name='git_reference',
        ),
        migrations.AddField(
            model_name='metric',
            name='file_path',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='metric',
            name='metrics',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
    ]
