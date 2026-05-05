---
name: execute-issues
description: Execute GitHub issues for a phase sequentially - implement, validate, commit, push, and generate a report.
---

# Skill: Execute GitHub Issues

Execute GitHub issues for a phase sequentially: implement, validate, commit, push, and generate a report.

## Usage

```
/execute-issues <label> [--issue TDB-xxx] [--dry-run]
```

The `<label>` is the GitHub phase label exactly as it appears (e.g., `0.1::phase:1`).

- `/execute-issues 0.1::phase:1` — execute all issues labeled `0.1::phase:1`
- `/execute-issues 0.1::phase:1 --issue TDB-003` — execute a single issue from that phase
- `/execute-issues 0.1::phase:1 --dry-run` — show execution plan without making changes

## Instructions

### Step 0: Verify prerequisites

1. Confirm we are on the correct working branch (not `main` directly — create a feature branch like `phase-{y}` if needed)
2. Confirm working tree is clean (`git status`)
3. Confirm `gh` is authenticated (`gh auth status`)
4. Parse the label to determine version and phase:
   - Label `0.1::phase:1` → version `x=0`, phase `y=1`, target release `0.1.0`
5. Fetch issues from GitHub:
   ```bash
   gh issue list --label "{label}" --state open --limit 100
   ```
6. Read the phase issues file for detailed descriptions: `specification/implementation/phase-{y}-issues.md`
7. Read the phase tasks file: `specification/phases/phase{y}_*.md`
8. If a github report exists (`phase-{y}-github-report.md`), read the TDB-to-GitHub# mapping

### Step 1: Build execution queue

From the GitHub issue list, build an ordered queue based on dependencies:
- Parse TDB-xxx IDs from issue titles (format: `TDB-xxx: {title}`)
- Determine dependency order from the phase issues file dependency tree
- Issues with no unmet dependencies go first
- Skip issues already closed on GitHub
- If `--issue TDB-xxx` is specified, execute only that issue (but verify its dependencies are closed)

Show the user the execution plan and ask for confirmation.

### Step 2: Execute each issue (loop)

For each issue in the queue:

#### 2a. Assign and announce

```bash
gh issue edit {issue-number} --add-assignee "@me"
```

Print: `--- Starting TDB-xxx: {title} ---`

#### 2b. Read issue details

Read the full issue description from the phase issues file (the detailed section for this TDB-xxx). Also read all related tasks from the phase tasks file (tasks referencing this TDB-xxx).

#### 2c. Implement

Execute the tasks described in the issue. Follow the architecture in `specification/ARCHITECTURE.md` and the project conventions in `specification/MISSION.md`. Key rules:

- Create files in the locations specified by the architecture's Project File Structure
- Implement according to the issue description and acceptance criteria
- Follow existing code style and patterns from already-implemented modules
- Use frozen dataclasses for AST nodes and plan nodes
- Python 3.11+, stdlib only for core engine
- Write tests alongside implementation when the issue includes test tasks
- Keep modules under 300 lines

#### 2d. Validate

Run validation checks:

1. **Syntax check:** `python -m py_compile {changed_files}` for each new/modified .py file
2. **Import check:** `python -c "from toydb.{module} import *"` for each new module
3. **Tests:** `python -m pytest tests/ -x --tb=short` if tests exist
4. **Acceptance criteria:** go through each criterion from the issue and verify

Record pass/fail for each check.

#### 2e. Commit

```bash
git add {specific files created/modified}
git commit -m "$(cat <<'EOF'
TDB-xxx: {title}

{1-2 sentence summary of what was implemented}

Closes #{github-issue-number}

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

#### 2f. Push

```bash
git push
```

#### 2g. Close issue with summary

```bash
gh issue close {issue-number} --comment "$(cat <<'EOF'
## Implementation Summary

**Commit:** {commit-hash}
**Files changed:** {count}

### What was done
{bullet list of key changes}

### Validation
{pass/fail status for each check}

