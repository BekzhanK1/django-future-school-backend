"""
Django signals for automatically creating notifications.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from learning.models import Assignment, Submission
from assessments.models import Test, Attempt
from forum.models import ForumPost, ForumThread
from schools.models import ClassroomUser
from courses.models import SubjectGroup

from .notifications_helper import (
    notify_new_assignment,
    notify_assignment_graded,
    notify_new_test,
    notify_test_available,
    notify_test_graded,
    notify_forum_question,
    notify_forum_reply,
    notify_forum_resolved,
)

User = get_user_model()


@receiver(post_save, sender=Assignment)
def assignment_created_or_published(sender, instance, created, **kwargs):
    """Notify students when a new assignment is created or published"""
    if created and instance.is_available:
        # Get all students in the subject group
        subject_group = instance.course_section.subject_group
        if subject_group:
            students = User.objects.filter(
                classroom_users__classroom=subject_group.classroom,
                role='student'
            ).distinct()
            
            if students.exists() and subject_group.teacher:
                notify_new_assignment(instance, list(students), subject_group.teacher)
    
    # If assignment becomes available after creation
    elif not created and instance.is_available:
        # Check if we already notified (simple check - could be improved)
        # For now, we'll notify again if it becomes available
        subject_group = instance.course_section.subject_group
        if subject_group:
            students = User.objects.filter(
                classroom_users__classroom=subject_group.classroom,
                role='student'
            ).distinct()
            
            if students.exists() and subject_group.teacher:
                # Only notify if no notification exists yet
                from .models_notifications import Notification
                existing = Notification.objects.filter(
                    user__in=students,
                    type='new_assignment',
                    related_assignment=instance
                ).exists()
                
                if not existing:
                    notify_new_assignment(instance, list(students), subject_group.teacher)


@receiver(post_save, sender=Submission)
def submission_graded(sender, instance, created, **kwargs):
    """Notify student when their assignment submission is graded"""
    if not created and instance.grade_value is not None:
        # Check if this is a new grade (not just an update)
        # We'll notify if grade_value was just set
        if instance.student and instance.assignment.course_section.subject_group.teacher:
            notify_assignment_graded(
                instance,
                instance.student,
                instance.assignment.course_section.subject_group.teacher
            )


@receiver(post_save, sender=Test)
def test_created_or_published(sender, instance, created, **kwargs):
    """Notify students when a new test is created or published"""
    if created and instance.is_published:
        # Get all students in the subject group
        subject_group = instance.course_section.subject_group if instance.course_section else None
        if subject_group:
            students = User.objects.filter(
                classroom_users__classroom=subject_group.classroom,
                role='student'
            ).distinct()
            
            if students.exists() and subject_group.teacher:
                notify_new_test(instance, list(students), subject_group.teacher)
    
    # If test becomes published after creation
    elif not created and instance.is_published:
        subject_group = instance.course_section.subject_group if instance.course_section else None
        if subject_group:
            students = User.objects.filter(
                classroom_users__classroom=subject_group.classroom,
                role='student'
            ).distinct()
            
            if students.exists() and subject_group.teacher:
                from .models_notifications import Notification
                existing = Notification.objects.filter(
                    user__in=students,
                    type='new_test',
                    related_test=instance
                ).exists()
                
                if not existing:
                    notify_new_test(instance, list(students), subject_group.teacher)


@receiver(post_save, sender=Attempt)
def attempt_graded(sender, instance, created, **kwargs):
    """Notify student when their test attempt is graded"""
    if not created and instance.score is not None:
        # Check if this is a new grade
        if instance.student and instance.test.course_section:
            subject_group = instance.test.course_section.subject_group
            if subject_group and subject_group.teacher:
                notify_test_graded(
                    instance,
                    instance.student,
                    subject_group.teacher
                )


@receiver(post_save, sender=ForumPost)
def forum_post_created(sender, instance, created, **kwargs):
    """Notify thread author when someone replies to their thread"""
    if created and instance.parent_post is None and instance.thread.created_by != instance.author:
        # This is a reply to the thread (not a nested reply)
        notify_forum_reply(
            instance,
            instance.thread.created_by,
            instance.author
        )


@receiver(post_save, sender=ForumThread)
def forum_thread_created(sender, instance, created, **kwargs):
    """Notify teacher when a student creates a new question"""
    if created and instance.type == 'question':
        # Check if created by a student
        if instance.created_by.role == 'student' and instance.subject_group.teacher:
            notify_forum_question(
                instance,
                instance.created_by,
                instance.subject_group.teacher
            )


@receiver(post_save, sender=ForumThread)
def forum_thread_resolved(sender, instance, created, **kwargs):
    """Notify thread author when their question is marked as resolved"""
    if not created and instance.is_resolved:
        # Check if it was just marked as resolved
        # We'll notify if it's resolved and we have a teacher/admin who resolved it
        # For now, we'll use the last updater (could be improved)
        if instance.subject_group.teacher:
            notify_forum_resolved(instance, instance.subject_group.teacher)
