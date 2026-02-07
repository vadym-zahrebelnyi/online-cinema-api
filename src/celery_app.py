from celery import Celery
from celery.schedules import crontab

from src.core.settings import settings

celery_app = Celery("worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.autodiscover_tasks(["src.accounts"])

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens-every-hour": {
        "task": "src.accounts.tasks.cleanup_expired_tokens_task",
        "schedule": crontab(minute="*"),
    },
}
