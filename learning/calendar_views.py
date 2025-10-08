from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q

from .models import Assignment
from assessments.models import Test
from schools.permissions import IsTeacherOrAbove


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_events(request):
    """
    Get calendar events (assignments and tests) for the authenticated user
    """
    user = request.user
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # Default to current month if no dates provided
    if not start_date:
        start_date = timezone.now().replace(day=1).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = start_date.replace(month=start_date.month + 1) - timedelta(days=1)
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    events = []
    
    # Get assignments
    if user.role in ['superadmin', 'schooladmin', 'teacher']:
        # Teachers and admins see all assignments
        assignments = Assignment.objects.filter(
            due_at__date__range=[start_date, end_date]
        ).select_related('course_section__subject_group__course', 'teacher')
    else:
        # Students see assignments for their courses
        student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
        assignments = Assignment.objects.filter(
            course_section__subject_group__course__in=student_courses,
            due_at__date__range=[start_date, end_date]
        ).select_related('course_section__subject_group__course', 'teacher')
    
    for assignment in assignments:
        events.append({
            'id': f'assignment_{assignment.id}',
            'title': assignment.title,
            'type': 'assignment',
            'start': assignment.due_at.isoformat(),
            'end': assignment.due_at.isoformat(),
            'course_name': assignment.course_section.subject_group.course.name,
            'course_code': assignment.course_section.subject_group.course.course_code,
            'teacher': assignment.teacher.username,
            'description': assignment.description,
            'url': f'/api/assignments/{assignment.id}/',
        })
    
    # Get tests
    if user.role in ['superadmin', 'schooladmin', 'teacher']:
        # Teachers and admins see all tests
        tests = Test.objects.filter(
            Q(start_date__date__range=[start_date, end_date]) |
            Q(end_date__date__range=[start_date, end_date]) |
            Q(reveal_results_at__date__range=[start_date, end_date])
        ).select_related('course_section__subject_group__course', 'teacher')
    else:
        # Students see tests for their courses
        student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
        tests = Test.objects.filter(
            Q(course_section__subject_group__course__in=student_courses) &
            (Q(start_date__date__range=[start_date, end_date]) |
             Q(end_date__date__range=[start_date, end_date]) |
             Q(reveal_results_at__date__range=[start_date, end_date]))
        ).select_related('course_section__subject_group__course', 'teacher')
    
    for test in tests:
        # Test start event
        if test.start_date and start_date <= test.start_date.date() <= end_date:
            events.append({
                'id': f'test_start_{test.id}',
                'title': f'{test.title} (Starts)',
                'type': 'test_start',
                'start': test.start_date.isoformat(),
                'end': test.start_date.isoformat(),
                'course_name': test.course_section.subject_group.course.name,
                'course_code': test.course_section.subject_group.course.course_code,
                'teacher': test.teacher.username,
                'description': test.description,
                'url': f'/api/tests/{test.id}/',
            })
        
        # Test end event
        if test.end_date and start_date <= test.end_date.date() <= end_date:
            events.append({
                'id': f'test_end_{test.id}',
                'title': f'{test.title} (Ends)',
                'type': 'test_end',
                'start': test.end_date.isoformat(),
                'end': test.end_date.isoformat(),
                'course_name': test.course_section.subject_group.course.name,
                'course_code': test.course_section.subject_group.course.course_code,
                'teacher': test.teacher.username,
                'description': test.description,
                'url': f'/api/tests/{test.id}/',
            })
        
        # Test results reveal event
        if test.reveal_results_at and start_date <= test.reveal_results_at.date() <= end_date:
            events.append({
                'id': f'test_results_{test.id}',
                'title': f'{test.title} (Results)',
                'type': 'test_results',
                'start': test.reveal_results_at.isoformat(),
                'end': test.reveal_results_at.isoformat(),
                'course_name': test.course_section.subject_group.course.name,
                'course_code': test.course_section.subject_group.course.course_code,
                'teacher': test.teacher.username,
                'description': 'Test results will be revealed',
                'url': f'/api/tests/{test.id}/',
            })
    
    # Sort events by start time
    events.sort(key=lambda x: x['start'])
    
    return Response({
        'events': events,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def upcoming_events(request):
    """
    Get upcoming events for the next 7 days
    """
    user = request.user
    today = timezone.now().date()
    next_week = today + timedelta(days=7)
    
    # Get assignments due in next 7 days
    if user.role in ['superadmin', 'schooladmin', 'teacher']:
        assignments = Assignment.objects.filter(
            due_at__date__range=[today, next_week]
        ).select_related('course_section__subject_group__course', 'teacher')
    else:
        student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
        assignments = Assignment.objects.filter(
            course_section__subject_group__course__in=student_courses,
            due_at__date__range=[today, next_week]
        ).select_related('course_section__subject_group__course', 'teacher')
    
    # Get tests in next 7 days
    if user.role in ['superadmin', 'schooladmin', 'teacher']:
        tests = Test.objects.filter(
            Q(start_date__date__range=[today, next_week]) |
            Q(end_date__date__range=[today, next_week]) |
            Q(reveal_results_at__date__range=[today, next_week])
        ).select_related('course_section__subject_group__course', 'teacher')
    else:
        student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
        tests = Test.objects.filter(
            Q(course_section__subject_group__course__in=student_courses) &
            (Q(start_date__date__range=[today, next_week]) |
             Q(end_date__date__range=[today, next_week]) |
             Q(reveal_results_at__date__range=[today, next_week]))
        ).select_related('course_section__subject_group__course', 'teacher')

    upcoming = []
    for assignment in assignments:
        upcoming.append({
            'id': f'assignment_{assignment.id}',
            'title': assignment.title,
            'type': 'assignment',
            'due_at': assignment.due_at.isoformat(),
            'course_name': assignment.course_section.subject_group.course.name,
            'days_until': (assignment.due_at.date() - today).days,
        })
    
    for test in tests:
        if test.start_date and today <= test.start_date.date() <= next_week:
            upcoming.append({
                'id': f'test_{test.id}',
                'title': test.title,
                'type': 'test',
                'due_at': test.start_date.isoformat(),
                'course_name': test.course_section.subject_group.course.name,
                'days_until': (test.start_date.date() - today).days,
            })
    
    # Sort by due date
    upcoming.sort(key=lambda x: x['due_at'])
    
    return Response({
        'upcoming': upcoming,
        'count': len(upcoming),
    })
