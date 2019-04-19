# Generated by Django 2.2 on 2019-04-19 19:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_auto_20190419_1033'),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeMetric',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_slug', models.CharField(max_length=30)),
                ('date', models.DateField()),
                ('git_reference', models.CharField(max_length=30)),
                ('complexity', models.IntegerField(null=True)),
                ('loc', models.IntegerField(null=True)),
            ],
            options={
                'unique_together': {('project_slug', 'date', 'git_reference')},
            },
        ),
        migrations.CreateModel(
            name='ExternalMetric',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_slug', models.CharField(max_length=30)),
                ('date', models.DateField()),
                ('jira_bug_issues', models.IntegerField(null=True)),
                ('gitlab_bug_issues', models.IntegerField(null=True)),
                ('sentry_errors', models.IntegerField(null=True)),
            ],
            options={
                'unique_together': {('project_slug', 'date')},
            },
        ),
        migrations.DeleteModel(
            name='Metric',
        ),
    ]
