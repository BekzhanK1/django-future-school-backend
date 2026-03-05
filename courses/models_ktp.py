from django.db import models
from django.core.validators import MinValueValidator

class AcademicPlan(models.Model):
    """
    Root document for a Course's Calendar-Thematic Plan (KTP).
    """
    course = models.ForeignKey(
        'courses.Course', 
        on_delete=models.CASCADE, 
        related_name='academic_plans'
    )
    teacher_name = models.CharField(max_length=255)
    academic_year = models.CharField(max_length=100, help_text="e.g., '2025-2026'")
    school_name = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.name} - {self.teacher_name} ({self.academic_year})"


class PlanSubjectGroup(models.Model):
    """
    Links a KTP to specific SubjectGroups (representing actual classes like 5A, 5B).
    """
    plan = models.ForeignKey(
        AcademicPlan, 
        on_delete=models.CASCADE, 
        related_name='plan_subject_groups'
    )
    subject_group = models.ForeignKey(
        'courses.SubjectGroup', 
        on_delete=models.CASCADE, 
        related_name='ktp_links'
    )

    class Meta:
        unique_together = ['plan', 'subject_group']

    def __str__(self):
        return f"{self.plan} -> {self.subject_group}"


class PlanQuarterDetail(models.Model):
    """
    Quarter-specific details for an Academic Plan.
    """
    plan = models.ForeignKey(
        AcademicPlan, 
        on_delete=models.CASCADE, 
        related_name='quarter_details'
    )
    quarter = models.ForeignKey(
        'courses.Quarter', 
        on_delete=models.CASCADE, 
        related_name='plan_details'
    )
    sor_count = models.PositiveIntegerField(default=0)
    soch_count = models.PositiveIntegerField(default=0)
    total_hours = models.PositiveIntegerField()

    class Meta:
        unique_together = ['plan', 'quarter']

    def __str__(self):
        return f"{self.plan} - {self.quarter.get_quarter_index_display()}"


class Section(models.Model):
    """
    Sections (topics/units) within a Quarter for a KTP.
    """
    plan_quarter_detail = models.ForeignKey(
        PlanQuarterDetail, 
        on_delete=models.CASCADE, 
        related_name='sections'
    )
    section_name = models.CharField(max_length=255)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.section_name


class LearningObjective(models.Model):
    """
    Global dictionary of educational objectives (e.g., "5.1.1.1").
    """
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField()

    def __str__(self):
        return f"{self.code} - {self.description[:50]}"


class Lesson(models.Model):
    """
    Individual lesson inside a Section.
    """
    section = models.ForeignKey(
        Section, 
        on_delete=models.CASCADE, 
        related_name='lessons'
    )
    lesson_number = models.PositiveIntegerField()
    topic = models.CharField(max_length=255)
    hours = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    scheduled_date = models.DateField(null=True, blank=True)
    is_summative = models.BooleanField(default=False, help_text="True if this lesson is a SOR or SOCH")
    
    objectives = models.ManyToManyField(
        LearningObjective, 
        related_name='lessons', 
        blank=True
    )

    class Meta:
        ordering = ['lesson_number']

    def __str__(self):
        return f"Lesson {self.lesson_number}: {self.topic}"
