from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class AcademicYear(models.Model):
    """
    Represents an academic year with quarters and holidays.
    Default: September 1 - May 25, 4 quarters (8+8+10+8 weeks)
    """
    name = models.CharField(
        max_length=100,
        help_text="e.g., '2024-2025 учебный год'"
    )
    start_date = models.DateField(
        help_text="Start of academic year (typically September 1)"
    )
    end_date = models.DateField(
        help_text="End of academic year (typically May 25)"
    )
    
    # Quarters are now managed by the Quarter model and its objects

    
    # Holidays
    autumn_holiday_start = models.DateField(
        null=True,
        blank=True,
        help_text="Autumn holiday start (default: Oct 27)"
    )
    autumn_holiday_end = models.DateField(
        null=True,
        blank=True,
        help_text="Autumn holiday end (default: Nov 2)"
    )
    
    winter_holiday_start = models.DateField(
        null=True,
        blank=True,
        help_text="Winter holiday start (default: Dec 29)"
    )
    winter_holiday_end = models.DateField(
        null=True,
        blank=True,
        help_text="Winter holiday end (default: Jan 7)"
    )
    
    spring_holiday_start = models.DateField(
        null=True,
        blank=True,
        help_text="Spring holiday start (default: Mar 19)"
    )
    spring_holiday_end = models.DateField(
        null=True,
        blank=True,
        help_text="Spring holiday end (default: Mar 29)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this is the current active academic year"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Academic Year"
        verbose_name_plural = "Academic Years"
    
    def clean(self):
        """Validate dates"""
        if self.end_date and self.start_date:
            if self.end_date <= self.start_date:
                raise ValidationError({
                    'end_date': 'End date must be after start date.'
                })
        
        # Validate holiday dates
        holidays = [
            (self.autumn_holiday_start, self.autumn_holiday_end, 'autumn'),
            (self.winter_holiday_start, self.winter_holiday_end, 'winter'),
            (self.spring_holiday_start, self.spring_holiday_end, 'spring'),
        ]
        
        for start, end, name in holidays:
            if start and end:
                if end < start:
                    raise ValidationError({
                        f'{name}_holiday_end': f'{name.capitalize()} holiday end must be after start.'
                    })
                if start < self.start_date or end > self.end_date:
                    raise ValidationError({
                        f'{name}_holiday_start': f'{name.capitalize()} holiday must be within academic year.'
                    })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        # If this is set as active, deactivate others
        if self.is_active:
            AcademicYear.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    def get_quarter_dates(self, quarter: int):
        """Calculate start and end dates for a quarter"""
        if quarter < 1 or quarter > 4:
            raise ValueError("Quarter must be between 1 and 4")
            
        try:
            q_obj = self.quarters.get(quarter_index=quarter)
            return q_obj.start_date, q_obj.end_date
        except:
            return None, None
    
    def is_holiday(self, date):
        """Check if a date is a holiday"""
        holidays = [
            (self.autumn_holiday_start, self.autumn_holiday_end),
            (self.winter_holiday_start, self.winter_holiday_end),
            (self.spring_holiday_start, self.spring_holiday_end),
        ]
        
        for start, end in holidays:
            if start and end and start <= date <= end:
                return True
        return False
    
    def is_weekend(self, date):
        """Check if a date is a weekend (Saturday=5, Sunday=6)"""
        return date.weekday() >= 5
    
    def is_working_day(self, date):
        """Check if a date is a working day (not holiday and not weekend)"""
        return not self.is_holiday(date) and not self.is_weekend(date)
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"


class Quarter(models.Model):
    """
    Represents a specific quarter within an academic year.
    """
    QUARTER_CHOICES = [
        (1, '1 четверть'),
        (2, '2 четверть'),
        (3, '3 четверть'),
        (4, '4 четверть'),
    ]

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='quarters'
    )
    quarter_index = models.PositiveSmallIntegerField(
        choices=QUARTER_CHOICES,
        help_text="Quarter index (1 to 4)"
    )
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ['academic_year', 'quarter_index']
        unique_together = ['academic_year', 'quarter_index']
        verbose_name = "Quarter"
        verbose_name_plural = "Quarters"

    def clean(self):
        if self.end_date and self.start_date:
            if self.end_date <= self.start_date:
                raise ValidationError({
                    'end_date': 'End date must be after start date.'
                })
            # Ensure within academic year
            if self.academic_year:
                if self.start_date < self.academic_year.start_date or self.end_date > self.academic_year.end_date:
                    raise ValidationError(
                        "Quarter dates must be within the academic year bounds."
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_quarter_index_display()} - {self.academic_year.name}"


class Holiday(models.Model):
    """
    Additional holidays that can be added to any academic year.
    Useful for flexible holiday management.
    """
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='additional_holidays',
        null=True,
        blank=True,
        help_text="If null, applies to all academic years"
    )
    name = models.CharField(
        max_length=100,
        help_text="Holiday name (e.g., 'День Независимости')"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_recurring = models.BooleanField(
        default=False,
        help_text="If true, this holiday repeats every year"
    )
    
    class Meta:
        ordering = ['start_date']
    
    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'End date must be after or equal to start date.'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
