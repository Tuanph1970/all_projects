#!/usr/bin/env python3
"""
Post-Migration Checklist Tool

Interactive checklist tool for completing all post-migration tasks
after Django decommissioning.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    CRITICAL = "critical"  # Must be done immediately
    HIGH = "high"         # Should be done within 24 hours
    MEDIUM = "medium"     # Should be done within 1 week
    LOW = "low"           # Nice to have


@dataclass
class ChecklistTask:
    """Individual checklist task"""
    id: str
    title: str
    description: str
    category: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    owner: str = ""
    notes: str = ""
    completed_at: Optional[datetime] = None
    depends_on: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority.value,
            "status": self.status.value,
            "owner": self.owner,
            "notes": self.notes,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "depends_on": self.depends_on,
        }


# Define all post-migration tasks
POST_MIGRATION_TASKS = [
    # Infrastructure Tasks
    ChecklistTask(
        id="infra-001",
        title="Remove Django from CI/CD pipelines",
        description="Update CI/CD configurations to remove Django build and deploy steps",
        category="Infrastructure",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="infra-002",
        title="Update DNS records",
        description="Remove any Django-specific DNS records or update A/CNAME records",
        category="Infrastructure",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="infra-003",
        title="Remove Django SSL certificates",
        description="Remove/archive SSL certificates that were Django-specific",
        category="Infrastructure",
        priority=TaskPriority.MEDIUM,
    ),
    ChecklistTask(
        id="infra-004",
        title="Clean up load balancer rules",
        description="Remove Django backend pools and health checks from load balancer",
        category="Infrastructure",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="infra-005",
        title="Archive Django infrastructure code",
        description="Archive Terraform/CloudFormation code for Django infrastructure",
        category="Infrastructure",
        priority=TaskPriority.LOW,
    ),

    # Documentation Tasks
    ChecklistTask(
        id="docs-001",
        title="Update architecture documentation",
        description="Update system architecture diagrams to reflect microservices-only architecture",
        category="Documentation",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="docs-002",
        title="Update API documentation",
        description="Ensure all API docs reference v2 endpoints only",
        category="Documentation",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="docs-003",
        title="Create migration retrospective",
        description="Document lessons learned from the migration process",
        category="Documentation",
        priority=TaskPriority.MEDIUM,
    ),
    ChecklistTask(
        id="docs-004",
        title="Update runbooks",
        description="Update operational runbooks to remove Django-specific procedures",
        category="Documentation",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="docs-005",
        title="Update onboarding docs",
        description="Update developer onboarding documentation",
        category="Documentation",
        priority=TaskPriority.MEDIUM,
    ),

    # Communication Tasks
    ChecklistTask(
        id="comm-001",
        title="Notify stakeholders",
        description="Send completion notification to all stakeholders",
        category="Communication",
        priority=TaskPriority.CRITICAL,
    ),
    ChecklistTask(
        id="comm-002",
        title="Update status page",
        description="Update public status page to reflect new architecture",
        category="Communication",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="comm-003",
        title="Notify API consumers",
        description="Send deprecation notice for any remaining v1 endpoints",
        category="Communication",
        priority=TaskPriority.HIGH,
    ),

    # Security Tasks
    ChecklistTask(
        id="sec-001",
        title="Rotate Django secrets",
        description="Rotate/invalidate any secrets that were used by Django",
        category="Security",
        priority=TaskPriority.CRITICAL,
    ),
    ChecklistTask(
        id="sec-002",
        title="Update IAM policies",
        description="Remove Django service account permissions",
        category="Security",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="sec-003",
        title="Security scan",
        description="Run security scan to ensure no Django artifacts remain",
        category="Security",
        priority=TaskPriority.MEDIUM,
    ),

    # Monitoring Tasks
    ChecklistTask(
        id="mon-001",
        title="Update monitoring dashboards",
        description="Remove Django panels from Grafana dashboards",
        category="Monitoring",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="mon-002",
        title="Update alerting rules",
        description="Remove Django-specific alerting rules from Prometheus",
        category="Monitoring",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="mon-003",
        title="Archive historical metrics",
        description="Export and archive Django historical metrics",
        category="Monitoring",
        priority=TaskPriority.LOW,
    ),

    # Database Tasks
    ChecklistTask(
        id="db-001",
        title="Schedule database archival",
        description="Schedule archival/deletion of Django database (after retention period)",
        category="Database",
        priority=TaskPriority.MEDIUM,
    ),
    ChecklistTask(
        id="db-002",
        title="Remove database users",
        description="Remove Django-specific database users and permissions",
        category="Database",
        priority=TaskPriority.HIGH,
    ),

    # Training Tasks
    ChecklistTask(
        id="train-001",
        title="Train support team",
        description="Complete training for support team on new architecture",
        category="Training",
        priority=TaskPriority.HIGH,
    ),
    ChecklistTask(
        id="train-002",
        title="Update troubleshooting guides",
        description="Create/update troubleshooting guides for microservices",
        category="Training",
        priority=TaskPriority.MEDIUM,
    ),

    # Cleanup Tasks
    ChecklistTask(
        id="clean-001",
        title="Remove Django code repository",
        description="Archive and remove Django repository from active repos",
        category="Cleanup",
        priority=TaskPriority.LOW,
    ),
    ChecklistTask(
        id="clean-002",
        title="Clean up artifact registry",
        description="Remove Django Docker images from container registry",
        category="Cleanup",
        priority=TaskPriority.LOW,
    ),
    ChecklistTask(
        id="clean-003",
        title="Remove legacy environment variables",
        description="Clean up environment variables and config maps",
        category="Cleanup",
        priority=TaskPriority.MEDIUM,
    ),
]


class PostMigrationChecklist:
    """Manages the post-migration checklist"""

    def __init__(self, state_file: str = ".post_migration_state.json"):
        self.state_file = state_file
        self.tasks: Dict[str, ChecklistTask] = {}
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        self._load_state()

    def _load_state(self):
        """Load state from file or initialize with defaults"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)

            self.started_at = datetime.fromisoformat(state["started_at"]) if state.get("started_at") else None
            self.completed_at = datetime.fromisoformat(state["completed_at"]) if state.get("completed_at") else None

            for task_data in state.get("tasks", []):
                task = ChecklistTask(
                    id=task_data["id"],
                    title=task_data["title"],
                    description=task_data["description"],
                    category=task_data["category"],
                    priority=TaskPriority(task_data["priority"]),
                    status=TaskStatus(task_data["status"]),
                    owner=task_data.get("owner", ""),
                    notes=task_data.get("notes", ""),
                    completed_at=datetime.fromisoformat(task_data["completed_at"]) if task_data.get("completed_at") else None,
                    depends_on=task_data.get("depends_on", []),
                )
                self.tasks[task.id] = task
        else:
            # Initialize with default tasks
            self.started_at = datetime.now()
            for task in POST_MIGRATION_TASKS:
                self.tasks[task.id] = task
            self._save_state()

    def _save_state(self):
        """Save current state to file"""
        state = {
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tasks": [task.to_dict() for task in self.tasks.values()],
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def get_progress(self) -> Dict:
        """Get overall progress"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        skipped = sum(1 for t in self.tasks.values() if t.status == TaskStatus.SKIPPED)
        in_progress = sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS)
        blocked = sum(1 for t in self.tasks.values() if t.status == TaskStatus.BLOCKED)
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)

        return {
            "total": total,
            "completed": completed,
            "skipped": skipped,
            "in_progress": in_progress,
            "blocked": blocked,
            "pending": pending,
            "percentage": (completed + skipped) / total * 100 if total > 0 else 0,
        }

    def update_task(self, task_id: str, status: TaskStatus, owner: str = "", notes: str = ""):
        """Update a task's status"""
        if task_id not in self.tasks:
            print(f"Task not found: {task_id}")
            return

        task = self.tasks[task_id]
        task.status = status
        if owner:
            task.owner = owner
        if notes:
            task.notes = notes

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()

        # Check if all tasks are complete
        progress = self.get_progress()
        if progress["completed"] + progress["skipped"] == progress["total"]:
            self.completed_at = datetime.now()

        self._save_state()

    def print_checklist(self, filter_status: Optional[TaskStatus] = None, filter_category: Optional[str] = None):
        """Print the checklist"""
        progress = self.get_progress()

        print("\n" + "=" * 70)
        print("  POST-MIGRATION CHECKLIST")
        print("=" * 70)
        print(f"\n  Started: {self.started_at.strftime('%Y-%m-%d %H:%M') if self.started_at else 'Not started'}")
        print(f"  Progress: {progress['completed']}/{progress['total']} completed ({progress['percentage']:.1f}%)")

        # Progress bar
        bar_width = 40
        filled = int(bar_width * progress['percentage'] / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"  [{bar}]")

        print(f"\n  Status: ✅ {progress['completed']} | 🔄 {progress['in_progress']} | ⏳ {progress['pending']} | ⏭️  {progress['skipped']} | 🚫 {progress['blocked']}")

        # Group by category
        categories = {}
        for task in self.tasks.values():
            if filter_status and task.status != filter_status:
                continue
            if filter_category and task.category != filter_category:
                continue

            if task.category not in categories:
                categories[task.category] = []
            categories[task.category].append(task)

        for category, tasks in sorted(categories.items()):
            print(f"\n  {category}")
            print("  " + "-" * 50)

            for task in sorted(tasks, key=lambda t: t.priority.value):
                status_icon = {
                    TaskStatus.COMPLETED: "✅",
                    TaskStatus.IN_PROGRESS: "🔄",
                    TaskStatus.PENDING: "⏳",
                    TaskStatus.SKIPPED: "⏭️ ",
                    TaskStatus.BLOCKED: "🚫",
                }[task.status]

                priority_icon = {
                    TaskPriority.CRITICAL: "🔴",
                    TaskPriority.HIGH: "🟠",
                    TaskPriority.MEDIUM: "🟡",
                    TaskPriority.LOW: "🟢",
                }[task.priority]

                print(f"  {status_icon} [{task.id}] {priority_icon} {task.title}")
                if task.owner:
                    print(f"       Owner: {task.owner}")

        print("\n" + "=" * 70)

    def interactive_mode(self):
        """Run interactive checklist mode"""
        while True:
            self.print_checklist()

            print("\nCommands:")
            print("  c <id>        - Mark task as completed")
            print("  s <id>        - Mark task as skipped")
            print("  p <id>        - Mark task as in progress")
            print("  b <id>        - Mark task as blocked")
            print("  o <id> <name> - Assign owner to task")
            print("  n <id> <note> - Add note to task")
            print("  f <category>  - Filter by category")
            print("  r             - Generate report")
            print("  q             - Quit")

            try:
                cmd = input("\nEnter command: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not cmd:
                continue

            parts = cmd.split(maxsplit=2)
            action = parts[0].lower()

            if action == 'q':
                break
            elif action == 'c' and len(parts) >= 2:
                self.update_task(parts[1], TaskStatus.COMPLETED)
                print(f"✅ Task {parts[1]} marked as completed")
            elif action == 's' and len(parts) >= 2:
                self.update_task(parts[1], TaskStatus.SKIPPED)
                print(f"⏭️  Task {parts[1]} marked as skipped")
            elif action == 'p' and len(parts) >= 2:
                self.update_task(parts[1], TaskStatus.IN_PROGRESS)
                print(f"🔄 Task {parts[1]} marked as in progress")
            elif action == 'b' and len(parts) >= 2:
                self.update_task(parts[1], TaskStatus.BLOCKED)
                print(f"🚫 Task {parts[1]} marked as blocked")
            elif action == 'o' and len(parts) >= 3:
                self.update_task(parts[1], self.tasks[parts[1]].status, owner=parts[2])
                print(f"👤 Task {parts[1]} assigned to {parts[2]}")
            elif action == 'n' and len(parts) >= 3:
                self.update_task(parts[1], self.tasks[parts[1]].status, notes=parts[2])
                print(f"📝 Note added to task {parts[1]}")
            elif action == 'r':
                self.generate_report()
            else:
                print("Invalid command")

    def generate_report(self):
        """Generate completion report"""
        progress = self.get_progress()

        report = f"""
# Post-Migration Completion Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Started:** {self.started_at.strftime('%Y-%m-%d %H:%M:%S') if self.started_at else 'N/A'}
**Completed:** {self.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.completed_at else 'In Progress'}

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | {progress['total']} |
| Completed | {progress['completed']} |
| Skipped | {progress['skipped']} |
| In Progress | {progress['in_progress']} |
| Blocked | {progress['blocked']} |
| Pending | {progress['pending']} |
| Completion | {progress['percentage']:.1f}% |

## Task Details

"""
        for task in sorted(self.tasks.values(), key=lambda t: (t.category, t.priority.value)):
            status = "✅" if task.status == TaskStatus.COMPLETED else "❌"
            report += f"- [{status}] **{task.title}** ({task.category})\n"
            if task.owner:
                report += f"  - Owner: {task.owner}\n"
            if task.notes:
                report += f"  - Notes: {task.notes}\n"
            if task.completed_at:
                report += f"  - Completed: {task.completed_at.strftime('%Y-%m-%d %H:%M')}\n"

        report_file = f"post_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"\n📄 Report saved to: {report_file}")
        return report_file


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Post-Migration Checklist Tool")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--report", "-r", action="store_true", help="Generate completion report")
    parser.add_argument("--status", "-s", help="Filter by status (pending, completed, etc.)")
    parser.add_argument("--complete", "-c", help="Mark task as completed")
    parser.add_argument("--reset", action="store_true", help="Reset checklist to initial state")

    args = parser.parse_args()

    if args.reset:
        if os.path.exists(".post_migration_state.json"):
            os.remove(".post_migration_state.json")
            print("Checklist reset to initial state")
        return

    checklist = PostMigrationChecklist()

    if args.complete:
        checklist.update_task(args.complete, TaskStatus.COMPLETED)
        print(f"✅ Task {args.complete} marked as completed")

    if args.report:
        checklist.generate_report()
    elif args.interactive:
        checklist.interactive_mode()
    else:
        filter_status = TaskStatus(args.status) if args.status else None
        checklist.print_checklist(filter_status=filter_status)


if __name__ == "__main__":
    main()
