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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "classroom"], name="uq_course_classroom"),
        ]

    def __str__(self) -> str:
        return f"{self.course} / {self.classroom}"


class CourseSection(models.Model):
    subject_group = models.ForeignKey(SubjectGroup, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return self.title

from django.db import models

# Create your models here.
