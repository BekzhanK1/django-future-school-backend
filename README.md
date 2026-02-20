# 🎓 Future School Backend API

A comprehensive Django REST API for managing schools, courses, assignments, assessments, and student progress. Built with Django, DRF, JWT authentication, and role-based access control.

## 🚀 Quick Start

### Base URL
```
http://localhost:8000/api/
```

### Authentication
All endpoints (except auth) require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## 🔐 Authentication Endpoints

### Login
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "student1",
  "password": "password123"
}
```

### Refresh Token
```http
POST /api/auth/refresh/
Content-Type: application/json

{
  "refresh": "your_refresh_token"
}
```

### Change Password
```http
POST /api/auth/change-password/
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "old_password",
  "new_password": "new_password"
}
```

### Password Reset
```http
# Request reset
POST /api/auth/request-password-reset/
Content-Type: application/json

{
  "email": "user@example.com"
}

# Confirm reset
POST /api/auth/confirm-password-reset/
Content-Type: application/json

{
  "token": "reset_token",
  "new_password": "new_password"
}
```

## 👥 User Roles & Permissions

| Role | Description | Access Level |
|------|-------------|--------------|
| `superadmin` | System administrator | Full access to everything |
| `schooladmin` | School administrator | Access to their school only |
| `teacher` | Teacher | Access to their assigned courses |
| `student` | Student | Access to their enrolled courses only |

## 🏫 Schools & Classrooms

### Schools
```http
GET    /api/schools/                    # List all schools
POST   /api/schools/                    # Create school
GET    /api/schools/{id}/               # Get school details
PUT    /api/schools/{id}/               # Update school
DELETE /api/schools/{id}/               # Delete school
```

### Classrooms
```http
GET    /api/classrooms/                 # List all classrooms
POST   /api/classrooms/                 # Create classroom
GET    /api/classrooms/{id}/            # Get classroom details
PUT    /api/classrooms/{id}/            # Update classroom
DELETE /api/classrooms/{id}/            # Delete classroom
```

### Classroom Users (Students)
```http
GET    /api/classroom-users/            # List classroom users
POST   /api/classroom-users/            # Add student to classroom
DELETE /api/classroom-users/{id}/       # Remove student from classroom

# Bulk operations
POST   /api/classroom-users/bulk-add/   # Add multiple students
POST   /api/classroom-users/bulk-remove/ # Remove multiple students
```

## 📚 Courses & Learning

### Courses
```http
GET    /api/courses/                    # List all courses
POST   /api/courses/                    # Create course
GET    /api/courses/{id}/               # Get course details
PUT    /api/courses/{id}/               # Update course
DELETE /api/courses/{id}/               # Delete course
```

### Subject Groups (Course + Classroom + Teacher)
```http
GET    /api/subject-groups/             # List subject groups
POST   /api/subject-groups/             # Create subject group
GET    /api/subject-groups/{id}/        # Get subject group details
PUT    /api/subject-groups/{id}/        # Update subject group
DELETE /api/subject-groups/{id}/        # Delete subject group
```

### Course Sections (Weekly Sections)
```http
GET    /api/course-sections/            # List course sections
POST   /api/course-sections/            # Create course section
GET    /api/course-sections/{id}/       # Get section with resources & assignments
PUT    /api/course-sections/{id}/       # Update course section
DELETE /api/course-sections/{id}/       # Delete course section

# Auto-create weekly sections
POST   /api/course-sections/auto-create-weeks/
{
  "subject_group_id": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "section_title_template": "Week of {start_date} - {end_date}"
}
```

## 📁 Resources (Course Content)

### Resources
```http
GET    /api/resources/                  # List root resources only
POST   /api/resources/                  # Create resource
GET    /api/resources/{id}/             # Get resource details
PUT    /api/resources/{id}/             # Update resource
DELETE /api/resources/{id}/             # Delete resource

# Special endpoints
GET    /api/resources/all/?course_section_id=1  # Get all resources (flat)
GET    /api/resources/tree/?course_section_id=1 # Get hierarchical tree
POST   /api/resources/{id}/move/        # Move resource to different position/parent
```

### Resource Types
- `file` - File attachments
- `link` - External links
- `directory` - Folder for organizing resources
- `text` - Text content

## 📝 Assignments

### Assignments
```http
GET    /api/assignments/                # List assignments
POST   /api/assignments/                # Create assignment
GET    /api/assignments/{id}/           # Get assignment with attachments
PUT    /api/assignments/{id}/           # Update assignment
DELETE /api/assignments/{id}/           # Delete assignment
```

### Assignment Attachments
```http
GET    /api/assignment-attachments/     # List assignment attachments
POST   /api/assignment-attachments/     # Create attachment
GET    /api/assignment-attachments/{id}/ # Get attachment details
PUT    /api/assignment-attachments/{id}/ # Update attachment
DELETE /api/assignment-attachments/{id}/ # Delete attachment

