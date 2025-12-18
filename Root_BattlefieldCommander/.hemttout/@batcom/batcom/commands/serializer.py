"""
Command serializer - converts commands to SQF-compatible format
"""

import logging
from typing import Dict, Any, List
from ..models.commands import Command

logger = logging.getLogger('batcom.commands.serializer')


def serialize_command(command: Command) -> Dict[str, Any]:
    """
    Serialize a command to SQF-compatible dictionary

    Args:
        command: Command object to serialize

    Returns:
        Dictionary that can be passed to SQF
    """
    return command.to_dict()


def serialize_commands(commands: List[Command]) -> List[Dict[str, Any]]:
    """
    Serialize multiple commands

    Args:
        commands: List of Command objects

    Returns:
        List of serialized command dictionaries
    """
    return [serialize_command(cmd) for cmd in commands]


def validate_command(command_dict: Dict[str, Any]) -> bool:
    """
    Validate a serialized command has required fields

    Args:
        command_dict: Serialized command dictionary

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["group_id", "type", "params"]

    for field in required_fields:
        if field not in command_dict:
            logger.error('Command missing required field: %s', field)
            return False

    if not isinstance(command_dict["params"], dict):
        logger.error('Command params must be a dictionary')
        return False

    return True


def validate_commands(commands: List[Dict[str, Any]]) -> bool:
    """
    Validate a batch of serialized commands

    Args:
        commands: List of serialized command dictionaries

    Returns:
        True if all valid, False if any invalid
    """
    return all(validate_command(cmd) for cmd in commands)
