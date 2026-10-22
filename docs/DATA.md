# Masar Database — Demo Data

## 1. Environment

These accounts and records are for local development and demonstration only.

- Django Admin URL: http://127.0.0.1:8000/admin/

- Admin username: `demo_admin`
- Demo password: Set the `MASAR_DEMO_PASSWORD` environment variable before running the seed command.

The demo password is read from `MASAR_DEMO_PASSWORD`. Set this variable in your local environment before running the seed command. Never commit an actual password to the repository.

## 2. Demo Student Accounts

| Username | University ID | Scenario |
|---|---|---|
| `demo_new` | `20260001` | New Level 1 student with no department selected |
| `demo_l1_continuing` | `20250002` | Continuing Level 1 student with fewer than 36 earned credit hours |
| `demo_ai_features` | `20230003` | Level 3 student with no department, used to test AI specialization-feature courses |
| `demo_failed_prereq` | `20230004` | Level 3 CS student with a failed prerequisite scenario involving CS214 |
| `demo_retake_passed` | `20230005` | IT student whose history demonstrates failing a course and passing a later retake |
| `demo_near_graduation` | `20230006` | Level 4 AI student approaching the 144-credit-hour graduation requirement |
| `demo_seventh_eligible` | `20240007` | Student intended to demonstrate eligibility for a seventh course |
| `demo_seventh_ineligible` | `20240008` | Student intended to demonstrate ineligibility for a seventh course |


The seeded demo accounts use the password configured through the `MASAR_DEMO_PASSWORD` environment variable.

## 3. Seeded Data Snapshot

The successful seed command reported:

- Courses: 122
- Course prerequisites: 95
- Course offerings: 116
- Demo students: 8

The database audit reported:

- Enrollments: 224
- Student semester records: 33
- Summer requests: 8
- Seventh-course requests: 1
- Notifications: 16
- Specialization recommendations: 1
- Department changes: 3
- Course preferences: 4

These counts describe the database at the time of the audit. They can change when demo data or application workflows are run.

## 4. Important Notes

- The demo data is synthetic and intended for development and testing.
- The seeded grade scale and some configuration values are placeholders; confirm the official faculty rules before production use.
- A seeded scenario is not proof that its corresponding application workflow has been tested.
- Test registration eligibility, prerequisite enforcement, GPA calculations, request decisions, and notifications through the relevant services or API before declaring those workflows complete.
- Do not use the seed command with `--reset` on a database containing data that must be preserved.
