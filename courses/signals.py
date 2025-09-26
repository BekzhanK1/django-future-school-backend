from datetime import date, timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SubjectGroup, CourseSection


def generate_academic_year_dates(reference_date: date) -> tuple[date, date]:
    """Return (start_date, end_date) for Sep 1 to May 25 inclusive around reference_date.

    If reference_date month >= September (9), use that year as start. Otherwise, use previous year.
    """
    if reference_date.month >= 9:
        start_year = reference_date.year
    else:
        start_year = reference_date.year - 1
    start = date(start_year, 9, 1)
    end = date(start_year + 1, 5, 25)
    return start, end


@receiver(post_save, sender=SubjectGroup)
def create_default_sections_for_subject_group(sender, instance: SubjectGroup, created: bool, **kwargs):
    if not created:
        return

    # Avoid duplicate creation if already exists
    if instance.sections.exists():
        return

    # 1) Create "General" section without dates
    CourseSection.objects.create(subject_group=instance, title="Общая информация", start_date=None, end_date=None, position=0)

    # 2) Create weekly sections from Sep 1 to May 25 inclusive
    today = date.today()
    start, end = generate_academic_year_dates(today)

    # Ensure we generate ranges like 1-7, 8-14, etc. within [start, end]
    current = start
    sections_to_create: list[CourseSection] = []
    position = 2
    while current <= end:
        week_start = current
        week_end = min(week_start + timedelta(days=6), end)
        MONTHS_RU = [
            "", "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
            "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"
        ]
        title = f"{week_start.day} {MONTHS_RU[week_start.month]} - {week_end.day} {MONTHS_RU[week_end.month]}"
        sections_to_create.append(
            CourseSection(
                subject_group=instance,
                title=title,
                start_date=week_start,
                end_date=week_end,
                position=position,
            )
        )
        current = week_end + timedelta(days=1)
        position += 1

    if sections_to_create:
        CourseSection.objects.bulk_create(sections_to_create)



