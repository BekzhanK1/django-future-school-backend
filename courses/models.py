import uuid
from django.db import models


class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    grade = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(grade__gte=0) & models.Q(grade__lte=12), name="check_course_grade_range"),
        ]

    def __str__(self) -> str:
        return f"{self.course_code} - {self.name}"


class SubjectGroup(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="subject_groups")
    classroom = models.ForeignKey("schools.Classroom", on_delete=models.CASCADE, related_name="subject_groups")
    teacher = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="subject_groups")
    external_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "classroom"], name="uq_course_classroom"),
        ]

    def save(self, *args, **kwargs):
        if not self.external_id:
            self.external_id = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.course} / {self.classroom}"


class CourseSection(models.Model):
    """
    Course section can be:
    - template section for a Course (course is set, subject_group is null)
    - concrete section for a SubjectGroup (subject_group is set, course is null)
    Concrete sections can optionally point to their template_section.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="template_sections",
        help_text="Set for template sections that belong to a Course (not a specific SubjectGroup).",
    )
    subject_group = models.ForeignKey(
        SubjectGroup,
        on_delete=models.CASCADE,
        related_name="sections",
        null=True,
        blank=True,
        help_text="Set for concrete sections of a specific SubjectGroup.",
    )
    # Optional link to a template section this section was derived from
    template_section = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_sections",
        help_text="Template section this section was derived from (if any).",
    )

    title = models.CharField(max_length=255)
    is_general = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Template-relative scheduling (used only when this is a template section for a Course)
    template_week_index = models.IntegerField(
        null=True,
        blank=True,
        help_text="Week index in the academic year (0 = first week). "
                  "Used to calculate start_date relative to academic_start_date.",
    )
    template_start_offset_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Alternative to week index: offset in days from academic_start_date.",
    )
    template_duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of the section in days (e.g. 7 for a week).",
    )

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        if self.subject_group:
            return f"{self.title} - {self.subject_group}"
        if self.course:
            return f"{self.title} - {self.course} (template)"
        return self.title

    def save(self, *args, **kwargs):
        # Auto-increment position within subject_group or course (for templates)
        if not self.position or self.position == 0:
            if self.subject_group:
                siblings = CourseSection.objects.filter(subject_group=self.subject_group)
            else:
                siblings = CourseSection.objects.filter(course=self.course, subject_group__isnull=True)
            max_pos = siblings.aggregate(models.Max("position"))["position__max"] or 0
            self.position = max_pos + 1
        super().save(*args, **kwargs)

from django.db import models

# Create your models here.
