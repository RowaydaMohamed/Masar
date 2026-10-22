# Engine Documentation (Masar)

The academic engine (`academics/engine.py`) provides pure, read-only functions to calculate student progression and course availability without writing to the database.

## Key Concepts

- **Counted Attempt:** Evaluates the latest graded attempt (completed or failed) for a course. Withdrawn or registered attempts are ignored. A passed course cannot be retaken for grade improvement.
- **Student Plan:** Aggregates courses from the `general` and `faculty` pools, plus the `department` pool if the student has chosen one. Courses outside this plan yield zero credits toward the 144 required hours.
- **Course Statuses (`compute_course_statuses`):** Priority mapping: `registered` -> `done` -> `failed` -> `locked` / `available`. Takes prerequisite fulfillment and academic level into consideration.
- **Academic Level & Standing:** Level is dynamically deduced based on `min_earned_hours` via `LevelThreshold` (36 hours per level). The standing string outputs formats like "سنة أولى مستجد" or "مستمر".
- **Path Algorithm (`graduation_path` view):** The graduation path is computed live by evaluating remaining unpassed plan courses against dependencies (prerequisites), terms, and credit limits using an in-degree graph sorting simulation.