from django.db import models
from django.core.exceptions import ValidationError


class DayOfWeek(models.IntegerChoices):
    """Days of the week (Monday = 0, Sunday = 6)"""
    MONDAY = 0, "Понедельник"
    TUESDAY = 1, "Вторник"
    WEDNESDAY = 2, "Среда"
    THURSDAY = 3, "Четверг"
    FRIDAY = 4, "Пятница"
    SATURDAY = 5, "Суббота"
    SUNDAY = 6, "Воскресенье"


class ScheduleSlot(models.Model):
    """
    Represents a time slot for a SubjectGroup.
    Allows flexible scheduling with different times for different days.
    """
    subject_group = models.ForeignKey(
        'courses.SubjectGroup',
        on_delete=models.CASCADE,
        related_name='schedule_slots'
    )
    
    day_of_week = models.IntegerField(
        choices=DayOfWeek.choices,
        help_text="Day of the week (0=Monday, 6=Sunday)"
    )
    
    start_time = models.TimeField(
        help_text="Start time of the lesson (e.g., 09:00)"
    )
    
    end_time = models.TimeField(
        help_text="End time of the lesson (e.g., 10:30)"
    )
    
    # Optional: classroom/room number
    room = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional room/classroom number"
    )
    
    # Optional: date range for this schedule slot
    # If null, the schedule applies indefinitely
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional start date for this schedule slot"
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional end date for this schedule slot"
    )
    
    # Quarter: 1, 2, 3, 4, or null for all quarters
    quarter = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(1, '1 четверть'), (2, '2 четверть'), (3, '3 четверть'), (4, '4 четверть')],
        help_text="Quarter this schedule applies to (null = all quarters)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        # Ensure no overlapping slots for the same subject_group on the same day
        constraints = [
            models.UniqueConstraint(
                fields=['subject_group', 'day_of_week', 'start_time'],
                name='unique_slot_per_day_time'
            )
        ]
        indexes = [
            models.Index(fields=['subject_group', 'day_of_week']),
        ]
    
    def clean(self):
        """Validate that end_time is after start_time"""
        if self.end_time and self.start_time:
            if self.end_time <= self.start_time:
                raise ValidationError({
                    'end_time': 'End time must be after start time.'
                })
        
        if self.end_date and self.start_date:
            if self.end_date < self.start_date:
                raise ValidationError({
                    'end_date': 'End date must be after or equal to start date.'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        day_name = self.get_day_of_week_display()
        return f"{self.subject_group} - {day_name} {self.start_time}-{self.end_time}"