# Bulk create attachments
POST   /api/assignment-attachments/bulk-create/
{
  "assignment_id": 1,
  "attachments": [
    {
      "type": "text",
      "title": "Instructions",
      "content": "Please solve step by step",
      "position": 1
    },
    {
      "type": "file",
      "title": "Problem Set",
      "file_url": "https://example.com/problems.pdf",
      "position": 2
    }
  ]
}
```

## 📤 Submissions

### Submissions
```http
GET    /api/submissions/                # List submissions
POST   /api/submissions/                # Create submission
GET    /api/submissions/{id}/           # Get submission with attachments & grade
PUT    /api/submissions/{id}/           # Update submission
DELETE /api/submissions/{id}/           # Delete submission
```

### Submission Attachments
```http
GET    /api/submission-attachments/     # List submission attachments
POST   /api/submission-attachments/     # Create attachment
GET    /api/submission-attachments/{id}/ # Get attachment details
PUT    /api/submission-attachments/{id}/ # Update attachment
DELETE /api/submission-attachments/{id}/ # Delete attachment

# Bulk create attachments
POST   /api/submission-attachments/bulk-create/
{
  "submission_id": 1,
  "attachments": [
    {
      "type": "text",
      "title": "My Solution",
      "content": "Here's how I solved it...",
      "position": 1
    },
    {
      "type": "file",
      "title": "Worked Solutions",
      "file_url": "https://example.com/solution.pdf",
      "position": 2
    }
  ]
}
```

## 🎯 Grading

### Grades
```http
GET    /api/grades/                     # List grades
POST   /api/grades/                     # Create grade
GET    /api/grades/{id}/                # Get grade details
PUT    /api/grades/{id}/                # Update grade
DELETE /api/grades/{id}/                # Delete grade

# Bulk grade submissions
POST   /api/grades/bulk-grade/
[
  {
    "submission_id": 1,
    "grade_value": 85,
    "feedback": "Good work!"
  },
  {
    "submission_id": 2,
    "grade_value": 92,
    "feedback": "Excellent!"
  }
]
```

## 🧪 Assessments (Tests) - Complete Frontend Guide

### Overview
The test system supports 4 question types with automatic scoring, time limits, multiple attempts, and controlled result visibility.

### Question Types
- **Multiple Choice** - Single correct answer
- **Choose All That Apply** - Multiple correct answers with partial credit
- **Open Questions** - Text answers requiring manual grading
- **Matching Items** - Match items from two lists

### Tests API
```http
GET    /api/assessments/tests/          # List tests (filtered by user role)
POST   /api/assessments/tests/          # Create test with questions
GET    /api/assessments/tests/{id}/     # Get test with questions & options
PUT    /api/assessments/tests/{id}/     # Update test
DELETE /api/assessments/tests/{id}/     # Delete test

# Test management
POST   /api/assessments/tests/{id}/publish/    # Publish test
POST   /api/assessments/tests/{id}/unpublish/  # Unpublish test
```

### Questions API
```http
GET    /api/assessments/questions/      # List questions
POST   /api/assessments/questions/      # Create question with options
GET    /api/assessments/questions/{id}/ # Get question with options
PUT    /api/assessments/questions/{id}/ # Update question
DELETE /api/assessments/questions/{id}/ # Delete question
```

### Options API
```http
GET    /api/assessments/options/        # List options
POST   /api/assessments/options/        # Create option
GET    /api/assessments/options/{id}/   # Get option details
PUT    /api/assessments/options/{id}/   # Update option
DELETE /api/assessments/options/{id}/   # Delete option
```

### Test Attempts API
```http
GET    /api/assessments/attempts/       # List attempts (filtered by user role)
POST   /api/assessments/attempts/start/ # Start new test attempt
GET    /api/assessments/attempts/{id}/  # Get attempt with answers
POST   /api/assessments/attempts/{id}/submit/        # Submit completed attempt
POST   /api/assessments/attempts/{id}/submit-answer/ # Submit answer for question
POST   /api/assessments/attempts/{id}/view-results/  # Mark results as viewed
```

### Test Answers API
```http
GET    /api/assessments/answers/        # List answers (filtered by user role)
GET    /api/assessments/answers/{id}/   # Get answer details
PUT    /api/assessments/answers/{id}/   # Update answer

# Bulk grade answers (for open questions)
POST   /api/assessments/answers/bulk-grade/
[
  {
    "answer_id": 1,
    "score": 8.5,
    "teacher_feedback": "Good work!"
  }
]
```

## 🎯 Test System API Examples

### 1. Teacher: Creating and Managing Tests

#### Create Test with Questions
```http
POST /api/assessments/tests/
Content-Type: application/json
Authorization: Bearer <token>

