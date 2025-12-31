"""
Container Resource Limits and Auto-Scaling Configuration

Provides resource management and scaling configurations for production deployment.
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ScalingMetric(Enum):
    """Metrics used for scaling decisions"""
    CPU = "cpu"
    MEMORY = "memory"
    REQUEST_COUNT = "request_count"
    RESPONSE_TIME = "response_time"
    QUEUE_LENGTH = "queue_length"
    CUSTOM = "custom"


@dataclass
class ResourceLimits:
    """Container resource limits configuration"""

    # CPU limits
    cpu_request: str = "100m"      # Minimum CPU guaranteed
    cpu_limit: str = "500m"        # Maximum CPU allowed

    # Memory limits
    memory_request: str = "256Mi"  # Minimum memory guaranteed
    memory_limit: str = "512Mi"    # Maximum memory allowed

    # Ephemeral storage
    storage_request: str = "100Mi"
    storage_limit: str = "500Mi"


@dataclass
class ServiceResourceConfig:
    """Service-specific resource configurations"""

    # Per-service resource limits
    service_limits: Dict[str, ResourceLimits] = field(default_factory=lambda: {
        "auth": ResourceLimits(
            cpu_request="50m",
            cpu_limit="200m",
            memory_request="128Mi",
            memory_limit="256Mi"
        ),
        "stock-data": ResourceLimits(
            cpu_request="200m",
            cpu_limit="1000m",
            memory_request="512Mi",
            memory_limit="1Gi"
        ),
        "portfolio": ResourceLimits(
            cpu_request="100m",
            cpu_limit="500m",
            memory_request="256Mi",
            memory_limit="512Mi"
        ),
        "prediction": ResourceLimits(
            cpu_request="500m",
            cpu_limit="2000m",
            memory_request="1Gi",
            memory_limit="2Gi"
        ),
        "analysis": ResourceLimits(
            cpu_request="200m",
            cpu_limit="1000m",
            memory_request="512Mi",
            memory_limit="1Gi"
        ),
        "ai-insights": ResourceLimits(
            cpu_request="200m",
            cpu_limit="1000m",
            memory_request="512Mi",
            memory_limit="1Gi"
        ),
        "chatbot": ResourceLimits(
            cpu_request="100m",
            cpu_limit="500m",
            memory_request="256Mi",
            memory_limit="512Mi"
        ),
        "feature-flags": ResourceLimits(
            cpu_request="50m",
            cpu_limit="200m",
            memory_request="64Mi",
            memory_limit="128Mi"
        ),
        "shadow-comparator": ResourceLimits(
            cpu_request="100m",
            cpu_limit="500m",
            memory_request="256Mi",
            memory_limit="512Mi"
        ),
    })


@dataclass
class AutoScalingConfig:
    """Horizontal Pod Autoscaler configuration"""

    # Scaling bounds
    min_replicas: int = 2
    max_replicas: int = 10

    # Target utilization percentages
    target_cpu_utilization: int = 70
    target_memory_utilization: int = 80

    # Scaling behavior
    scale_up_stabilization_seconds: int = 60
    scale_down_stabilization_seconds: int = 300

    # Scale up policy
    scale_up_percent: int = 100      # Max % increase per period
    scale_up_pods: int = 4           # Max pods to add per period
    scale_up_period_seconds: int = 60

    # Scale down policy
    scale_down_percent: int = 25     # Max % decrease per period
    scale_down_pods: int = 1         # Max pods to remove per period
    scale_down_period_seconds: int = 60


@dataclass
class ServiceScalingConfig:
    """Service-specific auto-scaling configurations"""

    service_scaling: Dict[str, AutoScalingConfig] = field(default_factory=lambda: {
        "auth": AutoScalingConfig(
            min_replicas=2,
            max_replicas=8,
            target_cpu_utilization=60
        ),
        "stock-data": AutoScalingConfig(
            min_replicas=3,
            max_replicas=15,
            target_cpu_utilization=70
        ),
        "portfolio": AutoScalingConfig(
            min_replicas=2,
            max_replicas=10,
            target_cpu_utilization=70
        ),
        "prediction": AutoScalingConfig(
            min_replicas=2,
            max_replicas=8,
            target_cpu_utilization=80
        ),
        "analysis": AutoScalingConfig(
            min_replicas=2,
            max_replicas=10,
            target_cpu_utilization=75
        ),
        "ai-insights": AutoScalingConfig(
            min_replicas=2,
            max_replicas=6,
            target_cpu_utilization=75
        ),
        "chatbot": AutoScalingConfig(
            min_replicas=2,
            max_replicas=8,
            target_cpu_utilization=70
        ),
    })


@dataclass
class QoSConfig:
    """Quality of Service configuration"""

    # Request timeout settings
    request_timeout_seconds: int = 30
    connection_timeout_seconds: int = 5
    idle_timeout_seconds: int = 60

    # Circuit breaker settings
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 30
    circuit_breaker_half_open_requests: int = 3

    # Retry settings
    max_retries: int = 3
    retry_backoff_ms: int = 100
    retry_max_backoff_ms: int = 1000

    # Bulkhead settings (concurrent request limits)
    max_concurrent_requests: int = 100
    max_queued_requests: int = 50


def get_resource_config() -> ServiceResourceConfig:
    """Get service resource configuration"""
    return ServiceResourceConfig()


def get_scaling_config() -> ServiceScalingConfig:
    """Get service scaling configuration"""
    return ServiceScalingConfig()


def get_qos_config() -> QoSConfig:
    """Get QoS configuration"""
    return QoSConfig()


def get_resource_limits_for_service(service_name: str) -> ResourceLimits:
    """Get resource limits for a specific service"""
    config = get_resource_config()
    return config.service_limits.get(
        service_name,
        ResourceLimits()  # Default limits
    )


def get_scaling_config_for_service(service_name: str) -> AutoScalingConfig:
    """Get scaling configuration for a specific service"""
    config = get_scaling_config()
    return config.service_scaling.get(
        service_name,
        AutoScalingConfig()  # Default scaling
    )


# Kubernetes manifest generators
def generate_resource_manifest(service_name: str) -> Dict[str, Any]:
    """
    Generate Kubernetes resource limits manifest for a service

    Args:
        service_name: Name of the service

    Returns:
        Dict containing resources section for K8s manifest
    """
    limits = get_resource_limits_for_service(service_name)

    return {
        "resources": {
            "requests": {
                "cpu": limits.cpu_request,
                "memory": limits.memory_request,
                "ephemeral-storage": limits.storage_request,
            },
            "limits": {
                "cpu": limits.cpu_limit,
                "memory": limits.memory_limit,
                "ephemeral-storage": limits.storage_limit,
            }
        }
    }


def generate_hpa_manifest(
    service_name: str,
    namespace: str = "default"
) -> Dict[str, Any]:
    """
    Generate Kubernetes HPA manifest for a service

    Args:
        service_name: Name of the service
        namespace: Kubernetes namespace

    Returns:
        Complete HPA manifest as dict
    """
    scaling = get_scaling_config_for_service(service_name)

    return {
        "apiVersion": "autoscaling/v2",
        "kind": "HorizontalPodAutoscaler",
        "metadata": {
            "name": f"{service_name}-hpa",
            "namespace": namespace,
        },
        "spec": {
            "scaleTargetRef": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "name": service_name,
            },
            "minReplicas": scaling.min_replicas,
            "maxReplicas": scaling.max_replicas,
            "metrics": [
                {
                    "type": "Resource",
                    "resource": {
                        "name": "cpu",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": scaling.target_cpu_utilization,
                        }
                    }
                },
                {
                    "type": "Resource",
                    "resource": {
                        "name": "memory",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": scaling.target_memory_utilization,
                        }
                    }
                }
            ],
            "behavior": {
                "scaleUp": {
                    "stabilizationWindowSeconds": scaling.scale_up_stabilization_seconds,
                    "policies": [
                        {
                            "type": "Percent",
                            "value": scaling.scale_up_percent,
                            "periodSeconds": scaling.scale_up_period_seconds,
                        },
                        {
                            "type": "Pods",
                            "value": scaling.scale_up_pods,
                            "periodSeconds": scaling.scale_up_period_seconds,
                        }
                    ],
                    "selectPolicy": "Max",
                },
                "scaleDown": {
                    "stabilizationWindowSeconds": scaling.scale_down_stabilization_seconds,
                    "policies": [
                        {
                            "type": "Percent",
                            "value": scaling.scale_down_percent,
                            "periodSeconds": scaling.scale_down_period_seconds,
                        },
                        {
                            "type": "Pods",
                            "value": scaling.scale_down_pods,
                            "periodSeconds": scaling.scale_down_period_seconds,
                        }
                    ],
                    "selectPolicy": "Min",
                }
            }
        }
    }


def generate_pdb_manifest(
    service_name: str,
    namespace: str = "default",
    min_available: str = "50%"
) -> Dict[str, Any]:
    """
    Generate Pod Disruption Budget manifest

    Args:
        service_name: Name of the service
        namespace: Kubernetes namespace
        min_available: Minimum available pods (can be number or percentage)

    Returns:
        Complete PDB manifest as dict
    """
    return {
        "apiVersion": "policy/v1",
        "kind": "PodDisruptionBudget",
        "metadata": {
            "name": f"{service_name}-pdb",
            "namespace": namespace,
        },
        "spec": {
            "minAvailable": min_available,
            "selector": {
                "matchLabels": {
                    "app": service_name,
                }
            }
        }
    }


# Docker Compose resource configuration
def generate_docker_compose_resources(service_name: str) -> Dict[str, Any]:
    """
    Generate Docker Compose deploy resources for a service

    Args:
        service_name: Name of the service

    Returns:
        Deploy section for docker-compose.yml
    """
    limits = get_resource_limits_for_service(service_name)

    # Convert K8s format to Docker format
    def convert_cpu(k8s_cpu: str) -> float:
        if k8s_cpu.endswith("m"):
            return float(k8s_cpu[:-1]) / 1000
        return float(k8s_cpu)

    def convert_memory(k8s_mem: str) -> str:
        # Docker uses different suffixes
        return k8s_mem.replace("Gi", "G").replace("Mi", "M").replace("Ki", "K")

    return {
        "deploy": {
            "resources": {
                "limits": {
                    "cpus": str(convert_cpu(limits.cpu_limit)),
                    "memory": convert_memory(limits.memory_limit),
                },
                "reservations": {
                    "cpus": str(convert_cpu(limits.cpu_request)),
                    "memory": convert_memory(limits.memory_request),
                }
            },
            "restart_policy": {
                "condition": "on-failure",
                "delay": "5s",
                "max_attempts": 3,
                "window": "120s",
            }
        }
    }


# Resource monitoring utilities
@dataclass
class ResourceMetrics:
    """Current resource usage metrics"""
    cpu_usage_percent: float = 0.0
    memory_usage_bytes: int = 0
    memory_limit_bytes: int = 0
    disk_usage_bytes: int = 0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0

    @property
    def memory_usage_percent(self) -> float:
        if self.memory_limit_bytes == 0:
            return 0.0
        return (self.memory_usage_bytes / self.memory_limit_bytes) * 100


def check_resource_health(
    metrics: ResourceMetrics,
    limits: ResourceLimits
) -> Dict[str, Any]:
    """
    Check if resource usage is within healthy bounds

    Args:
        metrics: Current resource metrics
        limits: Resource limits configuration

    Returns:
        Health status dict
    """
    # Parse memory limit
    mem_limit = limits.memory_limit
    if mem_limit.endswith("Gi"):
        mem_limit_bytes = int(mem_limit[:-2]) * 1024 * 1024 * 1024
    elif mem_limit.endswith("Mi"):
        mem_limit_bytes = int(mem_limit[:-2]) * 1024 * 1024
    else:
        mem_limit_bytes = int(mem_limit)

    cpu_healthy = metrics.cpu_usage_percent < 80
    memory_healthy = (metrics.memory_usage_bytes / mem_limit_bytes * 100) < 85

    return {
        "healthy": cpu_healthy and memory_healthy,
        "cpu": {
            "usage_percent": metrics.cpu_usage_percent,
            "healthy": cpu_healthy,
            "threshold": 80,
        },
        "memory": {
            "usage_bytes": metrics.memory_usage_bytes,
            "limit_bytes": mem_limit_bytes,
            "usage_percent": metrics.memory_usage_bytes / mem_limit_bytes * 100,
            "healthy": memory_healthy,
            "threshold": 85,
        }
    }
