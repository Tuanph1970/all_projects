"""
Load Balancer Configuration

Provides load balancer configurations for high availability deployment.
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class LoadBalancingAlgorithm(Enum):
    """Load balancing algorithms"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    IP_HASH = "ip_hash"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"


class SessionAffinity(Enum):
    """Session affinity modes"""
    NONE = "none"
    CLIENT_IP = "client_ip"
    COOKIE = "cookie"
    HEADER = "header"


@dataclass
class HealthCheckPolicy:
    """Load balancer health check policy"""

    # Check settings
    check_path: str = "/health/ready"
    check_interval_seconds: int = 10
    check_timeout_seconds: int = 5
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2

    # Check method
    check_method: str = "GET"
    expected_status_codes: List[int] = field(default_factory=lambda: [200])

    # Advanced settings
    check_host: Optional[str] = None
    check_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class BackendServer:
    """Backend server configuration"""
    address: str
    port: int
    weight: int = 1
    max_connections: int = 100
    backup: bool = False
    down: bool = False


@dataclass
class LoadBalancerConfig:
    """Load balancer configuration"""

    # Algorithm
    algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN

    # Session affinity
    session_affinity: SessionAffinity = SessionAffinity.NONE
    affinity_cookie_name: str = "SERVERID"
    affinity_cookie_ttl_seconds: int = 3600

    # Health check
    health_check: HealthCheckPolicy = field(default_factory=HealthCheckPolicy)

    # Connection settings
    max_connections_per_backend: int = 100
    connection_timeout_seconds: int = 5
    request_timeout_seconds: int = 60
    idle_timeout_seconds: int = 300

    # Retry settings
    retry_attempts: int = 3
    retry_on_status_codes: List[int] = field(default_factory=lambda: [502, 503, 504])

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_second: int = 100


@dataclass
class ServiceLoadBalancerConfig:
    """Service-specific load balancer configurations"""

    service_configs: Dict[str, LoadBalancerConfig] = field(default_factory=lambda: {
        "auth": LoadBalancerConfig(
            algorithm=LoadBalancingAlgorithm.ROUND_ROBIN,
            session_affinity=SessionAffinity.NONE,
            max_connections_per_backend=50,
        ),
        "stock-data": LoadBalancerConfig(
            algorithm=LoadBalancingAlgorithm.LEAST_CONNECTIONS,
            session_affinity=SessionAffinity.NONE,
            max_connections_per_backend=200,
            request_timeout_seconds=30,
        ),
        "portfolio": LoadBalancerConfig(
            algorithm=LoadBalancingAlgorithm.ROUND_ROBIN,
            session_affinity=SessionAffinity.CLIENT_IP,
            max_connections_per_backend=100,
        ),
        "prediction": LoadBalancerConfig(
            algorithm=LoadBalancingAlgorithm.LEAST_CONNECTIONS,
            session_affinity=SessionAffinity.NONE,
            max_connections_per_backend=50,
            request_timeout_seconds=120,  # ML predictions can be slow
        ),
        "chatbot": LoadBalancerConfig(
            algorithm=LoadBalancingAlgorithm.ROUND_ROBIN,
            session_affinity=SessionAffinity.COOKIE,  # Maintain conversation context
            max_connections_per_backend=100,
        ),
    })


def get_load_balancer_config(service_name: str) -> LoadBalancerConfig:
    """Get load balancer configuration for a service"""
    config = ServiceLoadBalancerConfig()
    return config.service_configs.get(
        service_name,
        LoadBalancerConfig()  # Default config
    )


# Traefik configuration generators
def generate_traefik_service(
    service_name: str,
    backends: List[BackendServer],
    config: Optional[LoadBalancerConfig] = None
) -> Dict[str, Any]:
    """
    Generate Traefik service configuration

    Args:
        service_name: Name of the service
        backends: List of backend servers
        config: Optional load balancer configuration

    Returns:
        Traefik service configuration dict
    """
    config = config or get_load_balancer_config(service_name)

    # Build servers list
    servers = []
    for backend in backends:
        server = {
            "url": f"http://{backend.address}:{backend.port}",
        }
        if config.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            server["weight"] = backend.weight
        servers.append(server)

    service_config = {
        "loadBalancer": {
            "servers": servers,
            "healthCheck": {
                "path": config.health_check.check_path,
                "interval": f"{config.health_check.check_interval_seconds}s",
                "timeout": f"{config.health_check.check_timeout_seconds}s",
            },
            "passHostHeader": True,
        }
    }

    # Add sticky session if needed
    if config.session_affinity == SessionAffinity.COOKIE:
        service_config["loadBalancer"]["sticky"] = {
            "cookie": {
                "name": config.affinity_cookie_name,
                "secure": True,
                "httpOnly": True,
            }
        }

    return service_config


