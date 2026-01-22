from datetime import date, timedelta, datetime

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

<<<<<<< HEAD
from .models import Course, SubjectGroup, CourseSection
from learning.models import Resource, Assignment, AssignmentAttachment
=======
from .models import SubjectGroup, CourseSection, Course
>>>>>>> 12b6ca4 (small fixes)


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


<<<<<<< HEAD
def clone_resource_tree(template_res: Resource, target_section: CourseSection, parent: Resource | None):
    """
    Recursively clone a template resource and its children into target_section.
    """
    clone = Resource.objects.create(
        course_section=target_section,
        parent_resource=parent,
        template_resource=template_res,
        type=template_res.type,
        title=template_res.title,
        description=template_res.description,
        url=template_res.url,
        file=template_res.file,
        position=template_res.position,
    )

    # Clone children
    for child in template_res.children.all().order_by("position", "id"):
        clone_resource_tree(child, target_section, clone)

    return clone
=======
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
>>>>>>> 12b6ca4 (small fixes)


@receiver(post_save, sender=Course)
def create_default_template_sections_for_course(sender, instance: Course, created: bool, **kwargs):
<<<<<<< HEAD
    """
    When a Course is created, automatically create default template sections (weekly sections)
    for the academic year.
    """
=======
    """Create default template sections for a course when it's created."""
>>>>>>> 12b6ca4 (small fixes)
    if not created:
        return
    
    # Avoid duplicate creation if template sections already exist
    if instance.template_sections.exists():
        return
    
    # Calculate academic year dates
    today = date.today()
    start, end = generate_academic_year_dates(today)
    
    # Calculate academic year start date for template_week_index
    if today.month >= 9:
        academic_start_year = today.year
    else:
        academic_start_year = today.year - 1
    academic_start_date = date(academic_start_year, 9, 1)
    
    # Create "General" section
    CourseSection.objects.create(
        course=instance,
        subject_group=None,
        title="Общая информация",
        is_general=True,
        start_date=None,
        end_date=None,
        position=0,
        template_week_index=None,
        template_start_offset_days=None,
        template_duration_days=None,
    )
    
    # Create weekly template sections
    current = start
    sections_to_create: list[CourseSection] = []
    week_index = 0
    position = 1
    
    while current <= end:
        week_start = current
        week_end = min(week_start + timedelta(days=6), end)
        
        MONTHS_RU = [
            "", "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
            "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"
        ]
        title = f"{week_start.day} {MONTHS_RU[week_start.month]} - {week_end.day} {MONTHS_RU[week_end.month]}"
        
        # Calculate template_week_index (weeks from academic start)
        days_from_start = (week_start - academic_start_date).days
        template_week_index = days_from_start // 7
        
        sections_to_create.append(
            CourseSection(
                course=instance,
                subject_group=None,
                title=title,
                is_general=False,
                start_date=week_start,  # Keep absolute dates for reference
                end_date=week_end,
                position=position,
                template_week_index=template_week_index,
                template_start_offset_days=days_from_start,
                template_duration_days=7,
            )
        )
        current = week_end + timedelta(days=1)
        week_index += 1
        position += 1
    
    if sections_to_create:
        CourseSection.objects.bulk_create(sections_to_create)


@receiver(post_save, sender=SubjectGroup)
def handle_subject_group_changes(sender, instance: SubjectGroup, created: bool, **kwargs):
    """
    When a SubjectGroup is created, copy all template sections, resources, and assignments
    from the course to this SubjectGroup. The SubjectGroup then lives independently.
    
    When a SubjectGroup is updated (e.g., teacher changed), update assignments that were
    created without a specific teacher to use SubjectGroup's teacher.
    """
    if not created:
        # On update, update assignments that use SubjectGroup's teacher
        _update_assignments_teacher(instance)
        return

    # Avoid duplicate creation if template sections already exist
    if instance.template_sections.exists():
        return

