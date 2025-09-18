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

## 🎯 Frontend Integration Guide for Tests

### 1. Teacher: Creating Tests

#### Create Test with Questions
```javascript
// POST /api/assessments/tests/
const createTest = async (testData) => {
  const response = await fetch('/api/assessments/tests/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      course_section: 1,
      title: "Math Quiz",
      description: "Basic math concepts",
      time_limit_minutes: 30,
      allow_multiple_attempts: true,
      max_attempts: 3,
      show_correct_answers: true,
      show_feedback: true,
      show_score_immediately: false,
      reveal_results_at: "2024-01-15T10:00:00Z",
      questions: [
        {
          type: "multiple_choice",
          text: "What is 2 + 2?",
          points: 5,
          position: 1,
          options: [
            { text: "3", is_correct: false, position: 1 },
            { text: "4", is_correct: true, position: 2 },
            { text: "5", is_correct: false, position: 3 }
          ]
        },
        {
          type: "choose_all",
          text: "Which are prime numbers?",
          points: 10,
          position: 2,
          options: [
            { text: "2", is_correct: true, position: 1 },
            { text: "3", is_correct: true, position: 2 },
            { text: "4", is_correct: false, position: 3 },
            { text: "5", is_correct: true, position: 4 }
          ]
        },
        {
          type: "open_question",
          text: "Explain photosynthesis",
          points: 15,
          position: 3,
          correct_answer_text: "Process by which plants convert sunlight to energy",
          sample_answer: "Plants use sunlight, water, and CO2 to create glucose"
        },
        {
          type: "matching",
          text: "Match countries with capitals",
          points: 20,
          position: 4,
          matching_pairs_json: [
            { left: "France", right: "Paris" },
            { left: "Germany", right: "Berlin" },
            { left: "Spain", right: "Madrid" }
          ]
        }
      ]
    })
  });
  return response.json();
};
```

#### Add Questions to Existing Test
```javascript
// POST /api/assessments/questions/
const addQuestion = async (testId, questionData) => {
  const response = await fetch('/api/assessments/questions/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      test: testId,
      type: "multiple_choice",
      text: "What is the capital of France?",
      points: 10,
      position: 5,
      options: [
        { text: "London", is_correct: false, position: 1 },
        { text: "Paris", is_correct: true, position: 2 },
        { text: "Berlin", is_correct: false, position: 3 }
      ]
    })
  });
  return response.json();
};
```

### 2. Student: Taking Tests

#### Start Test Attempt
```javascript
// POST /api/assessments/attempts/start/
const startTest = async (testId) => {
  const response = await fetch('/api/assessments/attempts/start/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ test_id: testId })
  });
  return response.json();
};
```

