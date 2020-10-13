# Generated by Django 2.2 on 2020-10-13 11:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0010_pullrequest_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='category',
            field=models.CharField(choices=[('bug', 'Bug-Fix'), ('change', 'Change')], default='change', max_length=20),
        ),
        migrations.AddField(
            model_name='pullrequest',
            name='category',
            field=models.CharField(choices=[('bug', 'Bug-Fix'), ('change', 'Change')], default='change', max_length=20),
        ),
    ]
