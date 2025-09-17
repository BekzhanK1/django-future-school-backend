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

## 🧪 Assessments (Tests)

### Tests
```http
GET    /api/tests/                      # List tests
POST   /api/tests/                      # Create test
GET    /api/tests/{id}/                 # Get test with questions
PUT    /api/tests/{id}/                 # Update test
DELETE /api/tests/{id}/                 # Delete test

# Test management
POST   /api/tests/{id}/publish/         # Publish test
POST   /api/tests/{id}/unpublish/       # Unpublish test
```

### Questions
```http
GET    /api/questions/                  # List questions
POST   /api/questions/                  # Create question
GET    /api/questions/{id}/             # Get question details
PUT    /api/questions/{id}/             # Update question
DELETE /api/questions/{id}/             # Delete question
```

### Test Attempts
```http
GET    /api/attempts/                   # List attempts
POST   /api/attempts/start/             # Start new attempt
GET    /api/attempts/{id}/              # Get attempt with answers
POST   /api/attempts/{id}/submit/       # Submit attempt
POST   /api/attempts/{id}/submit-answer/ # Submit answer for question
```

### Test Answers
```http
GET    /api/answers/                    # List answers
POST   /api/answers/                    # Create answer
GET    /api/answers/{id}/               # Get answer details
PUT    /api/answers/{id}/               # Update answer
DELETE /api/answers/{id}/               # Delete answer

# Bulk grade answers (for open questions)
POST   /api/answers/bulk-grade/
[
  {
    "answer_id": 1,
    "score": 8
  },
  {
    "answer_id": 2,
    "score": 10
  }
]
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
