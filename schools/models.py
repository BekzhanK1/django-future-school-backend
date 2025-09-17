from django.db import models


class School(models.Model):
    name = models.CharField(max_length=255, unique=True)
    city = models.CharField(max_length=255)
    country = models.CharField(max_length=255, default="Kazakhstan")
    logo_url = models.URLField(null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=64, null=True, blank=True)
    kundelik_id = models.CharField(max_length=255, unique=True, null=True, blank=True, db_index=True)

    def __str__(self) -> str:
        return self.name


class Classroom(models.Model):
    grade = models.PositiveSmallIntegerField()
    letter = models.CharField(max_length=1)
    language = models.CharField(max_length=50)
    kundelik_id = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="classrooms")

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(grade__gte=0) & models.Q(grade__lte=12), name="check_grade_range"),
            models.UniqueConstraint(fields=["school", "grade", "letter"], name="uq_classroom_per_school"),
        ]

    def __str__(self) -> str:
        return f"{self.grade}{self.letter} - {self.school.name}"


class ClassroomUser(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="classroom_users")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="classroom_users")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["classroom", "user"], name="_class_user_uc"),
        ]

from django.db import models

# Create your models here.
