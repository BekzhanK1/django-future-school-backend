from __future__ import annotations

from celery import shared_task

from .email_service import EmailService


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_email_task(self, subject: str, body_text: str, recipients: list[str], body_html: str | None = None) -> None:
    EmailService.send_email(subject=subject, body_text=body_text, body_html=body_html, to=recipients)





