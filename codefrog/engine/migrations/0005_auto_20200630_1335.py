# Generated by Django 2.2 on 2020-06-30 13:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_project_git_branch"),
        ("engine", "0004_pullrequest"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pullrequest",
            old_name="closed_at",
            new_name="merged_at",
        ),
        migrations.RenameField(
            model_name="pullrequest",
            old_name="pr_refid",
            new_name="pull_request_refid",
        ),
        migrations.AlterUniqueTogether(
            name="pullrequest",
            unique_together={("project", "pull_request_refid")},
        ),
    ]
