---
name: automated-pr-reviewer
description: Performs a deep audit. Use when user says "review code".
allowed-tools: [git_status_summary, git_diff_staged, search_codebase_grep]
---
# PR Review Protocol

## Phase 1: Context (Mandatory)
- Use `git_status_summary` to verify you are on the correct branch.
- If no changes are detected, ABORT and inform the user.

## Phase 2: Security
- Grep for 'API_KEY' or 'SECRET' using `search_codebase_grep`.
- **Constraint:** If a secret is found, do NOT output it in cleartext; only report the line number.

## Error Handling
- If a tool returns a "Permission Denied" error, request the user for escalated shell access before retrying.