{
  "course_section": 1,
  "title": "Math Quiz",
  "description": "Basic math concepts",
  "time_limit_minutes": 30,
  "allow_multiple_attempts": true,
  "max_attempts": 3,
  "show_correct_answers": true,
  "show_feedback": true,
  "show_score_immediately": false,
  "reveal_results_at": "2024-01-15T10:00:00Z",
  "questions": [
    {
      "type": "multiple_choice",
      "text": "What is 2 + 2?",
      "points": 5,
      "position": 1,
      "options": [
        { "text": "3", "is_correct": false, "position": 1 },
        { "text": "4", "is_correct": true, "position": 2 },
        { "text": "5", "is_correct": false, "position": 3 }
      ]
    },
    {
      "type": "choose_all",
      "text": "Which are prime numbers?",
      "points": 10,
      "position": 2,
      "options": [
        { "text": "2", "is_correct": true, "position": 1 },
        { "text": "3", "is_correct": true, "position": 2 },
        { "text": "4", "is_correct": false, "position": 3 },
        { "text": "5", "is_correct": true, "position": 4 }
      ]
    },
    {
      "type": "open_question",
      "text": "Explain photosynthesis",
      "points": 15,
      "position": 3,
      "correct_answer_text": "Process by which plants convert sunlight to energy",
      "sample_answer": "Plants use sunlight, water, and CO2 to create glucose"
    },
    {
      "type": "matching",
      "text": "Match countries with capitals",
      "points": 20,
      "position": 4,
      "matching_pairs_json": [
        { "left": "France", "right": "Paris" },
        { "left": "Germany", "right": "Berlin" },
        { "left": "Spain", "right": "Madrid" }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "id": 1,
  "course_section": 1,
  "title": "Math Quiz",
  "description": "Basic math concepts",
  "is_published": false,
  "time_limit_minutes": 30,
  "allow_multiple_attempts": true,
  "max_attempts": 3,
  "show_correct_answers": true,
  "show_feedback": true,
  "show_score_immediately": false,
  "reveal_results_at": "2024-01-15T10:00:00Z",
  "total_points": 50,
  "questions": [
    {
      "id": 1,
      "type": "multiple_choice",
      "text": "What is 2 + 2?",
      "points": 5,
      "position": 1,
      "options": [
        { "id": 1, "text": "3", "is_correct": false, "position": 1 },
        { "id": 2, "text": "4", "is_correct": true, "position": 2 },
        { "id": 3, "text": "5", "is_correct": false, "position": 3 }
      ]
    }
  ]
}
```

#### Add Question to Existing Test
```http
POST /api/assessments/questions/
Content-Type: application/json
Authorization: Bearer <token>

{
  "test": 1,
  "type": "multiple_choice",
  "text": "What is the capital of France?",
  "points": 10,
  "position": 5,
  "options": [
    { "text": "London", "is_correct": false, "position": 1 },
    { "text": "Paris", "is_correct": true, "position": 2 },
    { "text": "Berlin", "is_correct": false, "position": 3 }
  ]
}
```

#### Update Question
```http
PATCH /api/assessments/questions/5/
Content-Type: application/json
Authorization: Bearer <token>

{
  "text": "What is the capital of France? (Updated)",
  "points": 15
}
```

#### Delete Question
```http
DELETE /api/assessments/questions/5/
Authorization: Bearer <token>
```

#### Add Option to Question
```http
POST /api/assessments/options/
Content-Type: application/json
Authorization: Bearer <token>

{
  "question": 5,
  "text": "Rome",
  "is_correct": false,
  "position": 4
}
```

#### Publish Test
```http
POST /api/assessments/tests/1/publish/
Authorization: Bearer <token>
```

### 2. Student: Taking Tests

#### Start Test Attempt
```http
POST /api/assessments/attempts/start/
Content-Type: application/json
Authorization: Bearer <token>

{
  "test_id": 1
}
```

**Response:**
```json
{
  "id": 1,
  "test": 1,
  "student": 2,
  "attempt_number": 1,
  "started_at": "2024-01-10T10:00:00Z",
  "submitted_at": null,
  "score": null,
  "max_score": null,
  "is_completed": false,
  "is_graded": false,
  "can_view_results": false,
  "answers": []
}
```

#### Submit Answer for Multiple Choice Question
```http
POST /api/assessments/attempts/1/submit-answer/
Content-Type: application/json
Authorization: Bearer <token>

{
  "question_id": 1,
  "selected_option_ids": [2]
}
```

#### Submit Answer for Choose All Question
```http
POST /api/assessments/attempts/1/submit-answer/
Content-Type: application/json
Authorization: Bearer <token>

{
  "question_id": 2,
  "selected_option_ids": [4, 5, 7]
}
```

#### Submit Answer for Open Question
```http
POST /api/assessments/attempts/1/submit-answer/
Content-Type: application/json
Authorization: Bearer <token>

{
  "question_id": 3,
  "text_answer": "Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen."
}
```

#### Submit Answer for Matching Question
```http
POST /api/assessments/attempts/1/submit-answer/
Content-Type: application/json
Authorization: Bearer <token>

{
  "question_id": 4,
  "matching_answers_json": [
    { "left": "France", "right": "Paris" },
    { "left": "Germany", "right": "Berlin" },
    { "left": "Spain", "right": "Madrid" }
  ]
}
```

#### Submit Completed Test
```http
POST /api/assessments/attempts/1/submit/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "test": 1,
  "student": 2,
  "attempt_number": 1,
  "started_at": "2024-01-10T10:00:00Z",
  "submitted_at": "2024-01-10T10:25:00Z",
  "score": 45,
  "max_score": 50,
  "percentage": 90.0,
  "is_completed": true,
  "is_graded": true,
  "time_spent_minutes": 25.0,
  "answers": [
    {
      "id": 1,
      "question": 1,
      "selected_options": [
        { "id": 2, "text": "4", "is_correct": true }
      ],
      "score": 5,
      "max_score": 5,
      "is_correct": true
    }
  ]
}
```

### 3. Viewing Results

#### Get Test Results
```http
GET /api/assessments/attempts/1/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "test": 1,
  "student": 2,
  "attempt_number": 1,
  "started_at": "2024-01-10T10:00:00Z",
  "submitted_at": "2024-01-10T10:25:00Z",
  "score": 45,
  "max_score": 50,
  "percentage": 90.0,
  "is_completed": true,
  "is_graded": true,
  "time_spent_minutes": 25.0,
  "can_view_results": true,
  "answers": [
    {
      "id": 1,
      "question": 1,
      "question_text": "What is 2 + 2?",
      "question_type": "multiple_choice",
      "question_points": 5,
      "selected_options": [
        { "id": 2, "text": "4", "is_correct": true }
      ],
      "score": 5,
      "max_score": 5,
      "is_correct": true,
      "teacher_feedback": "Correct!"
    },
    {
      "id": 2,
      "question": 2,
      "question_text": "Which are prime numbers?",
      "question_type": "choose_all",
      "question_points": 10,
      "selected_options": [
        { "id": 4, "text": "2", "is_correct": true },
        { "id": 5, "text": "3", "is_correct": true },
        { "id": 7, "text": "5", "is_correct": true }
      ],
      "score": 10,
      "max_score": 10,
      "is_correct": true
    },
    {
      "id": 3,
      "question": 3,
      "question_text": "Explain photosynthesis",
      "question_type": "open_question",
      "question_points": 15,
      "text_answer": "Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen.",
      "score": 12,
      "max_score": 15,
      "is_correct": false,
      "teacher_feedback": "Good explanation, but you could mention chlorophyll."
    },
    {
      "id": 4,
      "question": 4,
      "question_text": "Match countries with capitals",
      "question_type": "matching",
      "question_points": 20,
      "matching_answers_json": [
        { "left": "France", "right": "Paris" },
        { "left": "Germany", "right": "Berlin" },
        { "left": "Spain", "right": "Madrid" }
      ],
      "score": 20,
      "max_score": 20,
      "is_correct": true
    }
  ]
}
```

### 4. Teacher: Grading Open Questions

#### Bulk Grade Answers
```http
POST /api/assessments/answers/bulk-grade/
Content-Type: application/json
Authorization: Bearer <token>

[
  {
    "answer_id": 3,
    "score": 12,
    "teacher_feedback": "Good explanation, but you could mention chlorophyll."
  },
  {
    "answer_id": 5,
    "score": 8,
    "teacher_feedback": "Partially correct, but missing key details."
  }
]
```

### 5. List Operations

#### Get All Tests (Filtered by User Role)
```http
GET /api/assessments/tests/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "course_section": 1,
      "title": "Math Quiz",
      "description": "Basic math concepts",
      "is_published": true,
      "total_points": 50,
      "time_limit_minutes": 30,
      "can_attempt": true,
      "is_available": true,
      "can_see_results": true,
      "questions": [...]
    }
  ]
}
```

#### Get Questions for a Test
```http
GET /api/assessments/questions/?test=1
Authorization: Bearer <token>
```

#### Get Student's Attempts
```http
GET /api/assessments/attempts/?student=2
Authorization: Bearer <token>
```

#### Get Answers for Grading
```http
GET /api/assessments/answers/?attempt__test=1&question__type=open_question
Authorization: Bearer <token>
```

### 6. Test Management

#### Update Test Settings
```http
PATCH /api/assessments/tests/1/
Content-Type: application/json
Authorization: Bearer <token>

