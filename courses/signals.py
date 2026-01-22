from datetime import date, timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SubjectGroup, CourseSection, Course


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
    """
    Disabled: Automatic section creation for SubjectGroup.
    Sections should be created either:
    1. Via sync_content endpoint (from template sections)
    2. Manually by teachers/admins
    """
    # Disabled to prevent duplicate sections and give more control
    return


@receiver(post_save, sender=Course)
def create_default_template_sections_for_course(sender, instance: Course, created: bool, **kwargs):
    """Create default template sections for a course when it's created."""
    if not created:
        return
    
    # Avoid duplicate creation if template sections already exist
    if instance.template_sections.exists():
        return
    
    # 1) Create "General" template section without dates
    CourseSection.objects.create(
        course=instance,
        subject_group=None,
        title="Общая информация",
        is_general=True,
        position=0,
        template_week_index=None,
        template_start_offset_days=None,
        template_duration_days=None,
    )

    # 2) Create weekly template sections for academic year (Sep 1 to May 25)
    # Use template_week_index to indicate which week of the academic year
    # This allows dates to be calculated later during sync based on academic_start_date
    start, end = generate_academic_year_dates(date.today())
    
    # Calculate number of weeks
    current = start
    sections_to_create: list[CourseSection] = []
    position = 1
    week_index = 0
    
    while current <= end:
        week_start = current
        week_end = min(week_start + timedelta(days=6), end)
        
        MONTHS_RU = [
            "", "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
            "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"
        ]
        title = f"Неделя {week_index + 1}: {week_start.day} {MONTHS_RU[week_start.month]} - {week_end.day} {MONTHS_RU[week_end.month]}"
        
        sections_to_create.append(
            CourseSection(
                course=instance,
                subject_group=None,
                title=title,
                is_general=False,
                position=position,
                template_week_index=week_index,
                template_start_offset_days=None,
                template_duration_days=7,
            )
        )
        current = week_end + timedelta(days=1)
        position += 1
        week_index += 1

    if sections_to_create:
        CourseSection.objects.bulk_create(sections_to_create)
