import os

from celery import Celery

from main.tasks import update_exchange_rates

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'balance.settings')

app = Celery('balance')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    update_exchange_rates.delay()