{
  "time_limit_minutes": 45,
  "max_attempts": 2,
  "show_score_immediately": true
}
```

#### Unpublish Test
```http
POST /api/assessments/tests/1/unpublish/
Authorization: Bearer <token>
```

#### Mark Results as Viewed
```http
POST /api/assessments/attempts/1/view-results/
Authorization: Bearer <token>
```

### 7. Filtering and Search

#### Filter Tests by Course Section
```http
GET /api/assessments/tests/?course_section=1
Authorization: Bearer <token>
```

#### Filter Questions by Type
```http
GET /api/assessments/questions/?type=multiple_choice
Authorization: Bearer <token>
```

#### Search Tests by Title
```http
GET /api/assessments/tests/?search=math
Authorization: Bearer <token>
```

#### Filter Attempts by Status
```http
GET /api/assessments/attempts/?is_completed=true
Authorization: Bearer <token>
```

## 📅 Calendar

### Calendar Events
```http
GET /api/calendar/events/?start_date=2024-01-01&end_date=2024-01-31
# Returns assignments and tests as calendar events
```

### Upcoming Events
```http
GET /api/calendar/upcoming/
# Returns events for the next 7 days
```

## 🔍 Filtering & Search

Most endpoints support filtering and search:

### Common Query Parameters
- `search` - Search across relevant fields
- `ordering` - Sort by field (e.g., `?ordering=-created_at`)
- `page` - Pagination (e.g., `?page=2`)
- `page_size` - Items per page (e.g., `?page_size=20`)

### Examples
```http
# Search assignments by title
GET /api/assignments/?search=math

# Filter submissions by assignment
GET /api/submissions/?assignment=1

# Order resources by position
GET /api/resources/?ordering=position

