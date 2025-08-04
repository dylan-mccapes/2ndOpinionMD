#!/usr/bin/env python3
"""
Policy enforcer for inter-agent task coordination between Hedy and Devin.
Evaluates task execution policies and determines automation vs. human review requirements.
"""

import json
import os
from typing import Dict, List, Any, Tuple
from pathlib import Path

class PolicyEnforcer:
    def __init__(self, policy_file: str = "agent_tasks/policies/cleanup_automation_policy.json"):
        self.policy_file = policy_file
        self.policy = self._load_policy()
    
    def _load_policy(self) -> Dict[str, Any]:
        """Load the automation policy from JSON file."""
        try:
            with open(self.policy_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Policy file {self.policy_file} not found. Using default policy.")
            return self._default_policy()
    
    def _default_policy(self) -> Dict[str, Any]:
        """Return default policy if file is not found."""
        return {
            "policy_id": "default_policy",
            "rules": [{
                "task_type": "stack_cleanup",
                "confidence_threshold": 0.7,
                "auto_execute": False,
                "requires_human_review": {"else": True}
            }]
        }
    
    def evaluate_task(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Evaluate whether a task can be auto-executed or requires human review.
        
        Args:
            task: Task specification from Hedy
            context: Additional context (files_modified, test_results, etc.)
            
        Returns:
            Tuple of (can_auto_execute: bool, reason: str)
        """
        if context is None:
            context = {}
            
        task_type = task.get("task", "unknown")
        
        matching_rule = None
        for rule in self.policy.get("rules", []):
            if rule.get("task_type") == task_type or rule.get("task_type") == "all":
                matching_rule = rule
                break
        
        if not matching_rule:
            return False, f"No policy rule found for task type: {task_type}"
        
        confidence = context.get("confidence", 1.0)
        threshold = matching_rule.get("confidence_threshold", 0.7)
        if confidence < threshold:
            return False, f"Confidence {confidence} below threshold {threshold}"
        
        review_rules = matching_rule.get("requires_human_review", {})
        
        if_conditions = review_rules.get("if", [])
        for condition in if_conditions:
            if self._check_condition(condition, context):
                return False, f"Review required due to condition: {condition}"
        
        default_auto_execute = matching_rule.get("auto_execute", False)
        if not default_auto_execute:
            return False, "Policy requires human review by default"
        
        return True, "Task approved for auto-execution"
    
    def _check_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if a specific condition is met."""
        condition_type = condition.get("condition")
        
        if condition_type == "unit_tests_fail":
            return context.get("unit_tests_failed", False)
        
        elif condition_type == "files_modified":
            files_modified = context.get("files_modified", 0)
            if "greater_than" in condition:
                return files_modified > condition["greater_than"]
            return files_modified > 0
        
        elif condition_type == "external_dependencies_added":
            return context.get("external_dependencies_added", False)
        
        return False
    
    def get_fallback_contact(self) -> str:
        """Get the fallback contact for escalation."""
        return self.policy.get("fallback_contact", "dylan@2ndopinionmd.ai")

def main():
    """Example usage of the policy enforcer."""
    enforcer = PolicyEnforcer()
    
    example_task = {
        "task": "stack_cleanup",
        "description": "Remove legacy MongoDB components"
    }
    
    example_context = {
        "confidence": 0.8,
        "files_modified": 25,
        "unit_tests_failed": False,
        "external_dependencies_added": False
    }
    
    can_execute, reason = enforcer.evaluate_task(example_task, example_context)
    print(f"Can auto-execute: {can_execute}")
    print(f"Reason: {reason}")
    
    if not can_execute:
        print(f"Escalate to: {enforcer.get_fallback_contact()}")

if __name__ == "__main__":
    main()