#### Submit Answer for Question
```javascript
// POST /api/assessments/attempts/{id}/submit-answer/
const submitAnswer = async (attemptId, questionId, answerData) => {
  const response = await fetch(`/api/assessments/attempts/${attemptId}/submit-answer/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      question_id: questionId,
      // For multiple choice
      selected_option_ids: [2, 3],
      // For open questions
      text_answer: "My detailed answer here",
      // For matching questions
      matching_answers_json: [
        { left: "France", right: "Paris" },
        { left: "Germany", right: "Berlin" }
      ]
    })
  });
  return response.json();
};
```

#### Submit Completed Test
```javascript
// POST /api/assessments/attempts/{id}/submit/
const submitTest = async (attemptId) => {
  const response = await fetch(`/api/assessments/attempts/${attemptId}/submit/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
};
```

### 3. Frontend UI Components

#### Test List Component
```javascript
const TestList = () => {
  const [tests, setTests] = useState([]);
  
  useEffect(() => {
    fetch('/api/assessments/tests/', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => setTests(data.results));
  }, []);

  return (
    <div>
      {tests.map(test => (
        <div key={test.id} className="test-card">
          <h3>{test.title}</h3>
          <p>{test.description}</p>
          <p>Points: {test.total_points}</p>
          <p>Time Limit: {test.time_limit_minutes} minutes</p>
          <p>Status: {test.is_published ? 'Published' : 'Draft'}</p>
          {test.can_attempt && (
            <button onClick={() => startTest(test.id)}>
              Start Test
            </button>
          )}
        </div>
      ))}
    </div>
  );
};
```

#### Question Component
```javascript
const QuestionComponent = ({ question, attemptId, onAnswerSubmit }) => {
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [textAnswer, setTextAnswer] = useState('');
  const [matchingAnswers, setMatchingAnswers] = useState([]);

  const handleSubmit = () => {
    let answerData = { question_id: question.id };
    
    if (question.type === 'multiple_choice' || question.type === 'choose_all') {
      answerData.selected_option_ids = selectedOptions;
    } else if (question.type === 'open_question') {
      answerData.text_answer = textAnswer;
    } else if (question.type === 'matching') {
      answerData.matching_answers_json = matchingAnswers;
    }
    
    onAnswerSubmit(attemptId, question.id, answerData);
  };

  return (
    <div className="question">
      <h4>{question.text}</h4>
      <p>Points: {question.points}</p>
      
      {question.type === 'multiple_choice' && (
        <div>
          {question.options.map(option => (
            <label key={option.id}>
              <input
                type="radio"
                name={`question_${question.id}`}
                value={option.id}
                onChange={(e) => setSelectedOptions([parseInt(e.target.value)])}
              />
              {option.text}
              {option.image_url && <img src={option.image_url} alt="Option" />}
            </label>
          ))}
        </div>
      )}
      
      {question.type === 'choose_all' && (
        <div>
          {question.options.map(option => (
            <label key={option.id}>
              <input
                type="checkbox"
                value={option.id}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedOptions([...selectedOptions, option.id]);
                  } else {
                    setSelectedOptions(selectedOptions.filter(id => id !== option.id));
                  }
                }}
              />
              {option.text}
              {option.image_url && <img src={option.image_url} alt="Option" />}
            </label>
          ))}
        </div>
      )}
      
      {question.type === 'open_question' && (
        <textarea
          value={textAnswer}
          onChange={(e) => setTextAnswer(e.target.value)}
          placeholder="Enter your answer..."
          rows={5}
        />
      )}
      
      {question.type === 'matching' && (
        <MatchingComponent
          pairs={question.matching_pairs_json}
          onAnswersChange={setMatchingAnswers}
        />
      )}
      
      <button onClick={handleSubmit}>Submit Answer</button>
    </div>
  );
};
```

#### Matching Component
```javascript
const MatchingComponent = ({ pairs, onAnswersChange }) => {
  const [matches, setMatches] = useState([]);
  
  const leftItems = pairs.map(pair => pair.left);
  const rightItems = pairs.map(pair => pair.right);
  
  const handleMatch = (leftItem, rightItem) => {
    const newMatch = { left: leftItem, right: rightItem };
    setMatches([...matches, newMatch]);
    onAnswersChange([...matches, newMatch]);
  };
  
  return (
    <div className="matching-container">
      <div className="left-column">
        {leftItems.map((item, index) => (
          <div key={index} className="match-item">
            {item}
          </div>
        ))}
      </div>
      <div className="right-column">
        {rightItems.map((item, index) => (
          <div key={index} className="match-item">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 4. Test Timer Component
```javascript
const TestTimer = ({ timeLimitMinutes, onTimeUp }) => {
  const [timeLeft, setTimeLeft] = useState(timeLimitMinutes * 60);
  
  useEffect(() => {
    if (timeLeft <= 0) {
      onTimeUp();
      return;
    }
    
    const timer = setTimeout(() => {
      setTimeLeft(timeLeft - 1);
    }, 1000);
    
    return () => clearTimeout(timer);
  }, [timeLeft, onTimeUp]);
  
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  return (
    <div className={`timer ${timeLeft < 300 ? 'warning' : ''}`}>
      Time Remaining: {formatTime(timeLeft)}
    </div>
  );
};
```

### 5. Results Viewing
```javascript
const TestResults = ({ attemptId }) => {
  const [attempt, setAttempt] = useState(null);
  
  useEffect(() => {
    fetch(`/api/assessments/attempts/${attemptId}/`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => setAttempt(data));
  }, [attemptId]);
  
  if (!attempt) return <div>Loading...</div>;
  
  return (
    <div className="test-results">
      <h2>Test Results</h2>
      <p>Score: {attempt.score}/{attempt.max_score}</p>
      <p>Percentage: {attempt.percentage}%</p>
      <p>Time Spent: {attempt.time_spent_minutes} minutes</p>
      
      {attempt.answers.map(answer => (
        <div key={answer.id} className="answer-result">
          <h4>{answer.question_text}</h4>
          <p>Your Answer: {answer.text_answer || answer.selected_options.map(opt => opt.text).join(', ')}</p>
          <p>Score: {answer.score}/{answer.max_score}</p>
          {answer.teacher_feedback && (
            <p>Feedback: {answer.teacher_feedback}</p>
          )}
        </div>
      ))}
    </div>
  );
};
```

### 6. Teacher Grading Interface
```javascript
const GradingInterface = ({ testId }) => {
  const [answers, setAnswers] = useState([]);
  
  const gradeAnswer = async (answerId, score, feedback) => {
    await fetch('/api/assessments/answers/bulk-grade/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify([{
        answer_id: answerId,
        score: score,
        teacher_feedback: feedback
      }])
    });
  };
  
  return (
    <div className="grading-interface">
      {answers.map(answer => (
        <div key={answer.id} className="grading-item">
          <h4>{answer.question_text}</h4>
          <p>Student Answer: {answer.text_answer}</p>
          <input
            type="number"
            placeholder="Score"
            onChange={(e) => setScore(answer.id, e.target.value)}
          />
          <textarea
            placeholder="Feedback"
            onChange={(e) => setFeedback(answer.id, e.target.value)}
          />
          <button onClick={() => gradeAnswer(answer.id, score, feedback)}>
            Grade
          </button>
        </div>
      ))}
    </div>
  );
};
```

### 7. Key Frontend Considerations

#### Error Handling
```javascript
const handleApiError = (error) => {
  if (error.status === 401) {
    // Redirect to login
    window.location.href = '/login';
  } else if (error.status === 403) {
    // Show access denied message
    alert('You do not have permission to access this resource');
  } else if (error.status === 400) {
    // Show validation errors
    console.error('Validation errors:', error.detail);
  }
};
```

#### Real-time Updates
```javascript
// Use WebSocket or polling for real-time updates
const useTestUpdates = (testId) => {
  useEffect(() => {
    const interval = setInterval(() => {
      // Check for test updates
      fetch(`/api/assessments/tests/${testId}/`)
        .then(res => res.json())
        .then(data => {
          // Update UI with new data
        });
    }, 30000); // Poll every 30 seconds
    
    return () => clearInterval(interval);
  }, [testId]);
};
```

#### State Management
```javascript
// Use Redux, Zustand, or Context for state management
const useTestStore = create((set) => ({
  currentTest: null,
  currentAttempt: null,
  answers: [],
  setCurrentTest: (test) => set({ currentTest: test }),
  addAnswer: (answer) => set((state) => ({
    answers: [...state.answers, answer]
  })),
  updateAnswer: (answerId, updates) => set((state) => ({
    answers: state.answers.map(answer =>
      answer.id === answerId ? { ...answer, ...updates } : answer
    )
  }))
}));
```

This comprehensive guide should help your frontend developer implement the complete test system with all question types, scoring, and management features!

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