# Filter tests by course
GET /api/tests/?course=1
```

## 📊 Response Examples

### Course Section with Resources & Assignments
```json
{
  "id": 1,
  "subject_group": 1,
  "title": "Week of 01 Jan - 07 Jan",
  "position": 1,
  "resources": [
    {
      "id": 1,
      "type": "file",
      "title": "Lecture Notes",
      "description": "Chapter 1 notes",
      "url": "https://example.com/notes.pdf",
      "position": 1,
      "level": 0,
      "children": []
    }
  ],
  "assignments": [
    {
      "id": 1,
      "title": "Math Assignment 1",
      "description": "Complete exercises 1-10",
      "due_at": "2024-01-15T23:59:00Z",
      "max_grade": 100,
      "attachments": [
        {
          "id": 1,
          "type": "text",
          "title": "Instructions",
          "content": "Solve step by step",
          "position": 1
        }
      ]
    }
  ]
}
```

### Submission with Attachments & Grade
```json
{
  "id": 1,
  "assignment": 1,
  "student": 2,
  "submitted_at": "2024-01-14T10:30:00Z",
  "assignment_title": "Math Assignment 1",
  "assignment_max_grade": 100,
  "grade_value": 85,
  "grade_feedback": "Good work!",
  "attachments": [
    {
      "id": 1,
      "type": "text",
      "title": "My Solution",
      "content": "Here's how I solved it...",
      "position": 1
    }
  ]
}
```

## 🗓️ Attendance

### Shared: Subject Group Members (Teacher + Students)

Use this before taking attendance to fetch the teacher and students for a subject group.

```http
GET /api/courses/subject-groups/{subject_group_id}/members/
Authorization: Bearer <token>
```

Access rules:
- Teacher: only their own subject groups
- School admin: subject groups in their school (read-only)
- Superadmin: all subject groups
- Student: only if they belong to the subject group’s classroom

Example response:
```json
{
  "subject_group": {
    "id": 12,
    "course_id": 7,
    "course_code": "MATH101",
    "course_name": "Mathematics",
    "classroom": "10A - School Name"
  },
  "teacher": {
    "id": 55,
    "username": "teacher_smith",
    "first_name": "Sarah",
    "last_name": "Smith",
    "email": "sarah.smith@school.com"
  },
  "students": [
    {
      "id": 101,
      "username": "john_doe",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@school.com"
    }
  ]
}
```

### Status values
- `present`
- `excused`
- `not_present`

Attendance percentage = (present + excused) / total_students * 100

### Teacher Workflow

1) Get members for the subject group
```http
GET /api/courses/subject-groups/12/members/
Authorization: Bearer <teacher_token>
```

2) Take attendance (create session)
```http
POST /api/learning/attendance/
Content-Type: application/json
Authorization: Bearer <teacher_token>

{
  "subject_group": 12,
  "notes": "Regular class - chapter 5",
  "records": [
    { "student": 101, "status": "present", "notes": "" },
    { "student": 102, "status": "excused", "notes": "Medical appointment" },
    { "student": 103, "status": "not_present", "notes": "" }
  ]
}
```

Response:
```json
{
  "id": 44,
  "subject_group": 12,
  "taken_by": 55,
  "taken_at": "2025-09-23T08:43:00Z",
  "notes": "Regular class - chapter 5",
  "subject_group_course_name": "Mathematics",
  "subject_group_course_code": "MATH101",
  "classroom_name": "10A - School Name",
  "taken_by_username": "teacher_smith",
  "taken_by_first_name": "Sarah",
  "taken_by_last_name": "Smith",
  "total_students": 28,
  "present_count": 26,
  "excused_count": 1,
  "not_present_count": 1,
  "attendance_percentage": 96.43,
  "records": [
    {
      "id": 201,
      "student": 101,
      "status": "present",
      "notes": "",
      "student_username": "john_doe",
      "student_first_name": "John",
      "student_last_name": "Doe",
      "student_email": "john.doe@school.com"
    }
  ]
}
```

3) View attendance sessions for a subject group
```http
GET /api/learning/attendance/?subject_group=12
Authorization: Bearer <teacher_token>
```

4) Update an attendance session
```http
PUT /api/learning/attendance/44/
Content-Type: application/json
Authorization: Bearer <teacher_token>

