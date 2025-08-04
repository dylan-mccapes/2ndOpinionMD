import json
import os

POLICY_PATH = "agent_tasks/policies/cleanup_automation_policy.json"

def load_policy(path=POLICY_PATH):
    with open(path, "r") as f:
        return json.load(f)

def should_auto_execute(task_type, confidence, changes, tests_passed):
    policy = load_policy()
    rules = next((r for r in policy["rules"] if r["task_type"] == task_type), None)
    if not rules:
        return False

    if confidence < rules["confidence_threshold"]:
        return False

    for condition in rules["requires_human_review"]["if"]:
        if condition["condition"] == "unit_tests_fail" and not tests_passed:
            return False
        if condition["condition"] == "files_modified" and changes["files_modified"] > condition["greater_than"]:
            return False
        if condition["condition"] == "external_dependencies_added" and changes.get("external_dependencies_added", False):
            return False

    return True
