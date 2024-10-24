# celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BitPin.settings')

app = Celery('BitPin')

# Namespace='CELERY' means all celery-related configuration keys
# should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure the periodic task
app.conf.beat_schedule = {
    'sync-articles-every-5-minutes': {
        'task': 'your_app.tasks.sync_articles_from_redis',
        'schedule': 10.0,  # 5 minutes in seconds
    },
}

app.conf.timezone = 'UTC'