{
  "notes": "Updated: chapter 5 review",
  "records": [
    { "student": 101, "status": "present", "notes": "On time" },
    { "student": 102, "status": "present", "notes": "Late but present" },
    { "student": 103, "status": "not_present", "notes": "Absent" }
  ]
}
```

5) Metrics
- All your subject groups:
```http
GET /api/learning/attendance/metrics/
Authorization: Bearer <teacher_token>
```
- One subject group:
```http
GET /api/learning/attendance/metrics/?subject_group_id=12
Authorization: Bearer <teacher_token>
```

Example response:
```json
[
  {
    "subject_group_name": "MATH101 / 10A - School Name",
    "classroom_name": "10A - School Name",
    "course_name": "Mathematics",
    "total_sessions": 8,
    "present_count": 206,
    "excused_count": 6,
    "not_present_count": 12,
    "attendance_percentage": 94.62
  }
]
```

### School Admin (Read-only)

- Members in your school:
```http
GET /api/courses/subject-groups/12/members/
Authorization: Bearer <school_admin_token>
```
- View attendance (filterable by `subject_group`, `taken_by`, `taken_at`):
```http
GET /api/learning/attendance/?subject_group=12
Authorization: Bearer <school_admin_token>
```
- Metrics across your school:
```http
GET /api/learning/attendance/metrics/
Authorization: Bearer <school_admin_token>
```

### Superadmin

- Same as school admin but for all schools:
```http
GET /api/courses/subject-groups/12/members/
Authorization: Bearer <superadmin_token>
```
```http
GET /api/learning/attendance/metrics/?subject_group_id=12
Authorization: Bearer <superadmin_token>
```

### Student

- View members (only if in the classroom):
```http
GET /api/courses/subject-groups/12/members/
Authorization: Bearer <student_token>
```
- View own attendance history:
```http
GET /api/learning/attendance/student-history/?student_id=101
Authorization: Bearer <student_token>
```
Response:
```json
[
  {
    "id": 201,
    "status": "present",
    "notes": "",
    "subject_group_course_name": "Mathematics",
    "subject_group_course_code": "MATH101",
    "classroom_name": "10A - School Name",
    "taken_at": "2025-09-23T08:43:00Z",
    "taken_by_username": "teacher_smith"
  }
]
```

## 🛡️ Security Features

- **JWT Authentication** - Secure token-based auth
- **Role-based Access Control** - Users only see what they're allowed to
- **Data Isolation** - Students can't see each other's submissions
- **School Isolation** - School admins only see their school's data
- **Teacher Isolation** - Teachers only see their assigned courses

## 📖 API Documentation

Visit the interactive Swagger UI at:
```
http://localhost:8000/api/docs/
```

## 🚨 Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

Error responses include details:
```json
{
  "detail": "Authentication credentials were not provided.",
  "code": "authentication_failed"
}
```

## 🎯 Frontend Integration Tips

1. **Store JWT tokens** in localStorage or secure cookies
2. **Implement token refresh** before expiration
3. **Handle 401 errors** by redirecting to login
4. **Use pagination** for large lists
5. **Implement real-time updates** for grades and submissions
6. **Cache course sections** for better performance
7. **Use calendar events** for assignment/test deadlines

## 🤝 Support

If you need help with the API, check the Swagger documentation or contact the backend team!

---

**Happy coding! 🚀**
## ⚙️ Environment (Email & Celery)

Add these to your `.env` (copy from `.env.example`):

```env
# PostgreSQL (optional; if unset, SQLite is used)
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Django
DJANGO_SECRET_KEY=your-secret-key
FRONTEND_URL=http://localhost:3000

# Email
GMAIL_EMAIL=your_gmail_address@gmail.com
GMAIL_PASSWORD=your_gmail_app_password
DEFAULT_FROM_EMAIL=Future School <your_gmail_address@gmail.com>

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=false
```

### Celery commands

```bash
# Worker
celery -A future_school.celery.celery_app worker -l info

# Beat (optional if you add periodic tasks)
celery -A future_school.celery.celery_app beat -l info
```

### Docker Compose (Redis + Celery)

```bash
# Build images
docker compose build

# Start Django + Redis + Celery worker + Beat
docker compose up -d

# View logs
docker compose logs -f celery-worker
docker compose logs -f celery-beat
docker compose logs -f django
```


---

## 🇷🇺 Руководство: Тесты (Assessments) — подробная инструкция с примерами

Базовый URL для всех примеров ниже: `http://localhost:8000/api/`

Аутентификация (JWT):
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

### Типы вопросов
- multiple_choice — Один правильный вариант (строгая проверка: засчитывается только один выбранный правильный вариант и ровно один выбор)
- choose_all — Несколько правильных вариантов (частичный балл: любая неверная приводит к 0, без неверных — доля правильных × балл)
- open_question — Открытый ответ (нужна ручная проверка учителем)
- matching — Сопоставление пар (частичный балл по доле совпавших пар)

---

## Учитель: создание теста, добавление/изменение вопросов и управление

### Создать тест (с вопросами или черновик без вопросов)
```http
POST /api/assessments/tests/
Authorization: Bearer <teacher_token>
Content-Type: application/json

{
  "course_section": 42,
  "title": "Алгебра: Квиз 1",
  "description": "Линейные уравнения",
  "is_published": false,
  "scheduled_at": "2025-09-30T09:00:00Z",
  "reveal_results_at": "2025-09-30T17:00:00Z",
  "time_limit_minutes": 30,
  "allow_multiple_attempts": true,
  "max_attempts": 2,
  "show_correct_answers": true,
  "show_feedback": true,
  "show_score_immediately": false,
  "questions": [
    {
      "type": "multiple_choice",
      "text": "2 + 2 = ?",
      "points": 2,
      "position": 1,
      "options": [
        {"text": "3", "is_correct": false, "position": 1},
        {"text": "4", "is_correct": true, "position": 2}
      ]
    },
    {
      "type": "choose_all",
      "text": "Выберите четные числа",
      "points": 3,
      "position": 2,
      "options": [
        {"text": "1", "is_correct": false, "position": 1},
        {"text": "2", "is_correct": true, "position": 2},
        {"text": "4", "is_correct": true, "position": 3}
      ]
    },
    {
      "type": "open_question",
      "text": "Объясните форму y = mx + b.",
      "points": 5,
      "position": 3
    },
    {
      "type": "matching",
      "text": "Соотнесите термины",
      "points": 4,
      "position": 4,
      "matching_pairs_json": [
        {"left": "Наклон", "right": "Скорость изменения"},
        {"left": "Пересечение", "right": "Значение при x=0"}
      ]
    }
  ]
}
```

