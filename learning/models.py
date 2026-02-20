from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class ResourceType(models.TextChoices):
    FILE = "file", "File"
    LINK = "link", "Link"
    DIRECTORY = "directory", "Directory"
    TEXT = "text", "Text"
    VIDEO = "video", "Video"
    AUDIO = "audio", "Audio"
    IMAGE = "image", "Image"
    PDF = "pdf", "PDF"
    WORD = "word", "Word"
    EXCEL = "excel", "Excel"
    POWERPOINT = "powerpoint", "Powerpoint"
    LESSON_LINK = "lesson_link", "Lesson Link"


class Resource(models.Model):
    course_section = models.ForeignKey("courses.CourseSection", on_delete=models.CASCADE, related_name="resources")
    parent_resource = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    # Optional link to template resource from which this one was cloned
    template_resource = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_resources",
        help_text="Template resource this resource was cloned from (if any).",
    )
    type = models.CharField(max_length=32, choices=ResourceType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    url = models.CharField(max_length=1024, null=True, blank=True)
    file = models.FileField(upload_to='resources/', null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    # If true, this resource will no longer be auto-synced with its template
    is_unlinked_from_template = models.BooleanField(
        default=False,
        help_text="If true, this resource is no longer auto-synced from its template.",
    )
    is_visible_to_students = models.BooleanField(
        default=True,
        help_text="If false, this resource is visible only to teachers, school admins, and super admins.",
    )

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        # Auto-increment position within (course_section, parent_resource)
        if not self.position or self.position == 0:
            siblings = Resource.objects.filter(course_section=self.course_section, parent_resource=self.parent_resource)
            max_pos = siblings.aggregate(models.Max('position'))['position__max'] or 0
            self.position = max_pos + 1
        super().save(*args, **kwargs)
    
    def delete_with_children(self):
        """
        Custom method to delete this resource and all its children recursively.
        This provides explicit control over the deletion process.
        """
        if self.type == 'directory':
            # Delete all children first (this will trigger CASCADE automatically)
            children = self.children.all()
            for child in children:
                if child.type == 'directory':
                    child.delete_with_children()  # Recursive call for subdirectories
                else:
                    child.delete()  # This will trigger the signals
        
        # Delete this resource (will trigger signals for file cleanup)
        self.delete()


class Assignment(models.Model):
    course_section = models.ForeignKey("courses.CourseSection", on_delete=models.CASCADE, related_name="assignments")
    # Optional link to template assignment this one was cloned from
    template_assignment = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_assignments",
        help_text="Template assignment this assignment was cloned from (if any).",
    )
    teacher = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    due_at = models.DateTimeField()
    # Template-relative scheduling: offset from section.start_date + time of day
    template_offset_days_from_section_start = models.IntegerField(
        null=True,
        blank=True,
        help_text="Offset in days from section start date to assignment due date (for templates).",
    )
    template_due_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of day for assignment due datetime (for templates).",
    )
    max_grade = models.PositiveIntegerField(default=100, help_text="Maximum possible grade for this assignment")
    file = models.FileField(upload_to='assignments/', null=True, blank=True)
    # If true, this assignment will no longer be auto-synced with its template
    is_unlinked_from_template = models.BooleanField(
        default=False,
        help_text="If true, this assignment is no longer auto-synced from its template.",
    )

    def __str__(self) -> str:
        return self.title


class AssignmentAttachmentType(models.TextChoices):
    TEXT = "text", "Text"
    FILE = "file", "File"
    LINK = "link", "Link"


class AssignmentAttachment(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="attachments")
    type = models.CharField(max_length=32, choices=AssignmentAttachmentType.choices)
    title = models.CharField(max_length=255)
    content = models.TextField(null=True, blank=True)  # For text content or file URLs
    file_url = models.URLField(null=True, blank=True)  # For file URLs
    file = models.FileField(upload_to='assignment_attachments/', null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self) -> str:
        return f"{self.assignment.title} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.position or self.position == 0:
            siblings = AssignmentAttachment.objects.filter(assignment=self.assignment)
            max_pos = siblings.aggregate(models.Max('position'))['position__max'] or 0
            self.position = max_pos + 1
        super().save(*args, **kwargs)


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="submissions")
    submitted_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField(null=True, blank=True)  # Keep for backward compatibility
    file = models.FileField(upload_to='submissions/', null=True, blank=True)

    def __str__(self) -> str:
        return f"Submission {self.id}"


