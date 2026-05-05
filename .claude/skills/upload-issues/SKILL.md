---
name: upload-issues
description: Upload issues from a phase issues file to GitHub one by one with proper labels and dependencies.
---

# Skill: Upload Phase Issues to GitHub

Upload issues from a phase issues file to GitHub one by one, with proper labels (prefixed by version.phase) and dependencies.

## Usage

```
/upload-issues <phase-issues-file>
```

Example: `/upload-issues @specification/implementation/phase-1-issues.md`

## Instructions

### Step 1: Read the phase issues file

Read the provided phase issues file (e.g., `specification/implementation/phase-{N}-issues.md`).

Determine from the file path:
- **y** (phase): from `phase-{y}-issues.md` (e.g., `phase-1-issues.md` → y = `1`)

Determine the current major version **x** by reading `pyproject.toml` (the `version` field).

Compute:
- **Label prefix**: `{x}.{y}::` (e.g., `0.1::`)
- **Target release**: `{x}.{y}.0` (e.g., `0.1.0`)

Parse the **Issues Summary Table** to extract for each issue:
- `ID` (e.g., TDB-001)
- `Title`
- `Size` (S, M)
- `Stage` (e.g., "1 — Foundation")
- `Dependencies` (list of TDB-xxx IDs)

Then parse each **detailed issue section** (### heading with TDB-xxx) to extract:
- `Description`
- `What needs to be done` (full content)
- `Dependencies`
- `Expected result`
- `Acceptance criteria` (checklist)

### Step 2: Confirm with user

Show the user a summary of what will be created:
- Number of issues
- Label prefix (e.g., `0.1::`)
- Target release version (e.g., `0.1.0`)
- Full list of labels that will be created
- Ask for confirmation before proceeding

### Step 3: Create labels (if they don't exist)

All labels MUST be prefixed with `{x}.{y}::` (version.phase).

Label format: `{x}.{y}::{category}:{value}`

Use `gh` to create these labels if they don't already exist:

```bash
# Phase label
gh label create "0.1::phase:1" --color "0052CC" --description "v0.1.0 — Phase 1" 2>/dev/null || true

# Size labels
gh label create "0.1::size:S" --color "28A745" --description "Small (1-2 days)" 2>/dev/null || true
gh label create "0.1::size:M" --color "FFC107" --description "Medium (3-5 days)" 2>/dev/null || true

# Stage labels (extract from issues)
gh label create "0.1::stage:Foundation" --color "6F42C1" 2>/dev/null || true
gh label create "0.1::stage:Parser" --color "6F42C1" 2>/dev/null || true
# ... etc for each unique stage found in the issues
```

### Step 4: Create issues ONE BY ONE

**IMPORTANT:** Issues must be created one at a time, sequentially. After creating each issue:
1. Show the user the result (issue number, URL)
2. Proceed to the next issue immediately (do not wait for confirmation between issues)

For each issue (in order from the summary table):

1. Build the issue body in markdown:

```markdown
## Description
{description from the detailed section}

## What needs to be done
{full content from the detailed section}

## Dependencies
{dependency list, with references to already-created issue numbers}

## Expected result
{expected result from the detailed section}

## Acceptance criteria
{checklist from the detailed section}

---
**ID:** {TDB-xxx}
**Size:** {S/M}
**Phase:** {y}
**Version:** {x}.{y}.0
**Stage:** {stage name}
```

2. Create the issue with a single `gh issue create` command (one issue per command, never batch):

```bash
gh issue create \
  --title "TDB-xxx: {title}" \
  --label "{x}.{y}::phase:{y},{x}.{y}::size:{S/M},{x}.{y}::stage:{stage-name}" \
  --body "$(cat <<'BODY'
{issue body}
BODY
)"
```

3. Record the mapping: TDB-xxx -> GitHub issue #number

4. Report to user: `Created TDB-xxx → #{number}: {title}`

5. If the issue has dependencies on already-created issues, add a comment:

```bash
gh issue comment {issue-number} --body "Blocked by #{dep-issue-number} (TDB-xxx)"
```

6. Move to the next issue.

### Step 5: Generate report

After all issues are created, generate a report file at:
`specification/implementation/phase-{N}-github-report.md`

Content:

```markdown
# Phase {y} — GitHub Issues Report

**Uploaded:** {date}
**Repository:** {github repo URL}
**Target version:** {x}.{y}.0
**Total issues:** {count}

## Issue Mapping

| TDB ID | GitHub # | Title | Labels | URL |
|--------|----------|-------|--------|-----|
| TDB-001 | #1 | Project scaffold and package structure | 0.1::phase:1, 0.1::size:S, 0.1::stage:Foundation | {url} |
| ... | ... | ... | ... | ... |

## Labels Created

- {x}.{y}::phase:{y}
- {x}.{y}::size:S, {x}.{y}::size:M
- {x}.{y}::stage:{list}
```

### Step 6: Report to user

Show the user:
- Total issues created
- Link to the GitHub issues board
- Path to the generated report file

## Versioning Reference

Version format: `x.y.z` where:
- `x` — major version, changed manually by the user
- `y` — phase number (1–9)
- `z` — fix/patch within a phase

Read the current major version `x` from `pyproject.toml` before creating issues. Target release for a phase is `{x}.{y}.0`.

All labels are prefixed with `{x}.{y}::` so that issues from different versions/phases are clearly separated.

## Error Handling

- If `gh` is not authenticated, tell the user to run `gh auth login`
- If an issue already exists with the same title, skip it and note in the report
- If label creation fails, continue (labels may already exist)
- On any failure, report what was created so far and what remains