Примечания:
- Поле `teacher` на стороне бэкенда связывается с текущим пользователем-учителем (модель требует это поле).
- Доступность теста для учеников определяется полями `is_published` и `scheduled_at`.

### Опубликовать / снять с публикации тест
```http
POST /api/assessments/tests/{test_id}/publish/
Authorization: Bearer <teacher_token>
```
```http
POST /api/assessments/tests/{test_id}/unpublish/
Authorization: Bearer <teacher_token>
```

### Добавить вопрос (если тест создан без вложенных вопросов)
```http
POST /api/assessments/questions/
Authorization: Bearer <teacher_token>
Content-Type: application/json

{
  "test": 101,
  "type": "multiple_choice",
  "text": "5 - 3 = ?",
  "points": 1,
  "position": 5,
  "options": [
    {"text": "1", "is_correct": false, "position": 1},
    {"text": "2", "is_correct": true, "position": 2}
  ]
}
```

### Типы вопросов — как задать данные
- multiple_choice: один правильный в `options[]` (`is_correct: true` ровно у одного)
- choose_all: несколько правильных в `options[]` (`is_correct: true` у нескольких)
- open_question: открытый текст, можно указать `correct_answer_text`/`sample_answer` (подсказки)
- matching: пары в `matching_pairs_json` (массив объектов с полями `left` и `right`)

### Обновление теста/вопроса/варианта
```http
PATCH /api/assessments/tests/{id}/
Authorization: Bearer <teacher_token>
Content-Type: application/json

{ "title": "Алгебра: Квиз 1 (обновлено)", "scheduled_at": "2025-09-30T10:00:00Z" }
```
```http
PATCH /api/assessments/questions/{id}/
Authorization: Bearer <teacher_token>
Content-Type: application/json

{ "text": "5 − 2 = ?", "points": 2 }
```
```http
PATCH /api/assessments/options/{id}/
Authorization: Bearer <teacher_token>
Content-Type: application/json

{ "is_correct": true, "position": 1 }
```

Удаление — `DELETE` соответствующего ресурса: `tests/{id}/`, `questions/{id}/`, `options/{id}/`.

### Массовая проверка открытых ответов (ручное выставление баллов)
```http
POST /api/assessments/answers/bulk-grade/
Authorization: Bearer <teacher_token>
Content-Type: application/json

[
  { "answer_id": 555, "score": 4.0, "teacher_feedback": "Хорошее объяснение." },
  { "answer_id": 556, "score": 3.0, "teacher_feedback": "Добавьте пример." }
]
```

---

## Ученик: прохождение теста и отправка ответов

### Список доступных тестов
```http
GET /api/assessments/tests/?ordering=-scheduled_at
Authorization: Bearer <student_token>
```
Ученик видит только тесты своих секций. Тест считается доступным, если `is_published: true` и `scheduled_at` не в будущем.

### Начать попытку
```http
POST /api/assessments/attempts/start/
Authorization: Bearer <student_token>
Content-Type: application/json

{ "test_id": 101 }
```
Правила: тест опубликован; если задан `scheduled_at` — время наступило; не превышен `max_attempts`. Если есть незавершенная попытка — вернется она же.

### Отправлять ответы по одному вопросу
```http
POST /api/assessments/attempts/{attempt_id}/submit-answer/
Authorization: Bearer <student_token>
Content-Type: application/json
```

- multiple_choice (выбор одного):
```json
{ "question_id": 1001, "selected_option_ids": [2002] }
```

- choose_all (выбрать все подходящие):
```json
{ "question_id": 1002, "selected_option_ids": [2005, 2006] }
```

- open_question (свободный текст):
```json
{ "question_id": 1003, "text_answer": "y = mx + b; m — наклон, b — пересечение." }
```

- matching (сопоставление пар):
```json
{
  "question_id": 1004,
  "matching_answers_json": [
    { "left": "Наклон", "right": "Скорость изменения" },
    { "left": "Пересечение", "right": "Значение при x=0" }
  ]
}
```

### Завершить попытку (автопроверка)
```http
POST /api/assessments/attempts/{attempt_id}/submit/
Authorization: Bearer <student_token>
```
Итоги: выставляются `score`, `max_score`, `percentage`, `is_completed: true`. Поле `is_graded: true`, если нет неоцененных открытых вопросов (их оценивает учитель вручную).

### Просмотр результатов (отметить как просмотренные)
```http
POST /api/assessments/attempts/{attempt_id}/view-results/
Authorization: Bearer <student_token>
```
Доступно после завершения попытки и, если задано, не раньше `reveal_results_at`.

---

## Бизнес-правила и нюансы

- Доступность тестов: `is_published == true` и (`scheduled_at` не задано или уже наступило).
- Попытки: ограничиваются `max_attempts` (если задано). При наличии незавершенной попытки повторный старт вернет её.
- Автопроверка:
  - multiple_choice — полный балл только при единственном правильном выбранном варианте и ровно одном выборе.
  - choose_all — любая неверная опция даёт 0; без неверных — частичный балл пропорционален числу правильных.
  - matching — частичный балл как доля совпавших пар × балл вопроса.
  - open_question — всегда требует ручной оценки (`score` выставляет учитель через bulk-grade или по одному ответу).
