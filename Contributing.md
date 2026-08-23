# Contributing to Masar

This file explains, step by step, exactly how we work as a team — Git branches, environment variables, and our CI (automated checks). If you're new to any of this, read the whole thing once before your first task. Nothing here assumes you already know Git beyond the very basics.

---

## Part 1 — Why we have two main branches

We have two permanent branches in this repo:

- **`main`** — this is the "always works" branch. If a professor or anyone outside the team opened this branch right now, it should run without errors. Nobody ever pushes to `main` directly.
- **`develop`** — this is where everyone's finished features get combined and tested together *before* they're trusted enough to go into `main`.

**Why not just use `main` for everything?** Because with 6 people working at once, code from different people needs a place to meet and get tested together first. If everyone pushed straight to `main`, one person's half-finished or buggy feature could break the branch we'd actually use to demo the project. `develop` is our safety buffer — it's fine if it's a little broken sometimes, `main` is not.

You will **never** work directly on `main` or `develop`. Every single task — big or small — happens in its own **feature branch**.

---

## Part 2 — A note for Windows users

If you're on Windows, you have two options for running the commands in this file:

1. **Command Prompt (`cmd.exe`)** — works, but some commands need Windows-style syntax (backslashes `\` instead of `/`, no `-p` flags on `mkdir`, etc.)
2. **Git Bash** — installed automatically with Git. Every command in this file (and in nearly every tutorial online) works exactly as written here, no translation needed.

**Recommendation: use Git Bash.** Right-click inside your project folder in File Explorer → **"Git Bash Here"**. If that option isn't there, search "Git Bash" in the Start menu and then `cd` into your project folder manually.

All commands below are written for Git Bash / Mac / Linux style. If you're stuck in `cmd.exe` and a command doesn't work, that's almost always why — ask in the group chat and mention you're on `cmd`, not Git Bash.

---

## Part 3 — Starting any new task, step by step

**Step 1 — Update your local `develop` branch.** This makes sure you're building on top of the latest code, not something outdated.
```bash
git checkout develop
git pull origin develop
```

**Step 2 — Create your own branch off `develop`.** Name it after your task, using the pattern `feature/short-name`:
```bash
git checkout -b feature/login-api
```
More examples: `feature/course-tree-component`, `feature/docker-backend`, `feature/ci-hello-check`

**Step 3 — Do your work.** Write code, create files, whatever the task needs.

**Step 4 — Commit your changes.** A commit is a "save point" with a message describing what you did. Commit in small, meaningful chunks rather than one giant commit at the end — it's much easier for teammates (and future-you) to understand.
```bash
git add .
git commit -m "Add login endpoint with JWT auth"
```
- `git add .` stages *all* your changed files, telling Git "include these in the next commit"
- `git commit -m "..."` actually saves that snapshot, with a message explaining what changed

**Commit message style:** say *what* changed, not "fixed stuff":
- Good: `Add prerequisite-check logic for course registration`
- Not helpful: `updates`, `fix`, `asdf`

**Step 5 — Push your branch to GitHub.**
```bash
git push origin feature/login-api
```
(First time pushing a new branch, Git might show you the exact command with `--set-upstream` — just copy-paste what it suggests.)

**Step 6 — Open a Pull Request (PR) on GitHub.** Go to the repo on GitHub, you'll usually see a yellow banner suggesting "Compare & pull request" for your branch — click it. Make sure it's comparing your branch **into `develop`** (not `main`). Write a short description of what you did.

**Step 7 — Wait for the automatic checks to run.** You'll see a section on the PR page with a yellow dot (running) that turns into a green check (passed) or red X (failed) within a few seconds — this is our CI pipeline (explained in Part 5 below) automatically checking your code.

**Step 8 — Get it reviewed.** At least one teammate should look at your PR and approve it before merging — even a quick "looks good" comment counts. This is how small mistakes get caught before they reach `develop`, not after.

**Step 9 — Merge.** Once approved (and checks are green), click **Merge pull request** on GitHub.

**Step 10 — Delete the branch.** GitHub shows a button right after merging — click it. The branch has done its job; no need to keep it around.

**Step 11 — Sync your local machine.**
```bash
git checkout develop
git pull origin develop
```
Now you're ready to start your next task from Step 1 again.

---

## Part 4 — Environment variables and `.env.example`

**The problem:** Our app needs secret or personal config values to run — a database password, an API key, etc. These can **never** be written directly into our code and pushed to GitHub, because then anyone who can see the repo can see the secret too.

**The solution — two files:**

1. **`.env`** — a file *on your own computer only*, containing your real secrets. It is listed in `.gitignore`, meaning Git is told to never track or upload it. You create this file yourself locally; it never touches GitHub.
2. **`.env.example`** — a *safe, fake* version that *does* live in the repo. It lists the variable **names** the project needs, with placeholder values — no real secrets. This is how a teammate cloning the repo knows exactly what to put in their own `.env` file, without asking around.

Example of what `.env.example` looks like:
```
# Django
SECRET_KEY=your-django-secret-key-here
DEBUG=True

# Database
DATABASE_NAME=masar_db
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password-here
DATABASE_HOST=localhost
DATABASE_PORT=5432

# AI chatbot
ANTHROPIC_API_KEY=your-anthropic-key-here
```

**When you join a task that needs a `.env`:** copy `.env.example`, rename your copy to `.env`, and fill in your own real values. Never commit your real `.env` — if `git status` ever shows `.env` as a file ready to commit, stop and check your `.gitignore`.

---

## Part 5 — What our CI pipeline actually does (and how we know it works)

**CI stands for Continuous Integration** — it just means "GitHub automatically runs some checks every time someone opens a Pull Request," instead of us running checks by hand and possibly forgetting.

**Where it lives:** a file at `.github/workflows/ci.yml` in the repo. This is a YAML file (a simple text format) that tells GitHub: *when X happens, do Y.*

**What we have right now** (our very first, intentionally simple version):
```yaml
name: CI Check

on: [pull_request]

jobs:
  hello:
    runs-on: ubuntu-latest
    steps:
      - name: Say hello
        run: echo "CI is alive"
```

**Reading it line by line:**
- `name:` — just a label, shown on GitHub's PR page
- `on: [pull_request]` — *when* this runs: every time a PR is opened or updated
- `jobs:` — the list of tasks to run
- `hello:` — a name we picked for this particular task
- `runs-on: ubuntu-latest` — GitHub gives us a free, temporary Linux computer to run this on
- `steps:` — the actual list of things to do, in order
- `run: echo "CI is alive"` — the one command it executes: just print a message

**Why start this simple instead of writing real tests immediately?** If we'd jumped straight to "run all our Django tests" and it failed, we wouldn't know if the problem was *the pipeline itself* not being wired up correctly, or *the tests* being broken. Proving the wiring works first with something trivial means any future failure is actually about real code, not setup.

**What you'll see on a working PR** (we already confirmed this works):
- **"CI Check / hello (pull_request)"** — our own check, confirming the pipeline runs
- **"GitGuardian Security Checks"** — an extra automatic check (added at the repo level) that scans for accidentally committed secrets, like API keys. If this ever fails, **do not ignore it** — it means a real secret got committed and needs to be removed and rotated (i.e. get a new key).

**What happens next, over time:** whoever works on real backend testing will replace the one line `run: echo "CI is alive"` with real steps — installing Django, running `pytest`, etc. The rest of the file (the `on:`, `jobs:`, `runs-on:` structure) barely changes. We built the skeleton; later tasks just fill it in.

---

## Part 6 — A few rules that keep things from breaking

- **Never push directly to `main` or `develop`.** Always go through a feature branch + PR, even for a one-line fix.
- **Always pull `develop` before branching**, every time — otherwise you might build on outdated code and hit painful merge conflicts later.
- **One feature branch = one task.** Don't pile unrelated changes into the same branch; it makes reviews slower and harder.
- **If your branch takes more than a few days**, pull the latest `develop` into it periodically so you don't drift too far:
  ```bash
  git checkout feature/your-branch
  git pull origin develop
  ```
- **`main` only updates at agreed checkpoints**, when `develop` is stable — not automatically on every single merge. The team lead handles merging `develop` → `main`.

---

## Part 7 — If you're stuck

If a merge conflict looks scary, a git error message doesn't make sense, or a CI check fails and you don't know why — **ask in the group chat before you force-push, delete a branch, or try to "fix" it alone with commands you're not sure about.** Almost every Git mistake is easily fixable if we catch it early. Most only become painful when someone panics and runs commands they don't fully understand.