<<<<<<< HEAD
    course = instance.course
    
    # Get template sections for this course (subject_group is null)
    template_sections = CourseSection.objects.filter(
        course=course,
        subject_group__isnull=True,
    ).order_by("position", "id")

    if not template_sections.exists():
        # If no template sections, create default sections
        today = date.today()
        start, end = generate_academic_year_dates(today)

        # Create "General" section
        CourseSection.objects.create(
            subject_group=instance,
            title="Общая информация",
            start_date=None,
            end_date=None,
            position=0
        )
        
        # Create weekly sections
        current = start
        sections_to_create: list[CourseSection] = []
        position = 1
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
        return

    # Calculate academic year start date
    today = date.today()
    if today.month >= 9:
        academic_start_year = today.year
    else:
        academic_start_year = today.year - 1
    academic_start_date = date(academic_start_year, 9, 1)

    # Copy each template section
    for tmpl_sec in template_sections:
        # Determine offset in days from academic_start_date
        offset_days = None
        if tmpl_sec.template_start_offset_days is not None:
            offset_days = tmpl_sec.template_start_offset_days
        elif tmpl_sec.template_week_index is not None:
            offset_days = tmpl_sec.template_week_index * 7

        # Calculate dates
        start_date = None
        end_date = None
        if offset_days is not None:
            start_date = academic_start_date + timedelta(days=offset_days)
            duration = tmpl_sec.template_duration_days or 7
            end_date = start_date + timedelta(days=duration - 1)
        elif tmpl_sec.start_date and tmpl_sec.end_date:
            # Fallback: copy absolute dates if template-relative data is missing
            start_date = tmpl_sec.start_date
            end_date = tmpl_sec.end_date

        # Create derived section
        derived_sec = CourseSection.objects.create(
            subject_group=instance,
            template_section=tmpl_sec,
            course=None,
            title=tmpl_sec.title,
            is_general=tmpl_sec.is_general,
            position=tmpl_sec.position,
            start_date=start_date,
            end_date=end_date,
        )

        # Copy resources: clone template resources into derived section
        tmpl_resources = Resource.objects.filter(
            course_section=tmpl_sec,
            parent_resource__isnull=True,
        ).order_by("position", "id")

        for tmpl_res in tmpl_resources:
            clone_resource_tree(tmpl_res, derived_sec, parent=None)

        # Copy assignments: clone template assignments
        tmpl_assignments = Assignment.objects.filter(
            course_section=tmpl_sec,
            template_assignment__isnull=True,  # Only copy root template assignments
        ).order_by("due_at", "id")
        
        for tmpl_asg in tmpl_assignments:
            # Calculate due_at based on template-relative fields if available
            due_at = tmpl_asg.due_at
            if (
                derived_sec.start_date
                and tmpl_asg.template_offset_days_from_section_start is not None
                and tmpl_asg.template_due_time is not None
            ):
                due_date = derived_sec.start_date + timedelta(
                    days=tmpl_asg.template_offset_days_from_section_start
                )
                due_at = datetime.combine(
                    due_date,
                    tmpl_asg.template_due_time,
                    tzinfo=timezone.get_current_timezone(),
                )

            # Use SubjectGroup's teacher if template assignment has no teacher
            teacher = tmpl_asg.teacher or instance.teacher
            if not teacher:
                # Skip assignment if no teacher is available
                continue
                
            derived_asg = Assignment.objects.create(
                course_section=derived_sec,
                template_assignment=tmpl_asg,
                teacher=teacher,
                title=tmpl_asg.title,
                description=tmpl_asg.description,
                due_at=due_at,
                max_grade=tmpl_asg.max_grade,
                file=tmpl_asg.file,
            )
            
            # Clone attachments
            for att in tmpl_asg.attachments.all().order_by("position", "id"):
                AssignmentAttachment.objects.create(
                    assignment=derived_asg,
                    type=att.type,
                    title=att.title,
                    content=att.content,
                    file_url=att.file_url,
                    file=att.file,
                    position=att.position,
                )


