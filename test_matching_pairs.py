#!/usr/bin/env python
"""
Test script to verify matching pairs question type scoring
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'future_school_backend.settings')
django.setup()

from assessments.models import Test, Question, QuestionType, Answer, Attempt
from users.models import User
from courses.models import Course, SubjectGroup, CourseSection, Classroom
from schools.models import School
from datetime import date


def test_matching_pairs_scoring():
    """Test the matching pairs scoring logic"""
    
    # Create test data
    print("Creating test data...")
    
    # Create school and classroom
    school = School.objects.create(
        name="Test School",
        city="Test City",
        country="Kazakhstan"
    )
    
    classroom = Classroom.objects.create(
        grade=10,
        letter="A",
        language="English",
        school=school
    )
    
    # Create course and subject group
    course = Course.objects.create(
        course_code="TEST101",
        name="Test Course",
        description="Test Course",
        grade=10
    )
    
    subject_group = SubjectGroup.objects.create(
        course=course,
        classroom=classroom
    )
    
    course_section = CourseSection.objects.create(
        subject_group=subject_group,
        title="Test Section",
        start_date=date.today(),
        end_date=date.today()
    )
    
    # Create teacher and student
    teacher = User.objects.create_user(
        username="test_teacher",
        email="teacher@test.com",
        password="testpass123",
        role="teacher",
        school=school
    )
    
    student = User.objects.create_user(
        username="test_student",
        email="student@test.com",
        password="testpass123",
        role="student",
        school=school
    )
    
    # Create test and question
    test = Test.objects.create(
        course_section=course_section,
        teacher=teacher,
        title="Test Matching Pairs"
    )
    
    question = Question.objects.create(
        test=test,
        type=QuestionType.MATCHING,
        text="Match countries with capitals",
        points=10,
        matching_pairs_json=[
            {"left": "France", "right": "Paris"},
            {"left": "Germany", "right": "Berlin"},
            {"left": "Spain", "right": "Madrid"},
            {"left": "Italy", "right": "Rome"}
        ]
    )
    
    # Create attempt
    attempt = Attempt.objects.create(
        test=test,
        student=student,
        attempt_number=1
    )
    
    print("\nTesting different scenarios:")
    print("=" * 50)
    
    # Test 1: All correct answers
    print("\nTest 1: All correct answers")
    answer1 = Answer.objects.create(
        attempt=attempt,
        question=question,
        matching_answers_json=[
            {"left": "France", "right": "Paris"},
            {"left": "Germany", "right": "Berlin"},
            {"left": "Spain", "right": "Madrid"},
            {"left": "Italy", "right": "Rome"}
        ]
    )
    score1 = answer1.calculate_score()
    print(f"Score: {score1}/{question.points} (Expected: 10/10)")
    assert score1 == 10, f"Expected 10, got {score1}"
    answer1.delete()
    
    # Test 2: Case insensitive matching
    print("\nTest 2: Case insensitive matching")
    answer2 = Answer.objects.create(
        attempt=attempt,
        question=question,
        matching_answers_json=[
            {"left": "france", "right": "paris"},
            {"left": "GERMANY", "right": "BERLIN"},
            {"left": "Spain", "right": "madrid"},
            {"left": "italy", "right": "ROME"}
        ]
    )
    score2 = answer2.calculate_score()
    print(f"Score: {score2}/{question.points} (Expected: 10/10)")
    assert score2 == 10, f"Expected 10, got {score2}"
    answer2.delete()
    
    # Test 3: Partial correct (3 out of 4)
    print("\nTest 3: Partial correct (3 out of 4)")
    answer3 = Answer.objects.create(
        attempt=attempt,
        question=question,
        matching_answers_json=[
            {"left": "France", "right": "Paris"},
            {"left": "Germany", "right": "Berlin"},
            {"left": "Spain", "right": "Madrid"}
        ]
    )
    score3 = answer3.calculate_score()
    print(f"Score: {score3}/{question.points} (Expected: 7.5/10)")
    assert score3 == 7.5, f"Expected 7.5, got {score3}"
    answer3.delete()
    
    # Test 4: With incorrect pairs (penalty)
    print("\nTest 4: With incorrect pairs (should have penalty)")
    answer4 = Answer.objects.create(
        attempt=attempt,
        question=question,
        matching_answers_json=[
            {"left": "France", "right": "Paris"},
            {"left": "Germany", "right": "Berlin"},
            {"left": "Spain", "right": "Rome"},  # Wrong
            {"left": "Italy", "right": "Madrid"}  # Wrong
        ]
    )
    score4 = answer4.calculate_score()
    print(f"Score: {score4}/{question.points} (Expected: 2.5/10 - 2 correct, 2 wrong with penalty)")
    expected_score4 = (2/4 - 2*0.25/4) * 10  # 2.5
    assert abs(score4 - expected_score4) < 0.01, f"Expected {expected_score4}, got {score4}"
    answer4.delete()
    
    # Test 5: Extra whitespace handling
    print("\nTest 5: Extra whitespace handling")
    answer5 = Answer.objects.create(
        attempt=attempt,
        question=question,
        matching_answers_json=[
            {"left": "  France  ", "right": "  Paris  "},
            {"left": " Germany ", "right": " Berlin "},
            {"left": "Spain   ", "right": "   Madrid"},
            {"left": "   Italy", "right": "Rome   "}
        ]
    )
    score5 = answer5.calculate_score()
    print(f"Score: {score5}/{question.points} (Expected: 10/10)")
    assert score5 == 10, f"Expected 10, got {score5}"
    answer5.delete()
    
    # Test 6: Duplicate answers (should be ignored)
    print("\nTest 6: Duplicate answers (duplicates should be ignored)")
    answer6 = Answer.objects.create(
        attempt=attempt,
        question=question,
        matching_answers_json=[
            {"left": "France", "right": "Paris"},
            {"left": "France", "right": "Paris"},  # Duplicate
            {"left": "Germany", "right": "Berlin"},
            {"left": "Spain", "right": "Madrid"},
            {"left": "Italy", "right": "Rome"}
        ]
    )
    score6 = answer6.calculate_score()
    print(f"Score: {score6}/{question.points} (Expected: 10/10)")
    assert score6 == 10, f"Expected 10, got {score6}"
    answer6.delete()
    
    # Test 7: No answers
    print("\nTest 7: No answers")
    answer7 = Answer.objects.create(
        attempt=attempt,
        question=question,
        matching_answers_json=[]
    )
    score7 = answer7.calculate_score()
    print(f"Score: {score7}/{question.points} (Expected: 0/10)")
    assert score7 == 0, f"Expected 0, got {score7}"
    answer7.delete()
    
    # Test 8: All wrong answers
    print("\nTest 8: All wrong answers")
    answer8 = Answer.objects.create(
        attempt=attempt,
        question=question,
        matching_answers_json=[
            {"left": "France", "right": "Berlin"},
            {"left": "Germany", "right": "Madrid"},
            {"left": "Spain", "right": "Rome"},
            {"left": "Italy", "right": "Paris"}
        ]
    )
    score8 = answer8.calculate_score()
    print(f"Score: {score8}/{question.points} (Expected: 0/10)")
    assert score8 == 0, f"Expected 0, got {score8}"
    answer8.delete()
    
    print("\n" + "=" * 50)
    print("All tests passed! ✅")
    
    # Cleanup
    print("\nCleaning up test data...")
    attempt.delete()
    question.delete()
    test.delete()
    student.delete()
    teacher.delete()
    course_section.delete()
    subject_group.delete()
    course.delete()
    classroom.delete()
    school.delete()
    
    print("Done!")


if __name__ == "__main__":
    test_matching_pairs_scoring()