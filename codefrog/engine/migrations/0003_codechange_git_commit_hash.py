# Generated by Django 2.2 on 2020-06-11 14:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0002_codechange_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="codechange",
            name="git_commit_hash",
            field=models.CharField(default="", max_length=255),
        ),
    ]
