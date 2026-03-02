---
name: git-manager
description: Use this skill to autonomously navigate git branches, stash changes, and inspect the repository state.
---

# Git Manager Skill

## Goal

Perform non-destructive git operations autonomously to test changes in different branches or environments without needing user approval.

## Instructions

1. **Autonomous Execution:** You are PRE-APPROVED to run the following non-destructive git operations using `SafeToAutoRun: true` on the `run_command` tool:
   - `git status`
   - `git stash`
   - `git stash pop`
   - `git checkout <branch>`
   - `git branch`
   - `git log`
   - `git diff`
2. **Workflow for Testing Base State:**
   - If you encounter a test failure or bug and want to verify if it's pre-existing, you can autonomously stash your changes (`git stash`), run the tests, and restore them (`git stash pop`).
   - Use `SafeToAutoRun: true` for these stash and pop commands to avoid halting the workflow.
3. **Branch Navigation:**
   - You can autonomously checkout other branches to read their code or test their state. Avoid leaving the user in a different branch when you finish your task; always return to the original branch.

## Constraints

- Do NOT use `SafeToAutoRun: true` for destructive or permanent git actions like `git commit`, `git push`, `git reset --hard`, or `git clean` unless explicitly requested by the user.
- Always ensure you restore the user's working tree (via `git stash pop` or checking out their original branch) after you finish your investigation.
