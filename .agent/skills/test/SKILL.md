---
name: test-manager
description: Use this skill when running tests (pytest, ctest, etc.) to handle long outputs and prevent context overflow.
---

# Test Manager Skill

## Goal

Execute project tests and handle large outputs autonomously without bothering the user.

## Instructions

1. **Detect Output Size:** If you expect a test run to produce more than 50 lines of output (e.g., a full Django test suite or C++ build), do NOT stream it to the chat.
2. **Autonomous Redirection:** Automatically redirect the output to a temporary file:
   - Command: `testCommand --noinput > test_output.txt 2>&1` (testCommand is the command to run the tests)
3. **Analyze & Report:** - After the command finishes, read only the last 20 lines of the file to see the summary.
   - If there are failures, search the file for "FAIL" or "ERROR" and only report the specific failing cases to the user.
4. **Clean up:** Delete the temporary file once the analysis is complete.

## Constraints

- Do not ask for permission to save test results to a file; it is the standard protocol for this workspace.
