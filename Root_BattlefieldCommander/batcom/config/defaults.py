"""
Default configuration values for BATCOM
"""

DEFAULT_CONFIG = {
    "logging": {
        "level": "INFO",
        "arma_console": False
    },
    "scan": {
        "tick": 2.0,
        "ai_groups": 5.0,
        "players": 3.0,
        "objectives": 5.0
    },
    "runtime": {
        "max_messages_per_tick": 50,
        "max_commands_per_tick": 30,
        "max_controlled_groups": 500
    },
    "ai": {
        "enabled": True,
        "provider": "openai",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "api_key": "",
        "model": "gpt-4",
        "timeout": 30
    },
    "safety": {
        "sandbox_enabled": True,
        "max_groups_per_objective": 10,
        "allowed_commands": [
            "move_to", "defend_area", "patrol_route", "seek_and_destroy", "spawn_squad",
            "transport_group", "escort_group", "fire_support", "deploy_asset"
        ],
        "blocked_commands": [],
        "audit_log": True
    }
}
