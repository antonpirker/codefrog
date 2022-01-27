# Generated by Django 2.2 on 2020-06-15 09:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_auto_20200615_0802"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sourcestatus",
            name="max_changes",
        ),
        migrations.RemoveField(
            model_name="sourcestatus",
            name="max_complexity",
        ),
        migrations.RemoveField(
            model_name="sourcestatus",
            name="min_changes",
        ),
        migrations.RemoveField(
            model_name="sourcestatus",
            name="min_complexity",
        ),
        migrations.AlterField(
            model_name="sourcestatus",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="source_stati",
                to="core.Project",
            ),
        ),
    ]
