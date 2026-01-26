"""
Helper functions for creating notifications.
"""
from typing import Optional, List
from django.contrib.auth import get_user_model
from .models_notifications import Notification, NotificationType

User = get_user_model()


def create_notification(
    user: User,
    notification_type: str,
    title: str,
    message: str = "",
    triggered_by: Optional[User] = None,
    related_assignment=None,
    related_test=None,
    related_forum_thread=None,
    related_forum_post=None,
) -> Notification:
    """
    Create a notification for a user.

    Args:
        user: The user to notify
        notification_type: Type of notification (from NotificationType)
        title: Title of the notification
        message: Optional message/description
        triggered_by: User who triggered the notification
        related_assignment: Related Assignment object
        related_test: Related Test object
        related_forum_thread: Related ForumThread object
        related_forum_post: Related ForumPost object

    Returns:
        Created Notification instance
    """
    return Notification.objects.create(
        user=user,
        type=notification_type,
        title=title,
        message=message,
        triggered_by=triggered_by,
        related_assignment=related_assignment,
        related_test=related_test,
        related_forum_thread=related_forum_thread,
        related_forum_post=related_forum_post,
    )


def notify_new_assignment(assignment, students: List[User], teacher: User):
    """Notify students about a new assignment"""
    notifications = []
    for student in students:
        notification = create_notification(
            user=student,
            notification_type=NotificationType.NEW_ASSIGNMENT,
            title=f"Новое задание: {assignment.title}",
            message=f"Преподаватель {teacher.get_full_name() or teacher.username} опубликовал новое задание.",
            triggered_by=teacher,
            related_assignment=assignment,
        )
        notifications.append(notification)
    return notifications


def notify_assignment_graded(submission, student: User, teacher: User):
    """Notify student that their assignment was graded"""
    grade_value = submission.grade_value
    max_grade = submission.assignment.max_points
    return create_notification(
        user=student,
        notification_type=NotificationType.ASSIGNMENT_GRADED,
        title=f"Задание оценено: {submission.assignment.title}",
        message=f"Вы получили {grade_value}/{max_grade} баллов.",
        triggered_by=teacher,
        related_assignment=submission.assignment,
    )


def notify_new_test(test, students: List[User], teacher: User):
    """Notify students about a new test"""
    notifications = []
    for student in students:
        notification = create_notification(
            user=student,
            notification_type=NotificationType.NEW_TEST,
            title=f"Новый тест: {test.title}",
            message=f"Преподаватель {teacher.get_full_name() or teacher.username} опубликовал новый тест.",
            triggered_by=teacher,
            related_test=test,
        )
        notifications.append(notification)
    return notifications


def notify_test_available(test, students: List[User], teacher: User):
    """Notify students that a test is now available"""
    notifications = []
    for student in students:
        notification = create_notification(
            user=student,
            notification_type=NotificationType.TEST_AVAILABLE,
            title=f"Тест доступен: {test.title}",
            message=f"Тест '{test.title}' теперь доступен для прохождения.",
            triggered_by=teacher,
            related_test=test,
        )
        notifications.append(notification)
    return notifications


def notify_test_graded(attempt, student: User, teacher: User):
    """Notify student that their test was graded"""
    score = attempt.score
    max_score = attempt.test.max_score
    return create_notification(
        user=student,
        notification_type=NotificationType.TEST_GRADED,
        title=f"Тест оценён: {attempt.test.title}",
        message=f"Вы получили {score}/{max_score} баллов за тест.",
        triggered_by=teacher,
        related_test=attempt.test,
    )


def notify_forum_reply(post, thread_author: User, reply_author: User):
    """Notify thread author about a reply"""
    return create_notification(
        user=thread_author,
        notification_type=NotificationType.FORUM_REPLY,
        title=f"Новый ответ в теме: {post.thread.title}",
        message=f"{reply_author.get_full_name() or reply_author.username} ответил на ваш вопрос.",
        triggered_by=reply_author,
        related_forum_thread=post.thread,
        related_forum_post=post,
    )


def notify_forum_question(thread, student: User, teacher: User):
    """Notify teacher about a new question from a student"""
    return create_notification(
        user=teacher,
        notification_type=NotificationType.FORUM_QUESTION,
        title=f"Новый вопрос: {thread.title}",
        message=f"{student.get_full_name() or student.username} задал новый вопрос.",
        triggered_by=student,
        related_forum_thread=thread,
    )


def notify_forum_resolved(thread, resolved_by: User):
    """Notify thread author that their question was marked as resolved"""
    return create_notification(
        user=thread.created_by,
        notification_type=NotificationType.FORUM_RESOLVED,
        title=f"Вопрос решён: {thread.title}",
        message=f"Ваш вопрос был отмечен как решённый.",
        triggered_by=resolved_by,
        related_forum_thread=thread,
    )
