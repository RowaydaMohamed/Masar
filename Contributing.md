# Contributing to Masar

This file explains exactly how we work with Git as a team. Read it once — it answers most "wait, what do I do?" questions before they happen.

## The two main branches

- **`main`** — always working, always demo-ready. Nobody pushes to this directly. It only receives code that's already been tested in `develop`.
- **`develop`** — where everyone's features come together and get tested against each other before they're considered "done."

You never work directly on either of these. You always work in your own **feature branch**.

## Starting any new task

1. Make sure your local `develop` is up to date:
   ```bash
   git checkout develop
   git pull origin develop
   ```
2. Create your own branch off `develop`, named after your task:
   ```bash
   git checkout -b feature/short-task-name
   ```
   Examples: `feature/login-api`, `feature/course-tree-component`, `feature/docker-backend`

3. Do your work. Commit as often as makes sense — small, clear commits are easier for everyone (including future-you) to understand than one giant commit at the end.
   ```bash
   git add .
   git commit -m "Add login endpoint with JWT auth"
   ```

4. Push your branch:
   ```bash
   git push origin feature/short-task-name
   ```

5. On GitHub, open a **Pull Request (PR)** from your branch into `develop`. Write a short description of what you did.

6. **Get at least one teammate to review it** before merging — even a quick "looks fine" comment counts. This is how bugs get caught early instead of during the defense.

7. Once approved, merge the PR into `develop`, then delete your feature branch (GitHub will offer you a button for this).

## A few rules that keep things from breaking

- **Never push directly to `main` or `develop`.** Always go through a feature branch + PR, even for tiny fixes.
- **Pull `develop` before you branch**, every time — otherwise you might build on top of outdated code and get messy conflicts later.
- **One feature branch = one task.** Don't pile unrelated changes into the same branch; it makes reviews harder and PRs slower to approve.
- **If your branch takes more than a few days**, pull the latest `develop` into it periodically so you don't drift too far and hit a wall of conflicts at the end:
  ```bash
  git checkout feature/your-branch
  git pull origin develop
  ```
- **`main` only updates when `develop` is stable and tested.** The team lead (or whoever we agree on) merges `develop` → `main` at agreed checkpoints, not automatically on every merge.

## Commit message style

Keep it short and say *what* changed, not "fixed stuff":
- Good: `Add prerequisite-check logic for course registration`
- Not great: `updates`, `fix`, `asdf`

## If you're stuck

If a merge conflict looks scary or you're not sure what a git error means — **ask in the group chat before you force-push or delete anything.** Almost every git mistake is fixable if we catch it early; most become painful only when someone tries to "fix" it alone with commands they don't fully understand yet.
