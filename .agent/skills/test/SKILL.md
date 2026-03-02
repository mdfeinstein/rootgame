---
name: test-manager
description: Use this skill when running tests (pytest, ctest, etc.) to handle long outputs and prevent context overflow.
---

# Test Manager Skill

## Goal

Execute project tests and handle large outputs autonomously without bothering the user.

## Instructions

1. **Autonomous Execution:** You are PRE-APPROVED and EXPECTED to run test commands with `SafeToAutoRun: true`. Do not wait for user approval to run tests. Even the writing to the log file is PRE-APPROVED, as is its deletion when you are done.
2. **Detect Output Size:** If you expect a test run to produce more than 50 lines of output (e.g., a full Django test suite or C++ build), do NOT stream it to the chat.
3. **Autonomous Redirection:** Use the dedicated test wrapper script to automatically redirect output to `test_output.txt`:
   - Command: `F:\python\envs\.venv_web\scripts\python.exe .agent\scripts\run_tests.py [test_path]` (e.g., `game.tests.transactions.birds`)
   - Ensure `SafeToAutoRun` is set to `true`.
4. **Analyze & Report:**
   - After the command finishes, use tools like `view_file` or `grep_search` to read the file.
   - If there are failures, search the file for "FAIL" or "ERROR" and specifically analyze those traces.
5. **Clean up:** Delete the temporary file using `SafeToAutoRun: true` (e.g. `rm test_output.txt`) once the analysis is complete.

## Constraints

- Do not ask for permission to save test results to a file or delete it; it is the standard protocol for this workspace.
- Do not ask for permission to run the test suite; use `SafeToAutoRun: true`.