class SubmissionAttachmentType(models.TextChoices):
    TEXT = "text", "Text"
    FILE = "file", "File"
    LINK = "link", "Link"


class SubmissionAttachment(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="attachments")
    type = models.CharField(max_length=32, choices=SubmissionAttachmentType.choices)
    title = models.CharField(max_length=255)
    content = models.TextField(null=True, blank=True)  # For text content or file URLs
    file_url = models.URLField(null=True, blank=True)  # For file URLs
    file = models.FileField(upload_to='submission_attachments/', null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self) -> str:
        return f"{self.submission} - {self.title}"

    def save(self, *args, **kwargs):
        # Auto-increment position within submission
        if not self.position or self.position == 0:
            siblings = SubmissionAttachment.objects.filter(submission=self.submission)
            max_pos = siblings.aggregate(models.Max('position'))['position__max'] or 0
            self.position = max_pos + 1
        super().save(*args, **kwargs)


class Grade(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="grade")
    graded_by = models.ForeignKey("users.User", on_delete=models.CASCADE)
    grade_value = models.PositiveIntegerField()
    feedback = models.TextField(null=True, blank=True)
    graded_at = models.DateTimeField(auto_now_add=True)


class ManualGradeType(models.TextChoices):
    """Тип ручной оценки: за урок, контрольная оффлайн, устный ответ и т.д."""
    LESSON = "lesson", "На уроке"
    OFFLINE_TEST = "offline_test", "Контрольная работа (оффлайн)"
    ORAL = "oral", "Устный ответ"
    OTHER = "other", "Другое"


class ManualGrade(models.Model):
    """
    Оценка, выставленная учителем вручную: за урок, за контрольную оффлайн,
    за устный ответ и т.д. Не привязана к заданию или тесту в системе.
    """
    student = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="manual_grades"
    )
    subject_group = models.ForeignKey(
        "courses.SubjectGroup", on_delete=models.CASCADE, related_name="manual_grades"
    )
    course_section = models.ForeignKey(
        "courses.CourseSection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_grades",
        help_text="Тема/раздел (опционально).",
    )
    value = models.PositiveIntegerField(help_text="Балл (например 5 или 85).")
    max_value = models.PositiveIntegerField(
        default=100,
        help_text="Максимум баллов (5 для 5-балльной шкалы, 100 для 100-балльной).",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Краткое название (например «Контрольная №2», «Ответ на уроке»).",
    )
    grade_type = models.CharField(
        max_length=32,
        choices=ManualGradeType.choices,
        default=ManualGradeType.OTHER,
    )
    graded_by = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="given_manual_grades"
    )
    graded_at = models.DateTimeField(default=timezone.now)
    feedback = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-graded_at", "id"]
        indexes = [
            models.Index(fields=["student", "subject_group"]),
            models.Index(fields=["subject_group", "graded_at"]),
        ]

    def __str__(self):
        return f"{self.student.username}: {self.value}/{self.max_value} ({self.title or self.get_grade_type_display()})"


class GradeWeightSourceType(models.TextChoices):
    """Тип источника оценки для веса."""
    ASSIGNMENT = "assignment", "Задание"
    TEST = "test", "Тест"
    MANUAL = "manual", "Ручная оценка"


class GradeWeight(models.Model):
    """
    Вес типа оценки по предметной группе в процентах (0–100).
    Сумма весов по трём типам (задание, тест, ручная) должна быть 100%.
    """
    subject_group = models.ForeignKey(
        "courses.SubjectGroup", on_delete=models.CASCADE, related_name="grade_weights"
    )
    source_type = models.CharField(
        max_length=32,
        choices=GradeWeightSourceType.choices,
        help_text="Тип оценки: задание, тест или ручная.",
    )
    weight = models.PositiveSmallIntegerField(
        default=34,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Вес в процентах (0–100). Сумма по трём типам = 100%.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subject_group", "source_type"],
                name="unique_subject_group_source_type",
            ),
        ]
        ordering = ["subject_group", "source_type"]

    def __str__(self):
        return f"{self.subject_group} / {self.get_source_type_display()}: {self.weight}"


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    EXCUSED = "excused", "Excused"
    NOT_PRESENT = "not_present", "Not Present"


