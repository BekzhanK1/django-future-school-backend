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
    # Use attempt.max_score if stored; otherwise fall back to total_points over questions
    max_score = getattr(attempt, "max_score", None)
    if max_score is None:
        # total_points is a @property on Test summing question.points
        max_score = getattr(attempt.test, "total_points", None)
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


def notify_manual_grade(manual_grade, student: User, teacher: User):
    """Notify student about a new manual grade from teacher"""
    msg = f"Вы получили оценку {manual_grade.value}"
    if manual_grade.feedback:
        msg += f". {manual_grade.feedback}"
    return create_notification(
        user=student,
        notification_type=NotificationType.MANUAL_GRADE,
        title=f"Новая оценка: {manual_grade.title or 'Оценка'}",
        message=msg,
        triggered_by=teacher,
    )


def notify_new_event(event, users: List[User], created_by: User):
    """Notify users about a new calendar event"""
    notifications = []
    msg = "Добавлено в календарь."
    if event.description:
        msg = event.description[:200] + "..." if len(event.description) > 200 else event.description
    for u in users:
        if u.id == created_by.id:
            continue
        notifications.append(
            create_notification(
                user=u,
                notification_type=NotificationType.NEW_EVENT,
                title=f"Новое событие: {event.title}",
                message=msg,
                triggered_by=created_by,
            )
        )
    return notifications


def notify_forum_announcement(thread, students: List[User], teacher: User):
    """Notify students when teacher publishes an announcement"""
    notifications = []
    for student in students:
        notifications.append(
            create_notification(
                user=student,
                notification_type=NotificationType.FORUM_ANNOUNCEMENT,
                title=f"Объявление: {thread.title}",
                message=f"Преподаватель {teacher.get_full_name() or teacher.username} опубликовал объявление.",
                triggered_by=teacher,
                related_forum_thread=thread,
            )
        )
    return notifications


def notify_direct_message_new_thread(thread, recipients: List[User], sender: User):
    """Notify participants when someone starts a new direct message thread"""
    notifications = []
    sender_name = sender.get_full_name() or sender.username
    for user in recipients:
        if user.id == sender.id:
            continue
        notifications.append(
            create_notification(
                user=user,
                notification_type=NotificationType.FORUM_DIRECT_MESSAGE,
                title=f"Новое сообщение: {thread.title}",
                message=f"{sender_name} начал(а) переписку с вами.",
                triggered_by=sender,
                related_forum_thread=thread,
            )
        )
    return notifications


def notify_direct_message_reply(post, recipients: List[User], reply_author: User):
    """Notify other participants when someone replies in a direct message thread"""
    notifications = []
    author_name = reply_author.get_full_name() or reply_author.username
    preview = (post.content[:100] + "…") if len(post.content) > 100 else post.content
    for user in recipients:
        if user.id == reply_author.id:
            continue
        notifications.append(
            create_notification(
                user=user,
                notification_type=NotificationType.FORUM_DIRECT_MESSAGE,
                title=f"Новое сообщение: {post.thread.title}",
                message=f"{author_name}: {preview}",
                triggered_by=reply_author,
                related_forum_thread=post.thread,
                related_forum_post=post,
            )
        )
    return notifications
