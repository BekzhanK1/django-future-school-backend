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
