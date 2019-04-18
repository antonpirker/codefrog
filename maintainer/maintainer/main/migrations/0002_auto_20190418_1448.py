# Generated by Django 2.1.3 on 2019-04-18 14:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='metric',
            old_name='slug',
            new_name='projet_slug',
        ),
        migrations.AlterUniqueTogether(
            name='metric',
            unique_together={('projet_slug', 'date', 'git_reference')},
        ),
    ]
