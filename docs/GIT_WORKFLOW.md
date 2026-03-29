# Git Workflow

This project uses Git to keep a stable baseline while allowing feature work without breaking the app.

## Branch Strategy

### Stable branch
- `main`
  - Always runnable
  - Only merge tested work here

### Working branches
- `feature/<name>`
  - New features
- `fix/<name>`
  - Bug fixes and regressions
- `refactor/<name>`
  - Cleanup and structure changes without intended feature changes
- `release/<name>`
  - Optional release prep branches

## Recommended branch names

```bash
feature/live-graph-filtering
feature/map-optimization
feature/timeline-dataset-expansion
fix/translation-switch-semantic
fix/prev-next-navigation
refactor/event-controller
```

## Daily Workflow

### 1. Start from stable main

```bash
git checkout main
git status
```

If you later connect a remote, also run:

```bash
git pull
```

### 2. Create a branch for new work

```bash
git checkout -b feature/my-new-feature
```

### 3. Make focused commits

```bash
git add app/ui/main_window.py
git commit -m "fix: restore prev and next verse navigation"
```

### 4. Test before merging

Run the app and verify the core checklist:
- app launches
- translation switch works
- single verse read works
- chapter read works
- prev/next verse works
- timeline select works
- map link works
- graph click works
- semantic search works
- study guide works

### 5. Merge back into main only when stable

```bash
git checkout main
git merge --no-ff feature/my-new-feature
```

### 6. Delete finished branch

```bash
git branch -d feature/my-new-feature
```

## Tagging Stable Baselines

Use tags to freeze known-good milestones.

### Create a tag

```bash
git tag -a v0.3-phase3-stable -m "Phase 3 stable baseline"
```

### List tags

```bash
git tag
```

### Restore a tag

```bash
git checkout v0.3-phase3-stable
```

### Create a recovery branch from a tag

```bash
git checkout -b restore-phase3 v0.3-phase3-stable
```

## No Remote Yet

If you see:

```bash
fatal: 'origin' does not appear to be a git repository
```

it means this repo does not have a remote configured yet.

### Check remotes

```bash
git remote -v
```

### Add a remote later

Example:

```bash
git remote add origin <your-repo-url>
git push -u origin main
git push origin v0.3-phase3-stable
```

Until then, your commits and tags are still saved locally.

## Useful Commands

### Check status

```bash
git status
```

### View branches

```bash
git branch
```

### Switch branches

```bash
git checkout main
git checkout feature/my-new-feature
```

### Compare changes

```bash
git diff
git diff main..feature/my-new-feature
```

### View history

```bash
git log --oneline --graph --decorate --all
```

### Unstage a file

```bash
git restore --staged app/ui/main_window.py
```

### Discard local changes to one file

```bash
git checkout -- app/ui/main_window.py
```

## Backup Archive

Create a zip snapshot from a stable tag:

```bash
git archive -o phase3_stable.zip v0.3-phase3-stable
```

## Commit Message Style

Use short, clear messages.

Examples:

```bash
fix: restore prev and next verse navigation
feature: add split timeline and map explorer
refactor: move event orchestration into focus_on_event
perf: cache selected event map exports
data: expand timeline events dataset
```

## Project Rule Set

1. Do not work directly on `main`
2. Use one branch per feature or fix
3. Tag every known-good milestone
4. Run the regression checklist before merging
5. If a branch gets messy, start a fresh branch from `main`

## Recommended Next Branches

```bash
git checkout main
git checkout -b feature/map-optimization
```

```bash
git checkout main
git checkout -b feature/live-graph-filtering
```

```bash
git checkout main
git checkout -b fix/translation-switch-semantic
```
