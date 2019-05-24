# Generated by Django 2.2 on 2019-05-24 08:00

from django.db import migrations

def up(apps, schema_editor):
    Project = apps.get_model('core', 'Project')

    Project.objects.create(
        name='Requests',
        slug='requests',
        git_url='https://github.com/kennethreitz/requests.git',
        external_services={
            'github_issues': {
                'owner': 'kennethreitz',
                'repo': 'requests'
            },
        },
    )

    Project.objects.create(
        name='Flask',
        slug='flask',
        git_url='https://github.com/pallets/flask.git',
        external_services={
            'github_issues': {
                'owner': 'pallets',
                'repo': 'flask'
            },
        },
    )

    Project.objects.create(
        name='Keras',
        slug='keras',
        git_url='https://github.com/keras-team/keras.git',
        external_services={
            'github_issues': {
                'owner': 'keras-team',
                'repo': 'keras'
            },
        },
    )

    Project.objects.create(
        name='React',
        slug='react',
        git_url='https://github.com/facebook/react.git',
        external_services={
            'github_issues': {
                'owner': 'facebook',
                'repo': 'react'
            },
        },
    )

    Project.objects.create(
        name='Kubernetes',
        slug='kubernetes',
        git_url='https://github.com/kubernetes/kubernetes.git',
        external_services={
            'github_issues': {
                'owner': 'kubernetes',
                'repo': 'kubernetes'
            },
        },
    )

    Project.objects.create(
        name='Visual Studio Code',
        slug='vscode',
        git_url='https://github.com/Microsoft/vscode.git',
        external_services={
            'github_issues': {
                'owner': 'Microsoft',
                'repo': 'vscode'
            },
        },
    )

    Project.objects.create(
        name='Atom Text Editor',
        slug='atom',
        git_url='https://github.com/atom/atom.git',
        external_services={
            'github_issues': {
                'owner': 'atom',
                'repo': 'atom'
            },
        },
    )

    Project.objects.create(
        name='Ruby on Rails',
        slug='rails',
        git_url='https://github.com/rails/rails.git',
        external_services={
            'github_issues': {
                'owner': 'rails',
                'repo': 'rails'
            },
        },
    )


def down(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(up, reverse_code=down),
    ]
