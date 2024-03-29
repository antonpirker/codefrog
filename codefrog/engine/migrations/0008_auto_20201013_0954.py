# Generated by Django 2.2 on 2020-10-13 09:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0007_codechange_issue"),
    ]

    operations = [
        migrations.AlterField(
            model_name="codechange",
            name="issue",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="code_change",
                to="engine.Issue",
            ),
        ),
        migrations.AlterField(
            model_name="codechange",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="code_changes",
                to="core.Project",
            ),
        ),
    ]
