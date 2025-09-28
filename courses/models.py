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
    subject_group = models.ForeignKey(SubjectGroup, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=255)
    is_general = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.title} - {self.subject_group}"

    def save(self, *args, **kwargs):
        # Auto-increment position within subject_group
        if not self.position or self.position == 0:
            siblings = CourseSection.objects.filter(subject_group=self.subject_group)
            max_pos = siblings.aggregate(models.Max('position'))['position__max'] or 0
            self.position = max_pos + 1
        super().save(*args, **kwargs)

from django.db import models

# Create your models here.
