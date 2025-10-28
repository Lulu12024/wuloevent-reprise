import os
from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand

APPS_DIR = Path(__file__).resolve().parent.parent.parent.parent

DATA_DIR = os.path.join(Path(__file__).resolve().parent.parent.parent.parent.parent, 'data')


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def handle(self, *args, **options):
        app_models_classes = []
        app_models_names = []
        apps_names = []
        models = []
        subdirectories = os.listdir(APPS_DIR)
        print(subdirectories)
        for dirname in subdirectories:
            if dirname not in ['__pycache__', 'xlib'] and os.path.isdir(os.path.join(APPS_DIR, dirname)):
                apps_names.append(dirname)
                print(dirname, 88888888888888)
                app_models_classes.extend(list(apps.get_app_config(dirname).get_models()))
                app_models_names.extend(map(lambda x: x.__name__, list(apps.get_app_config(dirname).get_models())))
                models.extend(map(lambda x: f'{dirname}.{x.__name__}', list(apps.get_app_config(dirname).get_models())))

        call_command('dumpdata', *models, '--natural-foreign', '--natural-primary', indent=2, verbosity=0,
                     output=os.path.join(DATA_DIR, 'backup.json'))

        # python manage.py dumpdata --natural-foreign --natural-primary  -e admin -e contenttypes  -e sessions -e auth.Group  -e auth.Permission --indent 2 > dump.json
