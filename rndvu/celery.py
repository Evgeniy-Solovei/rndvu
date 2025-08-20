import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rndvu.settings')

app = Celery('rndvu')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True, task_time_limit=6000, task_soft_time_limit=5800)
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
