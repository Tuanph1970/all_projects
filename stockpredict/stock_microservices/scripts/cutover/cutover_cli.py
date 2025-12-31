#!/usr/bin/env python3
"""
Traffic Cutover CLI Tool

This tool manages the gradual traffic cutover from Django to microservices.
It integrates with the feature flags service and can update Traefik configurations.

Usage:
    python cutover_cli.py status              # Show current status
    python cutover_cli.py phase canary        # Apply canary phase (10%)
    python cutover_cli.py phase half          # Apply 50/50 phase
    python cutover_cli.py phase complete      # Apply 100% cutover
    python cutover_cli.py rollback            # Emergency rollback
    python cutover_cli.py --help              # Show help
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

import httpx
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CutoverConfig:
    """Cutover configuration"""
    feature_flags_url: str = os.getenv("FEATURE_FLAGS_URL", "http://localhost:8010")
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "change-me-in-production")
    traefik_config_path: str = os.getenv(
        "TRAEFIK_CONFIG_PATH",
        os.path.join(os.path.dirname(__file__), "../../traefik/dynamic-weighted.yml")
    )
    dry_run: bool = False


# Cutover phases with descriptions
PHASES = {
    "shadow": {
        "name": "Shadow Mode",
        "description": "Django 100% | Microservices 0% (Shadow only)",
        "week": 1,
        "risk": "low"
    },
    "canary": {
        "name": "Canary Release",
        "description": "Django 90% | Microservices 10%",
        "week": 2,
        "risk": "low"
    },
    "early_adopter": {
        "name": "Early Adopter",
        "description": "Django 70% | Microservices 30%",
        "week": 3,
        "risk": "medium"
    },
    "half": {
        "name": "50/50 Split",
        "description": "Django 50% | Microservices 50%",
        "week": 4,
        "risk": "medium"
    },
    "majority": {
        "name": "Majority Migrated",
        "description": "Django 20% | Microservices 80%",
        "week": 5,
        "risk": "medium"
    },
    "final_validation": {
        "name": "Final Validation",
        "description": "Django 5% | Microservices 95%",
        "week": 6,
        "risk": "high"
    },
    "complete": {
        "name": "Complete Cutover",
        "description": "Django 0% | Microservices 100%",
        "week": 7,
        "risk": "high"
    },
    "rollback": {
        "name": "Emergency Rollback",
        "description": "Django 100% | Microservices 0%",
        "week": 0,
        "risk": "emergency"
    }
}


class CutoverManager:
    """Manages traffic cutover operations"""

    def __init__(self, config: CutoverConfig):
        self.config = config
        self.client = httpx.Client(
            base_url=config.feature_flags_url,
            headers={"X-API-Key": config.admin_api_key},
            timeout=30.0
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current cutover status"""
        try:
            response = self.client.get("/api/flags/status")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": str(e)}

    def get_all_flags(self) -> Dict[str, Any]:
        """Get all feature flags"""
        try:
            response = self.client.get("/api/flags/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get flags: {e}")
            return {"error": str(e)}

    def apply_phase(
        self,
        phase_name: str,
        reason: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Apply a cutover phase"""
        if phase_name not in PHASES:
            return {"error": f"Unknown phase: {phase_name}"}

        phase_info = PHASES[phase_name]

        if not dry_run:
            # Confirm high-risk phases
            if phase_info["risk"] in ["high", "emergency"]:
                print(f"\n⚠️  WARNING: This is a {phase_info['risk'].upper()} risk operation!")
                print(f"   Phase: {phase_info['name']}")
                print(f"   Description: {phase_info['description']}")
                confirm = input("\nType 'yes' to confirm: ")
                if confirm.lower() != 'yes':
                    return {"cancelled": True, "message": "Operation cancelled by user"}

        try:
            response = self.client.post(
                "/api/admin/apply-phase",
                json={
                    "phase": phase_name,
                    "reason": reason or f"Applied via CLI at {datetime.utcnow().isoformat()}",
                    "dry_run": dry_run
                }
            )
            response.raise_for_status()
            result = response.json()

            if not dry_run:
                # Also update Traefik config
                self._update_traefik_config(phase_name)

            return result
        except httpx.HTTPError as e:
            logger.error(f"Failed to apply phase: {e}")
            return {"error": str(e)}

    def rollback(self, reason: Optional[str] = None) -> Dict[str, Any]:
        """Emergency rollback to Django"""
        return self.apply_phase("rollback", reason=reason or "Emergency rollback")

    def _update_traefik_config(self, phase_name: str) -> bool:
        """Update Traefik configuration for the phase"""
        try:
            config_path = self.config.traefik_config_path

            if not os.path.exists(config_path):
                logger.warning(f"Traefik config not found: {config_path}")
                return False

            # Load current config
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Get phase percentages
            phase = PHASES.get(phase_name, {})
            percentages = self._get_phase_percentages(phase_name)

            if not percentages:
                return False

            # Update service weights
            services = config.get('http', {}).get('services', {})

            for service_name, service_config in services.items():
                if 'weighted' in service_config:
                    weighted = service_config['weighted']
                    for svc in weighted.get('services', []):
                        name = svc.get('name', '')
                        if 'microservice' in name:
                            # Find matching flag
                            flag_name = self._service_to_flag(name)
                            svc['weight'] = percentages.get(flag_name, 0)
                        elif 'django' in name:
                            flag_name = self._service_to_flag(name.replace('django-', ''))
                            svc['weight'] = 100 - percentages.get(flag_name, 0)

            # Backup and write new config
            backup_path = f"{config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)

            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)

            logger.info(f"Updated Traefik config for phase: {phase_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update Traefik config: {e}")
            return False

    def _get_phase_percentages(self, phase_name: str) -> Dict[str, int]:
        """Get percentage configuration for a phase"""
        # This should match the CUTOVER_PHASES in feature-flags config
        phases = {
            "shadow": {
                "auth_microservice": 0,
                "stock_data_microservice": 0,
                "portfolio_microservice": 0,
                "prediction_microservice": 0,
                "analysis_microservice": 0,
                "ai_insights_microservice": 0,
                "chatbot_microservice": 0,
            },
            "canary": {
                "auth_microservice": 10,
                "stock_data_microservice": 10,
                "portfolio_microservice": 10,
                "prediction_microservice": 5,
                "analysis_microservice": 5,
                "ai_insights_microservice": 5,
                "chatbot_microservice": 5,
            },
            "half": {
                "auth_microservice": 50,
                "stock_data_microservice": 50,
                "portfolio_microservice": 50,
                "prediction_microservice": 30,
                "analysis_microservice": 30,
                "ai_insights_microservice": 30,
                "chatbot_microservice": 30,
            },
            "complete": {
                "auth_microservice": 100,
                "stock_data_microservice": 100,
                "portfolio_microservice": 100,
                "prediction_microservice": 100,
                "analysis_microservice": 100,
                "ai_insights_microservice": 100,
                "chatbot_microservice": 100,
            },
            "rollback": {
                "auth_microservice": 0,
                "stock_data_microservice": 0,
                "portfolio_microservice": 0,
                "prediction_microservice": 0,
                "analysis_microservice": 0,
                "ai_insights_microservice": 0,
                "chatbot_microservice": 0,
            },
        }
        return phases.get(phase_name, {})

    def _service_to_flag(self, service_name: str) -> str:
        """Convert service name to flag name"""
        mapping = {
            "auth-microservice": "auth_microservice",
            "stock-data-microservice": "stock_data_microservice",
            "portfolio-microservice": "portfolio_microservice",
            "prediction-microservice": "prediction_microservice",
            "analysis-microservice": "analysis_microservice",
            "ai-insights-microservice": "ai_insights_microservice",
            "chatbot-microservice": "chatbot_microservice",
        }
        return mapping.get(service_name, service_name.replace("-", "_"))

    def close(self):
        """Close HTTP client"""
        self.client.close()


def print_status(status: Dict[str, Any]):
    """Print status in a formatted way"""
    print("\n" + "=" * 60)
    print("  CUTOVER STATUS")
    print("=" * 60)

    if "error" in status:
        print(f"\n  ❌ Error: {status['error']}")
        return

    current_phase = status.get("current_phase", "unknown")
    phase_info = PHASES.get(current_phase, {})

    print(f"\n  Current Phase: {phase_info.get('name', current_phase)}")
    print(f"  Description:   {phase_info.get('description', 'N/A')}")
    print(f"  Risk Level:    {phase_info.get('risk', 'unknown').upper()}")

    print("\n  Service Traffic Distribution:")
    print("  " + "-" * 50)

    flags = status.get("flags", {})
    for flag_name, flag_data in flags.items():
        percentage = flag_data.get("percentage", 0)
        enabled = flag_data.get("enabled", False)
        service = flag_data.get("service", "unknown")

        status_icon = "✅" if enabled else "❌"
        bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)

        print(f"  {status_icon} {service:25} [{bar}] {percentage:3}%")

    print("\n" + "=" * 60)


def print_phases():
    """Print available phases"""
    print("\n" + "=" * 60)
    print("  AVAILABLE PHASES")
    print("=" * 60)

    for phase_name, info in PHASES.items():
        risk_color = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴",
            "emergency": "🚨"
        }.get(info["risk"], "⚪")

        print(f"\n  {risk_color} {phase_name}")
        print(f"     Name: {info['name']}")
        print(f"     Week: {info['week']}")
        print(f"     Description: {info['description']}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Traffic Cutover CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s status                    # Show current status
    %(prog)s phase canary              # Apply canary phase
    %(prog)s phase half --dry-run      # Preview 50/50 phase
    %(prog)s rollback --reason "High error rate"
    %(prog)s phases                    # List all phases
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Status command
    subparsers.add_parser("status", help="Show current cutover status")

    # Phases command
    subparsers.add_parser("phases", help="List available phases")

    # Phase command
    phase_parser = subparsers.add_parser("phase", help="Apply a cutover phase")
    phase_parser.add_argument("name", choices=list(PHASES.keys()), help="Phase name")
    phase_parser.add_argument("--reason", help="Reason for change")
    phase_parser.add_argument("--dry-run", action="store_true", help="Preview without applying")

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Emergency rollback")
    rollback_parser.add_argument("--reason", help="Reason for rollback")

    # Flags command
    subparsers.add_parser("flags", help="Show all feature flags")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    config = CutoverConfig()
    manager = CutoverManager(config)

    try:
        if args.command == "status":
            status = manager.get_status()
            print_status(status)

        elif args.command == "phases":
            print_phases()

        elif args.command == "phase":
            print(f"\nApplying phase: {args.name}")
            result = manager.apply_phase(
                args.name,
                reason=args.reason,
                dry_run=args.dry_run
            )
            print(json.dumps(result, indent=2))

        elif args.command == "rollback":
            print("\n🚨 EMERGENCY ROLLBACK")
            result = manager.rollback(reason=args.reason)
            print(json.dumps(result, indent=2))

        elif args.command == "flags":
            flags = manager.get_all_flags()
            print(json.dumps(flags, indent=2))

    finally:
        manager.close()


if __name__ == "__main__":
    main()
