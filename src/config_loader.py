"""
Configuration Loader for AutoSteward AI
Loads project configuration from YAML file
"""

import yaml
import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class OpenMetadataConfig:
    host: str
    token: str
    verify_ssl: bool = True
    timeout: int = 120

@dataclass
class DatabaseConfig:
    type: str
    host: str
    port: int
    database: str
    username: str
    password: str
    docker_container: str = None

@dataclass
class ProjectConfig:
    name: str
    service_name: str
    database_name: str

@dataclass
class SeverityConfig:
    base_score: int = 30
    failing_test_points: int = 5
    max_failing_test_score: int = 20
    issue_type_scores: Dict[str, int] = None
    downstream_impact_points: int = 3
    max_downstream_impact_score: int = 15
    max_total_score: int = 100
    
    def __post_init__(self):
        if self.issue_type_scores is None:
            self.issue_type_scores = {
                'null_values': 20,
                'duplicates': 15,
                'format_mismatch': 10
            }

@dataclass
class DiscordNotifyOnConfig:
    issue_detected: bool = True
    fix_applied: bool = True
    fix_failed: bool = True
    error: bool = True

@dataclass
class DiscordPagingConfig:
    issue_detected_team: str = None
    fix_applied_team: str = None
    error_team: str = None

@dataclass
class DiscordConfig:
    enabled: bool = False
    webhook_url: str = None
    paging: DiscordPagingConfig = None
    notify_on: DiscordNotifyOnConfig = None
    
    def __post_init__(self):
        if self.paging is None:
            self.paging = DiscordPagingConfig()
        if self.notify_on is None:
            self.notify_on = DiscordNotifyOnConfig()

@dataclass
class AutoStewardConfig:
    openmetadata: OpenMetadataConfig
    database: DatabaseConfig
    project: ProjectConfig
    lineage: Dict[str, Any]
    monitoring: Dict[str, Any]
    ai: Dict[str, Any]
    severity: SeverityConfig
    discord: DiscordConfig = None

class ConfigLoader:
    """Loads configuration from YAML file with environment variable substitution"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.raw_config = self._load_yaml()
        self.config = self._parse_config()
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML file and substitute environment variables"""
        with open(self.config_path, 'r') as f:
            config_str = f.read()
        
        # Substitute environment variables
        config_str = self._substitute_env_vars(config_str)
        
        return yaml.safe_load(config_str)
    
    def _substitute_env_vars(self, text: str) -> str:
        """Replace ${VAR} with environment variable values"""
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))
        
        return re.sub(r'\$\{([^}]+)\}', replace_var, text)
    
    def _parse_config(self) -> AutoStewardConfig:
        """Parse raw YAML into typed configuration objects"""
        om = self.raw_config.get('openmetadata', {})
        db = self.raw_config.get('database', {})
        proj = self.raw_config.get('project', {})
        sev = self.raw_config.get('severity', {})
        disc = self.raw_config.get('discord', {})
        
        severity_config = SeverityConfig(
            base_score=sev.get('base_score', 30),
            failing_test_points=sev.get('failing_test_points', 5),
            max_failing_test_score=sev.get('max_failing_test_score', 20),
            issue_type_scores=sev.get('issue_type_scores', {
                'null_values': 20,
                'duplicates': 15,
                'format_mismatch': 10
            }),
            downstream_impact_points=sev.get('downstream_impact_points', 3),
            max_downstream_impact_score=sev.get('max_downstream_impact_score', 15),
            max_total_score=sev.get('max_total_score', 100)
        )
        
        # Parse discord notify_on config
        notify_on_raw = disc.get('notify_on', {})
        notify_on_config = DiscordNotifyOnConfig(
            issue_detected=notify_on_raw.get('issue_detected', True),
            fix_applied=notify_on_raw.get('fix_applied', True),
            fix_failed=notify_on_raw.get('fix_failed', True),
            error=notify_on_raw.get('error', True)
        )
        
        # Parse discord paging config
        paging_raw = disc.get('paging', {})
        paging_config = DiscordPagingConfig(
            issue_detected_team=paging_raw.get('issue_detected_team'),
            fix_applied_team=paging_raw.get('fix_applied_team'),
            error_team=paging_raw.get('error_team')
        )
        
        discord_config = DiscordConfig(
            enabled=disc.get('enabled', False),
            webhook_url=disc.get('webhook_url'),
            paging=paging_config,
            notify_on=notify_on_config
        )
        
        return AutoStewardConfig(
            openmetadata=OpenMetadataConfig(
                host=om.get('host', 'http://localhost:8585'),
                token=om.get('token', ''),
                verify_ssl=om.get('verify_ssl', True),
                timeout=om.get('timeout', 120)
            ),
            database=DatabaseConfig(
                type=db.get('type', 'postgresql'),
                host=db.get('host', 'localhost'),
                port=db.get('port', 5432),
                database=db.get('database', ''),
                username=db.get('username', ''),
                password=db.get('password', ''),
                docker_container=db.get('docker_container')
            ),
            project=ProjectConfig(
                name=proj.get('name', ''),
                service_name=proj.get('service_name', ''),
                database_name=proj.get('database_name', '')
            ),
            lineage=self.raw_config.get('lineage', {}),
            monitoring=self.raw_config.get('monitoring', {}),
            ai=self.raw_config.get('ai', {}),
            severity=severity_config,
            discord=discord_config
        )
    
    def get(self) -> AutoStewardConfig:
        """Return the parsed configuration"""
        return self.config

# Convenience function
def load_config(config_path: str = "config.yaml") -> AutoStewardConfig:
    """Load configuration from file"""
    loader = ConfigLoader(config_path)
    return loader.get()