### Acceptance criteria
{checklist with pass/fail}
EOF
)"
```

#### 2h. Log progress

Append to the in-memory execution log:
- Issue ID, title
- Commit hash
- Files changed (list)
- Validation results
- Status: success/partial/failed

### Step 3: Handle failures

If implementation or validation fails for an issue:

1. Do NOT commit broken code
2. Stash or revert changes: `git checkout -- .`
3. Add a comment to the GitHub issue explaining what failed
4. Log the failure
5. Ask the user: continue to next issue (if no dependency), or stop?

### Step 3b: Version bump on phase completion

After ALL issues in the phase are completed successfully (none failed, none remaining):

1. Determine the target version:
   - Read current major version `x` from `pyproject.toml`
   - Target release: `{x}.{y}.0` (e.g., if x=0, phase 1 → `0.1.0`)

2. Update the version in `pyproject.toml`:

```toml
[project]
version = "{x}.{y}.0"
```

3. Update the version in `toydb/__init__.py`:

```python
__version__ = "{x}.{y}.0"
```

4. Update `RELEASE.md` — prepend a new version entry after the header. The entry should list all features implemented in this phase (one line per issue completed):

```markdown
## {x}.{y}.0 (YYYY-MM-DD)

Phase {y} — {phase milestone name}

- TDB-001: {title} — {1-sentence summary}
- TDB-002: {title} — {1-sentence summary}
...
```

5. Commit the version bump:

```bash
git add pyproject.toml toydb/__init__.py RELEASE.md
git commit -m "$(cat <<'EOF'
Release v{x}.{y}.0 — Phase {y} complete

All {count} issues implemented and validated.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

6. Tag the release:

```bash
git tag -a v{x}.{y}.0 -m "Phase {y}: {phase milestone name}"
```

7. Report to user: `Phase {y} complete → version bumped to {x}.{y}.0, tagged v{x}.{y}.0`

If some issues failed or were skipped, do NOT bump the version. Note in the execution report that the phase is incomplete.

### Step 4: Generate execution report

After all issues are processed (or on stop), generate:
`specification/implementation/phase-{y}-execution-report.md`

```markdown
# Phase {y} — Execution Report

**Date:** {date}
**Branch:** {branch name}
**Label:** {label}
**Target version:** {x}.{y}.0
**Executed by:** Claude Code

## Summary

| Status | Count |
|--------|-------|
| Completed | {n} |
| Failed | {n} |
| Skipped | {n} |
| Remaining | {n} |

## Issues

| # | TDB ID | Title | Status | Commit | Files | Tests |
|---|--------|-------|--------|--------|-------|-------|
| 1 | TDB-001 | Project scaffold and package structure | completed | a1b2c3d | 8 | 0/0 |
| 2 | TDB-002 | Error hierarchy | completed | e4f5g6h | 1 | 3/3 |
| ... | ... | ... | ... | ... | ... | ... |

## Detailed Results

### TDB-001: Project scaffold and package structure

**Status:** completed
**Commit:** a1b2c3d
**Files changed:**
- `toydb/__init__.py` (new)
- `toydb/__main__.py` (new)
- `pyproject.toml` (new)
- ...

**Validation:**
- [x] Syntax check: all files pass
- [x] Import check: all modules import
- [ ] Tests: N/A (no tests yet)
- [x] Acceptance criteria: 5/5 pass

---

### TDB-002: Error hierarchy
...

## Next Steps

{List of remaining issues not yet executed, with their dependencies}
```

Commit and push this report:

```bash
git add specification/implementation/phase-{y}-execution-report.md
git commit -m "$(cat <<'EOF'
Add phase {y} execution report

{n} issues completed, {n} failed, {n} remaining.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git push
```

## Important Rules

- **One issue at a time.** Never work on multiple issues simultaneously.
- **Dependency order.** Never start an issue whose dependencies are not closed.
- **Clean commits.** Each issue = one commit. No mixing work across issues.
- **No broken code.** Only commit code that passes validation.
- **Stdlib only.** Core engine has no third-party dependencies. Only `pytest` as dev dependency.
- **Frozen dataclasses.** All AST nodes and plan nodes must be frozen dataclasses.
- **Module size limit.** If a module exceeds 300 lines, split it.
- **Version bump on phase completion.** When all issues in a phase pass, bump to `{x}.{y}.0` and tag.
- **Ask on ambiguity.** If an issue description is unclear, ask the user rather than guessing.
- **Progress updates.** Print a short status line after each issue completes.
