# Masar Backend API Documentation

## 1. Authentication

### Register Student

- **URL:** `/api/auth/register/`
- **Method:** `POST`
- **Body:**
    ```json
    {
        "university_id": "2024123456",
        "full_name": "Student Name",
        "full_name_ar": "اسم الطالب",
        "email": "student@fci.edu.eg",
        "password": "strongpassword123",
        "admission_semester_id": 1,
        "academic_level": 1
    }
    ```
    _(Note: `full_name_ar`, `admission_semester_id`, and `academic_level` are optional. If `admission_semester_id` is omitted, the system defaults to the current active semester)._

### Login

- **URL:** `/api/auth/login/`
- **Method:** `POST`
- **Body:**
    ```json
    {
        "identifier": "2024123456",
        "password": "strongpassword123"
    }
    ```
    _(Note: `identifier` accepts either the University ID or the student's email address)._
- **Returns:** A JSON object containing the `access` and `refresh` JWT tokens.

### Get My Profile

- **URL:** `/api/auth/me/`
- **Method:** `GET`
- **Headers Required:** `Authorization: Bearer <access_token>`
- **Returns:**
    ```json
    {
        "university_id": "2024123456",
        "email": "student@fci.edu.eg",
        "full_name": "Student Name",
        "full_name_ar": "اسم الطالب",
        "academic_level": 1,
        "department": {
            "code": "CS",
            "name": "Computer Science",
            "name_ar": "علوم الحاسب"
        },
        "standing": "new",
        "status": "active"
    }
    ```
    _(Note: `department` will be `null` if the student has not specialized yet)._

## 2. Core Features & AI

### System Ping

- **URL:** `/api/ping/`
- **Method:** `GET`

### Get All Courses

- **URL:** `/api/courses/`
- **Method:** `GET`

### Student Dashboard

- **URL:** `/api/dashboard/`
- **Method:** `GET`
- **Headers Required:** `Authorization: Bearer <access_token>`

### Predict Specialization

- **URL:** `/api/predict/`
- **Method:** `POST`
- **Headers Required:** `Authorization: Bearer <access_token>`
- **Body:**
    ```json
    {
        "grades": [
            85, 90, 78, 92, 88, 85, 90, 78, 92, 88, 85, 90, 78, 92, 88, 85, 90,
            78, 92, 88, 85, 90, 78, 92
        ]
    }
    ```
    _(Note: The `grades` array MUST contain exactly 24 numerical values representing the course grades in order)._

## 3. Specializations & Trees

### Get All Specializations

- **URL:** `/api/specializations/`
- **Method:** `GET`
- **Headers Required:** `Authorization: Bearer <access_token>`
- **Returns:** List of active departments (CS, IT, IS, AI) with their compulsory and elective hours.

### Get Specialization Curriculum Tree

- **URL:** `/api/specializations/<code>/tree/`
- **Method:** `GET`
- **Headers Required:** `Authorization: Bearer <access_token>`
- **Returns:** The static curriculum map for the department (including General, Faculty, and Department courses), marking which courses are shared.

### Set/Update Student Specialization

- **URL:** `/api/me/specialization/`
- **Method:** `PUT`
- **Headers Required:** `Authorization: Bearer <access_token>`
- **Body:**
    ```json
    {
        "department_code": "CS"
    }
    ```

## 4. Courses & Requests

### Get Course Details

- **URL:** `/api/courses/<code>/`
- **Method:** `GET`
- **Headers Required:** `Authorization: Bearer <access_token>`
- **Returns:** Detailed course card info (credits, prerequisites, description) and the student's personal status for that course.

### 7th-Course Overload Request

- **URL:** `/api/seventh-request/`
- **Method:** `POST`
- **Headers Required:** `Authorization: Bearer <access_token>`
- **Body:**
    ```json
    {
        "course_code": "CS415",
        "reason": "Need this to graduate next semester"
    }
    ```

### Summer Course Demands

- **URL:** `/api/summer-requests/`
- **Method:** `GET` / `POST`
- **Headers Required:** `Authorization: Bearer <access_token>`
- **GET Returns:** List of courses the student is eligible to request for summer, plus their already-submitted requests.
- **POST Body:**
    ```json
    {
        "course_codes": ["CS214", "IT221"]
    }
    ```