- Видимость результатов: если `reveal_results_at` пустое — сразу; иначе после указанного времени. Ученик может отметить просмотр через `view-results`.
- Разграничение доступа по ролям: ученик видит свои попытки/ответы; учитель — свои тесты и их попытки/ответы; schooladmin — в пределах своей школы; superadmin — всё.

---

## Быстрые шпаргалки (curl)

Создать тест:
```bash
curl -X POST http://localhost:8000/api/assessments/tests/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "course_section": 42,
    "title": "Алгебра: Квиз 1",
    "questions": [{"type":"multiple_choice","text":"2+2?","points":2,"position":1,
      "options":[{"text":"3","is_correct":false,"position":1},{"text":"4","is_correct":true,"position":2}]}]
  }'
```

Начать попытку:
```bash
curl -X POST http://localhost:8000/api/assessments/attempts/start/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"test_id":101}'
```

Ответить на вопрос (multiple_choice):
```bash
curl -X POST http://localhost:8000/api/assessments/attempts/9001/submit-answer/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question_id":1001,"selected_option_ids":[2002]}'
```

Завершить попытку:
```bash
curl -X POST http://localhost:8000/api/assessments/attempts/9001/submit/ \
  -H "Authorization: Bearer $TOKEN"
```


## 📅 Events (Timetable and School Events)

### Overview
The Events API provides a unified way to manage timetable lessons and general school events. Events can target a whole `school`, a `subject_group`, or a specific `course_section`.

- Types: `lesson`, `school_event`, `other`
- Fields: `title`, `description`, `type`, `start_at`, `end_at`, `is_all_day`, `location`, `school`, `subject_group`, `course_section`
- Role-aware access: students/teachers see relevant events; admins see their school; superadmins see all.

Base URL prefix: `http://localhost:8000/api/`

### List Events
```http
GET /api/events/
Authorization: Bearer <token>

# Optional filters
GET /api/events/?type=lesson&subject_group=12&start_date=2025-09-01&end_date=2025-12-31
```

- Filters: `type`, `school`, `subject_group`, `course_section`, `start_date`, `end_date`
- Search: `?search=<text>` over `title`/`description`
- Ordering: `?ordering=start_at` (or `-start_at`, `title`, `end_at`)

Response (paginated):
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 101,
      "title": "Algebra lesson",
      "description": "Regular class",
      "type": "lesson",
      "start_at": "2025-09-01T14:00:00Z",
      "end_at": "2025-09-01T14:45:00Z",
      "is_all_day": false,
      "location": "Room 302",
      "school": 1,
      "subject_group": 12,
      "course_section": null,
      "created_by": 55,
      "created_at": "2025-09-01T08:00:00Z",
      "updated_at": "2025-09-01T08:00:00Z"
    }
  ]
}
```

### Create Single Event
```http
POST /api/events/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "School Assembly",
  "description": "Welcome back!",
  "type": "school_event",
  "start_at": "2025-09-02T10:00:00Z",
  "end_at": "2025-09-02T11:00:00Z",
  "is_all_day": false,
  "location": "Main Hall",
  "school": 1
}
```

Response:
```json
{
  "id": 202,
  "title": "School Assembly",
  "type": "school_event",
  "start_at": "2025-09-02T10:00:00Z",
  "end_at": "2025-09-02T11:00:00Z",
  "school": 1,
  "subject_group": null,
  "course_section": null
}
```

### Retrieve / Update / Delete
```http
GET    /api/events/{id}/
PATCH  /api/events/{id}/
DELETE /api/events/{id}/
Authorization: Bearer <token>
```

### Create Recurring Lesson Events
Generate weekly lesson events on chosen weekdays between dates. If `end_date` is omitted, it defaults to May 25 of the corresponding academic year (Sep 1 → May 25).

```http
POST /api/events/create-recurring/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Algebra lesson",
  "description": "Regular class",
  "location": "Room 302",
  "subject_group": 12,
  "start_date": "2025-09-01",
  "end_date": "2025-12-21",        // optional; defaults to academic-year May 25 if omitted
  "weekdays": [0, 2, 4],             // 0=Mon, 2=Wed, 4=Fri
  "start_time": "14:00:00",
  "end_time": "14:45:00"
}
```

Response:
```json
{ "created": 42 }
```

Validation rules:
- `end_time` must be after `start_time`.
- If provided, `end_date` must be on/after `start_date`.
- At least one target must be set: `subject_group`, `course_section`, or `school`.

Notes:
- All created recurring events are of type `lesson`.
- Role-based access limits which events a user can see:
  - Student: events for their school and their subject groups
  - Teacher: events for their school and the subject groups they teach
  - School admin: events in their school
  - Superadmin: all events

### Filtering Examples
```http
# All lessons for a subject group in September
GET /api/events/?type=lesson&subject_group=12&start_date=2025-09-01&end_date=2025-09-30

# School-wide events only
GET /api/events/?type=school_event&school=1

# Search by title/description
GET /api/events/?search=algebra
```