def generate_traefik_middleware(
    service_name: str,
    config: Optional[LoadBalancerConfig] = None
) -> Dict[str, Any]:
    """Generate Traefik middleware configuration"""
    config = config or get_load_balancer_config(service_name)

    middlewares = {}

    # Rate limiting middleware
    if config.rate_limit_enabled:
        middlewares[f"{service_name}-ratelimit"] = {
            "rateLimit": {
                "average": config.rate_limit_requests_per_second,
                "burst": config.rate_limit_requests_per_second * 2,
                "period": "1s",
            }
        }

    # Retry middleware
    if config.retry_attempts > 0:
        middlewares[f"{service_name}-retry"] = {
            "retry": {
                "attempts": config.retry_attempts,
                "initialInterval": "100ms",
            }
        }

    # Circuit breaker middleware
    middlewares[f"{service_name}-circuit-breaker"] = {
        "circuitBreaker": {
            "expression": "NetworkErrorRatio() > 0.5 || ResponseCodeRatio(500, 600, 0, 600) > 0.5",
            "checkPeriod": "10s",
            "fallbackDuration": "30s",
            "recoveryDuration": "30s",
        }
    }

    return middlewares


# Nginx configuration generator
def generate_nginx_upstream(
    service_name: str,
    backends: List[BackendServer],
    config: Optional[LoadBalancerConfig] = None
) -> str:
    """
    Generate Nginx upstream configuration

    Args:
        service_name: Name of the service
        backends: List of backend servers
        config: Optional load balancer configuration

    Returns:
        Nginx upstream configuration string
    """
    config = config or get_load_balancer_config(service_name)

    lines = [f"upstream {service_name} {{"]

    # Add load balancing directive
    if config.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
        lines.append("    least_conn;")
    elif config.algorithm == LoadBalancingAlgorithm.IP_HASH:
        lines.append("    ip_hash;")
    elif config.algorithm == LoadBalancingAlgorithm.RANDOM:
        lines.append("    random;")

    # Add servers
    for backend in backends:
        server_line = f"    server {backend.address}:{backend.port}"
        if backend.weight != 1:
            server_line += f" weight={backend.weight}"
        if backend.max_connections:
            server_line += f" max_conns={backend.max_connections}"
        if backend.backup:
            server_line += " backup"
        if backend.down:
            server_line += " down"
        server_line += ";"
        lines.append(server_line)

    # Add keepalive
    lines.append(f"    keepalive {config.max_connections_per_backend // 4};")

    lines.append("}")

    return "\n".join(lines)


def generate_nginx_health_check(
    service_name: str,
    config: Optional[LoadBalancerConfig] = None
) -> str:
    """Generate Nginx health check location"""
    config = config or get_load_balancer_config(service_name)

    return f"""
location /{service_name}/health {{
    proxy_pass http://{service_name}{config.health_check.check_path};
    proxy_connect_timeout {config.health_check.check_timeout_seconds}s;
    proxy_read_timeout {config.health_check.check_timeout_seconds}s;

    # Health check specific settings
    health_check interval={config.health_check.check_interval_seconds}s
                 fails={config.health_check.unhealthy_threshold}
                 passes={config.health_check.healthy_threshold}
                 uri={config.health_check.check_path}
                 match=health_ok;
}}

match health_ok {{
    status {' '.join(map(str, config.health_check.expected_status_codes))};
}}
"""


# HAProxy configuration generator
def generate_haproxy_backend(
    service_name: str,
    backends: List[BackendServer],
    config: Optional[LoadBalancerConfig] = None
) -> str:
    """
    Generate HAProxy backend configuration

    Args:
        service_name: Name of the service
        backends: List of backend servers
        config: Optional load balancer configuration

    Returns:
        HAProxy backend configuration string
    """
    config = config or get_load_balancer_config(service_name)

    lines = [f"backend {service_name}_backend"]

    # Balance algorithm
    algo_map = {
        LoadBalancingAlgorithm.ROUND_ROBIN: "roundrobin",
        LoadBalancingAlgorithm.LEAST_CONNECTIONS: "leastconn",
        LoadBalancingAlgorithm.IP_HASH: "source",
        LoadBalancingAlgorithm.RANDOM: "random",
    }
    lines.append(f"    balance {algo_map.get(config.algorithm, 'roundrobin')}")

    # Health check
    lines.append(f"    option httpchk GET {config.health_check.check_path}")
    lines.append(f"    http-check expect status {config.health_check.expected_status_codes[0]}")

    # Timeouts
    lines.append(f"    timeout connect {config.connection_timeout_seconds}s")
    lines.append(f"    timeout server {config.request_timeout_seconds}s")

    # Cookie-based sticky sessions
    if config.session_affinity == SessionAffinity.COOKIE:
        lines.append(f"    cookie {config.affinity_cookie_name} insert indirect nocache")

    # Retry
    lines.append(f"    retries {config.retry_attempts}")

    # Servers
    for i, backend in enumerate(backends):
        server_line = f"    server {service_name}_{i} {backend.address}:{backend.port}"
        server_line += f" weight {backend.weight}"
        server_line += f" maxconn {backend.max_connections}"
        server_line += " check"
        server_line += f" inter {config.health_check.check_interval_seconds}s"
        server_line += f" fall {config.health_check.unhealthy_threshold}"
        server_line += f" rise {config.health_check.healthy_threshold}"

        if config.session_affinity == SessionAffinity.COOKIE:
            server_line += f" cookie s{i}"
        if backend.backup:
            server_line += " backup"

        lines.append(server_line)

    return "\n".join(lines)
