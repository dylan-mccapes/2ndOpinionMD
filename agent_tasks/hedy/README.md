# Hedy Task Directory

This directory is for inter-agent coordination between Hedy (OpenAI agent) and Devin.

## 🔐 Automation Policies

This agent uses automation policies from the `agent_tasks/policies/` directory to determine whether to proceed autonomously or request human review.

- Active Policy: [`cleanup_automation_policy.json`](../policies/cleanup_automation_policy.json)
- Applies to: Legacy stack removal, import cleanup, and dead code deletion
- Enforced by: `hedy_policy_enforcer.py`

When confidence > 0.7 and the rules are satisfied, Hedy will proceed autonomously. Otherwise, the task will pause and request manual approval.

## Usage
- Hedy posts JSON task files here for Devin to execute
- Task files should follow the format: `task_YYYYMMDD_HHMMSS.json`
- Include structured TODOs and execution requirements

## Task Format
```json
{
  "task_id": "unique_identifier",
  "timestamp": "2025-08-04T01:23:14Z",
  "priority": "high|medium|low",
  "type": "fix_imports|build_test|refactor|documentation",
  "description": "Brief description of the task",
  "requirements": [
    "Specific requirement 1",
    "Specific requirement 2"
  ],
  "files_affected": [
    "path/to/file1.py",
    "path/to/file2.js"
  ],
  "verification_steps": [
    "How to verify completion"
  ]
}
```

## Current Status
- Repository: 2ndOpinionMD-MVP
- Branch: devin/1754256524-repo-cleanup-modular-structure
- PR: #117 (Modular Architecture Restructuring)
- Critical Issues: Broken imports after modular restructuring, React build failure
