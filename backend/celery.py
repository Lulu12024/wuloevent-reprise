# -*- coding: utf-8 -*-
import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from celery import Celery

def detect_tasks(project_root):
    tasks = []
    file_path = os.path.join(project_root, 'apps')
    for root, dirs, files in os.walk(file_path):
        for filename in files:
            if os.path.basename(root) == 'tasks':
                if filename != '__init__.py' and filename.endswith('.py'):
                    task = os.path.join(root, filename) \
                        .replace(os.path.dirname(project_root) + '/', '') \
                        .replace('/', '.') \
                        .replace('.py', '')
                    tasks.append(task)
    return tuple(tasks)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
app = Celery("wuloevents_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


def revoke_task(task_uuid: str):
    print("Revoke task: ", task_uuid)
    return app.control.revoke(task_uuid, terminate=True)