def _update_assignments_teacher(instance: SubjectGroup):
    """
    Update assignments that were created without a specific teacher to use SubjectGroup's teacher.
    Only update assignments where teacher matches the old teacher or assignments created by the teacher.
    """
    if not instance.teacher:
        return
    
    # Update assignments in all sections of this SubjectGroup
    # Update assignments that don't have template_assignment (teacher's own assignments)
    # to use the new teacher
    from learning.models import Assignment
    
    # Get all sections for this SubjectGroup
    sections = CourseSection.objects.filter(subject_group=instance)
    
    # Update assignments that are not linked to template (teacher's own assignments)
    # These should follow the SubjectGroup's teacher
    for section in sections:
        Assignment.objects.filter(
            course_section=section,
            template_assignment__isnull=True  # Teacher's own assignments
        ).update(teacher=instance.teacher)
        
        # For template-based assignments, we keep the original teacher from the template
        # unless they were explicitly assigned to the SubjectGroup's teacher
        # This preserves the template structure while allowing customization


@receiver(post_save, sender=Resource)
def propagate_template_resource_to_subject_groups(sender, instance: Resource, created: bool, **kwargs):
    """
    When a resource is created in a template section, copy it to all existing SubjectGroups
    that use this course template.
    """
    if not created:
        return
    
    # Skip if this resource is already a clone (has template_resource)
    if instance.template_resource_id:
        return
    
    section = instance.course_section
    
    # Check if this is a template section (has course but no subject_group)
    if not section.course or section.subject_group:
        return
    
    # Find all SubjectGroups using this course
    subject_groups = SubjectGroup.objects.filter(course=section.course)
    
    for sg in subject_groups:
        # Find the corresponding derived section for this SubjectGroup
        derived_section = CourseSection.objects.filter(
            subject_group=sg,
            template_section=section,
        ).first()
        
        if not derived_section:
            continue
        
        # Check if resource already exists (avoid duplicates)
        existing = Resource.objects.filter(
            course_section=derived_section,
            template_resource=instance,
        ).first()
        
        if existing:
            continue
        
        # Clone the resource
        clone_resource_tree(instance, derived_section, parent=None)


@receiver(post_save, sender=Assignment)
def propagate_template_assignment_to_subject_groups(sender, instance: Assignment, created: bool, **kwargs):
    """
    When an assignment is created in a template section, copy it to all existing SubjectGroups
    that use this course template.
    """
    if not created:
        return
    
    section = instance.course_section
    
    # Check if this is a template section (has course but no subject_group)
    if not section.course or section.subject_group:
        return
    
    # Only copy root template assignments (not ones that are already clones)
    if instance.template_assignment_id:
        return
    
    # Find all SubjectGroups using this course
    subject_groups = SubjectGroup.objects.filter(course=section.course)
    
    for sg in subject_groups:
        # Find the corresponding derived section for this SubjectGroup
        derived_section = CourseSection.objects.filter(
            subject_group=sg,
            template_section=section,
        ).first()
        
        if not derived_section:
            continue
        
        # Check if assignment already exists (avoid duplicates)
        existing = Assignment.objects.filter(
            course_section=derived_section,
            template_assignment=instance,
        ).first()
        
        if existing:
            continue
        
        # Calculate due_at based on template-relative fields if available
        due_at = instance.due_at
        if (
            derived_section.start_date
            and instance.template_offset_days_from_section_start is not None
            and instance.template_due_time is not None
        ):
            due_date = derived_section.start_date + timedelta(
                days=instance.template_offset_days_from_section_start
            )
            due_at = datetime.combine(
                due_date,
                instance.template_due_time,
                tzinfo=timezone.get_current_timezone(),
            )
        
        # Use SubjectGroup's teacher if template assignment has no teacher
        teacher = instance.teacher or sg.teacher
        if not teacher:
            continue
        
        # Clone the assignment
        derived_asg = Assignment.objects.create(
            course_section=derived_section,
            template_assignment=instance,
            teacher=teacher,
            title=instance.title,
            description=instance.description,
            due_at=due_at,
            max_grade=instance.max_grade,
            file=instance.file,
        )
        
        # Clone attachments
        for att in instance.attachments.all().order_by("position", "id"):
            AssignmentAttachment.objects.create(
                assignment=derived_asg,
                type=att.type,
                title=att.title,
                content=att.content,
                file_url=att.file_url,
                file=att.file,
                position=att.position,
            )


=======
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
>>>>>>> 12b6ca4 (small fixes)
