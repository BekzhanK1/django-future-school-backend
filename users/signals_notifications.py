"""
Django signals for automatically creating notifications.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from learning.models import Assignment, Submission, Grade
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
    notify_forum_announcement,
    notify_direct_message_reply,
)

User = get_user_model()


@receiver(post_save, sender=Assignment)
def assignment_created_or_published(sender, instance, created, **kwargs):
    """Notify students when a new assignment is created"""
    from django.utils import timezone

    # Check if assignment is available (due_at is in the future or not set)
    is_available = not instance.due_at or timezone.now() < instance.due_at

    # Only notify for non-template assignments (subject_group must exist)
    subject_group = instance.course_section.subject_group if instance.course_section else None
    if not subject_group:
        return  # Template assignment, skip notification

    if created and is_available:
        # Get all students in the subject group
        students = User.objects.filter(
            classroom_users__classroom=subject_group.classroom,
            role='student'
        ).distinct()

        if students.exists() and subject_group.teacher:
            notify_new_assignment(instance, list(
                students), subject_group.teacher)

    # If assignment becomes available after creation (due_at was changed to future)
    elif not created and is_available:
        # Check if we already notified
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
                notify_new_assignment(instance, list(
                    students), subject_group.teacher)


@receiver(post_save, sender=Grade)
def grade_created_or_updated(sender, instance, created, **kwargs):
    """Notify student when their assignment submission is graded (via Grade model)"""
    try:
        submission = instance.submission
        student = submission.student
        subject_group = submission.assignment.course_section.subject_group if submission.assignment.course_section else None
        teacher = subject_group.teacher if subject_group else None
        if student and teacher:
            notify_assignment_graded(instance.submission, student, instance.graded_by)
    except Exception:
        pass


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
                notify_new_test(instance, list(students),
                                subject_group.teacher)

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
                    notify_new_test(instance, list(students),
                                    subject_group.teacher)


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
    """Notify on reply: in direct_message notify all other participants; else notify thread author or parent post author"""
    if not created:
        return
    thread = instance.thread
    if thread.type == "direct_message":
        participants = list(thread.participants.all())
        if not participants:
            return
        if instance.author_id in [p.id for p in participants]:
            notify_direct_message_reply(instance, participants, instance.author)
        return
    if instance.author_id == thread.created_by_id:
        return
    if instance.parent_post_id:
        parent_author = instance.parent_post.author
        if parent_author.id != instance.author_id:
            notify_forum_reply(instance, parent_author, instance.author)
    else:
        notify_forum_reply(instance, thread.created_by, instance.author)


@receiver(post_save, sender=ForumThread)
def forum_thread_created(sender, instance, created, **kwargs):
    """Notify: question (student/parent)→teacher; announcement→students; announcement_to_parents→parents. direct_message is notified from serializer after participants are set."""
    if not created:
        return
    if instance.type == "question" and instance.subject_group and instance.subject_group.teacher:
        if instance.created_by.role in ("student", "parent"):
            notify_forum_question(
                instance,
                instance.created_by,
                instance.subject_group.teacher,
            )
        return
    if instance.type == "announcement" and instance.subject_group:
        students = User.objects.filter(
            classroom_users__classroom=instance.subject_group.classroom,
            role='student'
        ).distinct()
        if students.exists() and instance.subject_group.teacher:
            notify_forum_announcement(instance, list(students), instance.subject_group.teacher)
    elif instance.type == 'announcement_to_parents' and instance.subject_group:
        from schools.models import ClassroomUser
        student_ids = ClassroomUser.objects.filter(
            classroom=instance.subject_group.classroom
        ).values_list('user_id', flat=True)
        parents = User.objects.filter(
            children__in=student_ids,
            role='parent'
        ).distinct()
        if parents.exists() and instance.subject_group.teacher:
            notify_forum_announcement(instance, list(parents), instance.subject_group.teacher)


@receiver(post_save, sender=ForumThread)
def forum_thread_resolved(sender, instance, created, **kwargs):
    """Notify thread author when their question is marked as resolved"""
    if not created and instance.is_resolved:
        # Check if it was just marked as resolved
        # We'll notify if it's resolved and we have a teacher/admin who resolved it
        # For now, we'll use the last updater (could be improved)
        if instance.subject_group.teacher:
            notify_forum_resolved(instance, instance.subject_group.teacher)
