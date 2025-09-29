from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


@dataclass
class EmailContent:
    subject: str
    text_body: str
    html_body: Optional[str] = None


class EmailService:
    @staticmethod
    def render_template(template_base: str, context: Mapping[str, object]) -> EmailContent:
        """
        Render a pair of templates located at templates/email/{template_base}.txt and .html
        """
        text_template = f"email/{template_base}.txt"
        html_template = f"email/{template_base}.html"
        text_body = render_to_string(text_template, context)
        try:
            html_body = render_to_string(html_template, context)
        except Exception:
            html_body = None
        subject = context.get("subject", "") or ""
        return EmailContent(subject=subject, text_body=text_body, html_body=html_body)

    @staticmethod
    def send_email(subject: str, body_text: str, to: Iterable[str], body_html: Optional[str] = None, from_email: Optional[str] = None) -> None:
        sender = from_email or settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        message = EmailMultiAlternatives(subject=subject, body=body_text, from_email=sender, to=list(to))
        if body_html:
            message.attach_alternative(body_html, "text/html")
        message.send(fail_silently=False)





