# Masar Backend — Local Development Guide

This directory contains the Django backend and API for the Masar project. Follow the instructions below to set up your local development environment.

## Prerequisites

Ensure you have Python installed on your system before proceeding.

## Setup Instructions

**1. Navigate to the backend directory**
Open your terminal and ensure you are inside the backend folder:

```bash
cd backend
```

**2. Create the virtual environment**
Generate a quarantined Python environment to keep project dependencies isolated:

```bash
python -m venv venv
```

**3. Activate the virtual environment**
You must activate the environment every time you work on the backend. Use the command that matches your operating system and terminal:

- **Windows (PowerShell):** `.\venv\Scripts\activate`
- **Windows (Git Bash):** `source venv/Scripts/activate`
- **Ubuntu / Linux / Mac:** `source venv/bin/activate`

_(Note: You will know it is activated when `(venv)` appears at the beginning of your terminal prompt line.)_

**4. Install project dependencies**
Install Django, Django REST Framework, and any other required packages from the blueprint file:

```bash
pip install -r requirements.txt
```

**5. Start the local development server**
Boot up the server to confirm everything is installed correctly:

```bash
python manage.py runserver
```

Navigate to `http://127.0.0.1:8000/` in your web browser. If the setup was successful, you will see the default Django welcome page.
