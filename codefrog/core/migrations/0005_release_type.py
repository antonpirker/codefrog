# Generated by Django 2.2 on 2019-05-31 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_release'),
    ]

    operations = [
        migrations.AddField(
            model_name='release',
            name='type',
            field=models.CharField(default='git_tag', max_length=20),
        ),
    ]