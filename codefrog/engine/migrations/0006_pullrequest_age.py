# Generated by Django 2.2 on 2020-06-30 14:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0005_auto_20200630_1335"),
    ]

    operations = [
        migrations.AddField(
            model_name="pullrequest",
            name="age",
            field=models.IntegerField(null=True),
        ),
    ]
