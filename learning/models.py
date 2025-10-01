from django.db import models


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
    type = models.CharField(max_length=32, choices=ResourceType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    url = models.CharField(max_length=1024, null=True, blank=True)
    file = models.FileField(upload_to='resources/', null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

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


class Assignment(models.Model):
    course_section = models.ForeignKey("courses.CourseSection", on_delete=models.CASCADE, related_name="assignments")
    teacher = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    due_at = models.DateTimeField()
    max_grade = models.PositiveIntegerField(default=100, help_text="Maximum possible grade for this assignment")
    file = models.FileField(upload_to='assignments/', null=True, blank=True)

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

from django.db import models
from django.utils import timezone


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
    OTHER = "other", "Other"


class Event(models.Model):
    """Generic calendar Event used for timetable lessons and school-wide events."""
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=32, choices=EventType.choices, default=EventType.OTHER)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=255, null=True, blank=True)
    
    # Targeting
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    subject_group = models.ForeignKey("courses.SubjectGroup", on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    course_section = models.ForeignKey("courses.CourseSection", on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    
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
        ]
    
    def __str__(self) -> str:
        return f"{self.title} @ {self.start_at:%Y-%m-%d %H:%M}"
