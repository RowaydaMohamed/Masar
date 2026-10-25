# Masar Backend API Documentation

## 1. Authentication

### Register Student

- **URL:** `/api/auth/register/`
- **Method:** `POST`
- **Body:**
  {
  "university_id": "2024123456",
  "full_name": "Student Name",
  "email": "student@fci.edu.eg",
  "password": "strongpassword123",
  "entry_year": 2026,
  "academic_level": 1
  }
  _(Note: `entry_year` and `academic_level` are optional)_

### Login

- **URL:** `/api/auth/login/`
- **Method:** `POST`
- **Body:**
  {
  "email": "student@fci.edu.eg",
  "password": "strongpassword123"
  }
- **Returns:** A JSON object containing the `access` and `refresh` JWT tokens.

### Get My Profile

- **URL:** `/api/auth/me/`
- **Method:** `GET`
- **Headers Required:** `Authorization: Bearer <access_token>`

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
  {
  "grades": [85, 90, 78, 92, 88, 85, 90, 78, 92, 88, 85, 90, 78, 92, 88, 85, 90, 78, 92, 88, 85, 90, 78, 92]
  }
  _(Note: The `grades` array MUST contain exactly 24 numerical values representing the course grades in order)._
