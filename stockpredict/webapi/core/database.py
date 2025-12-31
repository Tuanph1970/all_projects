import pymysql
from typing import Optional
import os
from dataclasses import dataclass
import atexit


@dataclass
class DatabaseConfig:
    host: str
    user: str
    password: str
    database: str
    port: int


@dataclass
class SSHConfig:
    enabled: bool
    host: str
    port: int
    user: str
    password: str


class SSHTunnelManager:
    """Manages SSH tunnel for database connections."""
    _instance: Optional['SSHTunnelManager'] = None
    _tunnel = None
    _local_port: Optional[int] = None

    def __new__(cls) -> 'SSHTunnelManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.ssh_config = SSHConfig(
                enabled=os.getenv('SSH_ENABLED', 'false').lower() == 'true',
                host=os.getenv('SSH_HOST', '112.213.91.103'),
                port=int(os.getenv('SSH_PORT', '22')),
                user=os.getenv('SSH_USER', 'root'),
                password=os.getenv('SSH_PASSWORD', 'VietnamPA_2025')
            )
            self.db_host = os.getenv('DB_HOST', '127.0.0.1')
            self.db_port = int(os.getenv('DB_PORT', '3306'))
            self.initialized = True

            # Register cleanup on exit
            atexit.register(self.stop_tunnel)

    def start_tunnel(self) -> int:
        """Start SSH tunnel and return local port for MySQL connection."""
        if not self.ssh_config.enabled:
            return self.db_port

        if self._tunnel is not None and self._tunnel.is_active:
            return self._local_port

        try:
            from sshtunnel import SSHTunnelForwarder

            self._tunnel = SSHTunnelForwarder(
                (self.ssh_config.host, self.ssh_config.port),
                ssh_username=self.ssh_config.user,
                ssh_password=self.ssh_config.password,
                remote_bind_address=('127.0.0.1', self.db_port),
                local_bind_address=('127.0.0.1', 0)  # 0 = auto-assign port
            )
            self._tunnel.start()
            self._local_port = self._tunnel.local_bind_port
            print(f"SSH tunnel established: localhost:{self._local_port} -> {self.ssh_config.host}:{self.db_port}")
            return self._local_port
        except ImportError:
            print("Warning: sshtunnel not installed. Run: pip install sshtunnel")
            return self.db_port
        except Exception as e:
            print(f"Failed to establish SSH tunnel: {e}")
            raise

    def stop_tunnel(self):
        """Stop SSH tunnel."""
        if self._tunnel is not None:
            try:
                self._tunnel.stop()
                print("SSH tunnel closed")
            except Exception as e:
                print(f"Error closing SSH tunnel: {e}")
            finally:
                self._tunnel = None
                self._local_port = None

    def get_connection_params(self) -> tuple:
        """Get host and port for database connection."""
        if self.ssh_config.enabled:
            local_port = self.start_tunnel()
            return ('127.0.0.1', local_port)
        return (self.db_host, self.db_port)


class DatabaseConnection:
    _instance: Optional['DatabaseConnection'] = None
    _connection: Optional[pymysql.Connection] = None

    def __new__(cls) -> 'DatabaseConnection':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.ssh_manager = SSHTunnelManager()
            self.config = DatabaseConfig(
                host=os.getenv('DB_HOST', '127.0.0.1'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', 'Mysql_2025'),
                database=os.getenv('DB_NAME', 'defaultdb'),
                port=int(os.getenv('DB_PORT', '3306'))
            )
            self.initialized = True

    def get_connection(self) -> pymysql.Connection:
        if self._connection is None or not self._connection.open:
            host, port = self.ssh_manager.get_connection_params()
            self._connection = pymysql.connect(
                host=host,
                user=self.config.user,
                password=self.config.password,
                db=self.config.database,
                port=port,
                autocommit=True
            )
        return self._connection

    def close_connection(self):
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None


def get_database_connection() -> pymysql.Connection:
    """Get a new database connection with SSH tunnel support."""
    db_instance = DatabaseConnection()
    host, port = db_instance.ssh_manager.get_connection_params()
    return pymysql.connect(
        host=host,
        user=db_instance.config.user,
        password=db_instance.config.password,
        db=db_instance.config.database,
        port=port,
        autocommit=True
    )


# Global tunnel manager for Django integration
_django_tunnel_manager: Optional[SSHTunnelManager] = None


def get_django_db_settings() -> dict:
    """Get database settings for Django with SSH tunnel support."""
    global _django_tunnel_manager

    ssh_enabled = os.getenv('SSH_ENABLED', 'false').lower() == 'true'

    if ssh_enabled:
        if _django_tunnel_manager is None:
            _django_tunnel_manager = SSHTunnelManager()
        host, port = _django_tunnel_manager.get_connection_params()
    else:
        host = os.getenv('DB_HOST', '127.0.0.1')
        port = int(os.getenv('DB_PORT', '3306'))

    return {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.getenv('DB_NAME', 'defaultdb'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'Mysql_2025'),
        'HOST': host,
        'PORT': str(port),
    }
