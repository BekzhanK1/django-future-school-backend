from django.test import TestCase
from django.utils import timezone
from datetime import date, datetime, timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from courses.models import Course, SubjectGroup, CourseSection
from schools.models import School, Classroom
from assessments.models import Test
from assessments.serializers import CreateTestSerializer, TestSerializer

User = get_user_model()


class TestAutoCourseSectionAssignment(APITestCase):
    def setUp(self):
        """Set up test data"""
        # Create school
        self.school = School.objects.create(
            name="Test School",
            city="Test City",
            country="Kazakhstan"
        )
        
        # Create classroom
        self.classroom = Classroom.objects.create(
            grade=10,
            letter="A",
            language="Kazakh",
            school=self.school
        )
        
        # Create course
        self.course = Course.objects.create(
            course_code="MATH101",
            name="Mathematics",
            description="Basic Mathematics",
            grade=10
        )
        
        # Create subject group
        self.subject_group = SubjectGroup.objects.create(
            course=self.course,
            classroom=self.classroom
        )
        
        # Create course sections with different date ranges
        self.section1 = CourseSection.objects.create(
            subject_group=self.subject_group,
            title="First Quarter",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31)
        )
        
        self.section2 = CourseSection.objects.create(
            subject_group=self.subject_group,
            title="Second Quarter",
            start_date=date(2024, 4, 1),
            end_date=date(2024, 6, 30)
        )
        
        self.section3 = CourseSection.objects.create(
            subject_group=self.subject_group,
            title="Third Quarter",
            start_date=date(2024, 7, 1),
            end_date=date(2024, 9, 30)
        )
        
        # Create teacher user
        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="testpass123",
            role="teacher",
            school=self.school
        )
    
    def test_auto_assign_course_section_by_date(self):
        """Test that course section is automatically assigned based on scheduled_at date"""
        # Test data for a test scheduled in the first quarter
        test_data = {
            'title': 'Math Test 1',
            'description': 'First quarter math test',
            'scheduled_at': datetime(2024, 2, 15, 10, 0),  # Within first quarter
            'is_published': False,
            'teacher': self.teacher.id
        }
        
        serializer = CreateTestSerializer(data=test_data, context={'request': type('obj', (object,), {'user': self.teacher})()})
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        test = serializer.save()
        
        # Verify that the test was assigned to the correct course section
        self.assertEqual(test.course_section, self.section1)
        self.assertEqual(test.title, 'Math Test 1')
    
    def test_auto_assign_course_section_second_quarter(self):
        """Test auto-assignment for second quarter"""
        test_data = {
            'title': 'Math Test 2',
            'description': 'Second quarter math test',
            'scheduled_at': datetime(2024, 5, 20, 14, 30),  # Within second quarter
            'is_published': False,
            'teacher': self.teacher.id
        }
        
        serializer = CreateTestSerializer(data=test_data, context={'request': type('obj', (object,), {'user': self.teacher})()})
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        test = serializer.save()
        
        # Verify that the test was assigned to the second quarter section
        self.assertEqual(test.course_section, self.section2)
    
    def test_auto_assign_course_section_third_quarter(self):
        """Test auto-assignment for third quarter"""
        test_data = {
            'title': 'Math Test 3',
            'description': 'Third quarter math test',
            'scheduled_at': datetime(2024, 8, 10, 9, 0),  # Within third quarter
            'is_published': False,
            'teacher': self.teacher.id
        }
        
        serializer = CreateTestSerializer(data=test_data, context={'request': type('obj', (object,), {'user': self.teacher})()})
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        test = serializer.save()
        
        # Verify that the test was assigned to the third quarter section
        self.assertEqual(test.course_section, self.section3)
    
    def test_no_course_section_found_for_date(self):
        """Test error when no course section is found for the given date"""
        test_data = {
            'title': 'Math Test 4',
            'description': 'Test with no matching section',
            'scheduled_at': datetime(2024, 12, 15, 10, 0),  # Outside all quarters
            'is_published': False,
            'teacher': self.teacher.id
        }
        
        serializer = CreateTestSerializer(data=test_data, context={'request': type('obj', (object,), {'user': self.teacher})()})
        self.assertFalse(serializer.is_valid())
        self.assertIn('No course section found for the scheduled date', str(serializer.errors))
    
    def test_explicit_course_section_override(self):
        """Test that explicitly provided course_section overrides auto-assignment"""
        test_data = {
            'course_section': self.section2.id,  # Explicitly assign to section 2
            'title': 'Math Test 5',
            'description': 'Test with explicit section',
            'scheduled_at': datetime(2024, 2, 15, 10, 0),  # Would auto-assign to section 1
            'is_published': False,
            'teacher': self.teacher.id
        }
        
        serializer = CreateTestSerializer(data=test_data, context={'request': type('obj', (object,), {'user': self.teacher})()})
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        test = serializer.save()
        
        # Verify that the explicitly provided section was used
        self.assertEqual(test.course_section, self.section2)
    
    def test_no_course_section_no_scheduled_at(self):
        """Test error when neither course_section nor scheduled_at is provided"""
        test_data = {
            'title': 'Math Test 6',
            'description': 'Test without section or date',
            'is_published': False,
            'teacher': self.teacher.id
        }
        
        serializer = CreateTestSerializer(data=test_data, context={'request': type('obj', (object,), {'user': self.teacher})()})
        self.assertFalse(serializer.is_valid())
        self.assertIn('Either course_section must be provided or scheduled_at must be provided', str(serializer.errors))
    
    def test_subject_group_information_in_response(self):
        """Test that subject group information is included in test response"""
        # Create a test with auto-assigned course section
        test_data = {
            'title': 'Math Test with Subject Group Info',
            'description': 'Test to verify subject group info is shown',
            'scheduled_at': datetime(2024, 2, 15, 10, 0),  # Within first quarter
            'is_published': False,
        }
        
        create_serializer = CreateTestSerializer(data=test_data, context={'request': type('obj', (object,), {'user': self.teacher})()})
        self.assertTrue(create_serializer.is_valid(), f"Create serializer errors: {create_serializer.errors}")
        
        test = create_serializer.save()
        
        # Serialize the test to check response fields
        response_serializer = TestSerializer(test)
        response_data = response_serializer.data
        
        # Verify subject group information is included
        self.assertIn('subject_group_id', response_data)
        self.assertIn('classroom_name', response_data)
        self.assertIn('classroom_grade', response_data)
        self.assertIn('classroom_letter', response_data)
        self.assertIn('course_name', response_data)
        self.assertIn('course_code', response_data)
        self.assertIn('course_section_title', response_data)
        
        # Verify the values are correct
        self.assertEqual(response_data['subject_group_id'], self.subject_group.id)
        self.assertEqual(response_data['classroom_grade'], 10)
        self.assertEqual(response_data['classroom_letter'], 'A')
        self.assertEqual(response_data['course_name'], 'Mathematics')
        self.assertEqual(response_data['course_code'], 'MATH101')
        self.assertEqual(response_data['course_section_title'], 'First Quarter')
    
    def test_auto_assign_course_section_with_subject_group(self):
        """Test auto-assignment when subject_group is provided in input"""
        test_data = {
            'subject_group': self.subject_group.id,
            'title': 'Math Test with Subject Group',
            'description': 'Test with subject group specified',
            'scheduled_at': datetime(2024, 2, 15, 10, 0),  # Within first quarter
            'is_published': False,
        }
        
        serializer = CreateTestSerializer(data=test_data, context={'request': type('obj', (object,), {'user': self.teacher})()})
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        test = serializer.save()
        
        # Verify that the test was assigned to the correct course section
        self.assertEqual(test.course_section, self.section1)
        self.assertEqual(test.title, 'Math Test with Subject Group')
    
    def test_auto_assign_course_section_with_wrong_subject_group(self):
        """Test error when subject_group doesn't have a section for the given date"""
        # Create another subject group without sections for the test date
        another_course = Course.objects.create(
            course_code="PHYS101",
            name="Physics",
            description="Basic Physics",
            grade=10
        )
        
        another_subject_group = SubjectGroup.objects.create(
            course=another_course,
            classroom=self.classroom
        )
        
        test_data = {
            'subject_group': another_subject_group.id,
            'title': 'Physics Test',
            'description': 'Test for physics subject group',
            'scheduled_at': datetime(2024, 2, 15, 10, 0),  # No sections for this subject group
            'is_published': False,
        }
        
        serializer = CreateTestSerializer(data=test_data, context={'request': type('obj', (object,), {'user': self.teacher})()})
        self.assertFalse(serializer.is_valid())
        self.assertIn('No course section found for the scheduled date', str(serializer.errors))