class Attendance(models.Model):
    """Represents an attendance session for a subject group"""
    subject_group = models.ForeignKey("courses.SubjectGroup", on_delete=models.CASCADE, related_name="attendances")
    taken_by = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="taken_attendances")
    taken_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(null=True, blank=True, help_text="Optional notes about the attendance session")
    
    class Meta:
        ordering = ['-taken_at']
        indexes = [
            models.Index(fields=['subject_group', 'taken_at']),
            models.Index(fields=['taken_by', 'taken_at']),
        ]
    
    def __str__(self) -> str:
        return f"Attendance for {self.subject_group} on {self.taken_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def total_students(self):
        """Total number of students in the classroom"""
        return self.subject_group.classroom.classroom_users.filter(user__role='student').count()
    
    @property
    def present_count(self):
        """Number of students marked as present"""
        return self.records.filter(status=AttendanceStatus.PRESENT).count()
    
    @property
    def excused_count(self):
        """Number of students marked as excused"""
        return self.records.filter(status=AttendanceStatus.EXCUSED).count()
    
    @property
    def not_present_count(self):
        """Number of students marked as not present"""
        return self.records.filter(status=AttendanceStatus.NOT_PRESENT).count()
    
    @property
    def attendance_percentage(self):
        """Calculate attendance percentage (present + excused / total)"""
        if self.total_students == 0:
            return 0
        return round(((self.present_count + self.excused_count) / self.total_students) * 100, 2)


class AttendanceRecord(models.Model):
    """Individual student attendance record within an attendance session"""
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name="records")
    student = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="attendance_records")
    status = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.NOT_PRESENT)
    notes = models.TextField(null=True, blank=True, help_text="Optional notes about this student's attendance")
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['attendance', 'student'], name='unique_attendance_student'),
        ]
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self) -> str:
        return f"{self.student.username} - {self.get_status_display()} on {self.attendance.taken_at.strftime('%Y-%m-%d')}"


# Create your models here.


class EventType(models.TextChoices):
    LESSON = "lesson", "Lesson"
    SCHOOL_EVENT = "school_event", "School Event"
    MEETING = "meeting", "Meeting"
    GATHERING = "gathering", "Gathering"
    OTHER = "other", "Other"


class EventTargetAudience(models.TextChoices):
    """Кому показывать событие: все, только учителя, класс, выбранные пользователи."""
    ALL = "all", "All"
    TEACHERS = "teachers", "Teachers"
    CLASS = "class", "Class"
    SPECIFIC = "specific", "Specific"


class Event(models.Model):
    """Generic calendar Event used for timetable lessons and school-wide events."""
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=32, choices=EventType.choices, default=EventType.OTHER)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=255, null=True, blank=True)
    
    # Targeting: кто видит событие
    target_audience = models.CharField(
        max_length=32,
        choices=EventTargetAudience.choices,
        default=EventTargetAudience.ALL,
    )
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    subject_group = models.ForeignKey("courses.SubjectGroup", on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    course_section = models.ForeignKey("courses.CourseSection", on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    target_users = models.ManyToManyField(
        "users.User",
        related_name="targeted_events",
        blank=True,
        help_text="Для target_audience=specific: кому показывать событие.",
    )
    
    # Audit
    created_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["start_at", "id"]
        indexes = [
            models.Index(fields=["type", "start_at"]),
            models.Index(fields=["school", "start_at"]),
            models.Index(fields=["subject_group", "start_at"]),
            models.Index(fields=["course_section", "start_at"]),
            models.Index(fields=["target_audience", "start_at"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.title} @ {self.start_at:%Y-%m-%d %H:%M}"
