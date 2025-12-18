"""
Command data models

These classes represent commands to be executed by AI groups.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import time
import threading

# Thread-safe counter for ensuring unique group IDs
_group_id_counter = 0
_group_id_lock = None  # Lazy initialization to avoid threading issues on Linux


def _get_lock():
    """Get or create the threading lock (lazy initialization for Linux compatibility)"""
    global _group_id_lock
    if _group_id_lock is None:
        _group_id_lock = threading.Lock()
    return _group_id_lock


def _generate_unique_group_id(prefix: str) -> str:
    """
    Generate a unique group ID with timestamp and counter.
    Thread-safe to prevent collisions when multiple commands are created simultaneously.

    Args:
        prefix: Prefix for the group ID (e.g., "DEPLOY_EAST", "SPAWN_WEST")

    Returns:
        Unique group ID string
    """
    global _group_id_counter
    with _get_lock():
        _group_id_counter += 1
        return f"{prefix}_{int(time.time() * 1000)}_{_group_id_counter}"


class CommandType(str, Enum):
    """Types of commands that can be issued"""
    DEPLOY_ASSET = "deploy_asset"
    MOVE_TO = "move_to"
    DEFEND_AREA = "defend_area"
    PATROL_ROUTE = "patrol_route"
    SEEK_AND_DESTROY = "seek_and_destroy"
    SPAWN_SQUAD = "spawn_squad"
    TRANSPORT_GROUP = "transport_group"
    ESCORT_GROUP = "escort_group"
    FIRE_SUPPORT = "fire_support"


@dataclass
class Command:
    """
    Represents a command to be executed by a group

    Attributes:
        group_id: Target group ID
        type: Command type
        params: Command-specific parameters
    """
    group_id: str
    type: CommandType
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for SQF serialization"""
        return {
            "group_id": self.group_id,
            "type": self.type.value,
            "params": self.params
        }


@dataclass
class MoveCommand(Command):
    """
    Move to a specific position

    Params:
        position: [x, y, z] coordinates
        speed: Speed mode ("SLOW", "LIMITED", "NORMAL", "FULL")
        formation: Formation type (optional)
        behaviour: Behaviour mode ("CARELESS", "SAFE", "AWARE", "COMBAT", "STEALTH")
        combat_mode: Combat mode ("BLUE", "GREEN", "WHITE", "YELLOW", "RED")
    """
    def __init__(self, group_id: str, position: List[float], **kwargs):
        super().__init__(
            group_id=group_id,
            type=CommandType.MOVE_TO,
            params={
                "position": position,
                **kwargs
            }
        )


@dataclass
class DefendCommand(Command):
    """
    Defend an area

    Params:
        position: [x, y, z] center of defense area
        radius: Defense radius in meters
        garrison: Whether to garrison buildings
        behaviour: Behaviour mode
    """
    def __init__(self, group_id: str, position: List[float], radius: float = 100, **kwargs):
        super().__init__(
            group_id=group_id,
            type=CommandType.DEFEND_AREA,
            params={
                "position": position,
                "radius": radius,
                **kwargs
            }
        )


@dataclass
class PatrolCommand(Command):
    """
    Patrol a route

    Params:
        waypoints: List of [x, y, z] positions
        speed: Speed mode
        behaviour: Behaviour mode
    """
    def __init__(self, group_id: str, waypoints: List[List[float]], **kwargs):
        super().__init__(
            group_id=group_id,
            type=CommandType.PATROL_ROUTE,
            params={
                "waypoints": waypoints,
                **kwargs
            }
        )


@dataclass
class SeekCommand(Command):
    """
    Search and destroy in an area

    Params:
        position: [x, y, z] center of search area
        radius: Search radius in meters
        behaviour: Behaviour mode (default: "COMBAT")
    """
    def __init__(self, group_id: str, position: List[float], radius: float = 200, **kwargs):
        super().__init__(
            group_id=group_id,
            type=CommandType.SEEK_AND_DESTROY,
            params={
                "position": position,
                "radius": radius,
                **kwargs
            }
        )


@dataclass
class SpawnSquadCommand(Command):
    """
    Spawn a new squad

    Params:
        side: Side to spawn units for ("EAST", "WEST", "RESISTANCE")
        unit_classes: List of unit class names to spawn
        position: [x, y, z] spawn position
        objective_id: Optional objective ID this spawn is associated with
    """
    def __init__(self, side: str, unit_classes: List[str], position: List[float], objective_id: Optional[str] = None, **kwargs):
        # Generate unique group_id using timestamp + counter
        super().__init__(
            group_id=_generate_unique_group_id(f"SPAWN_{side}"),
            type=CommandType.SPAWN_SQUAD,
            params={
                "side": side,
                "unit_classes": unit_classes,
                "position": position,
                "objective_id": objective_id,
                **kwargs
            }
        )


@dataclass
class TransportCommand(Command):
    """
    Coordinate a transport of a passenger group using a vehicle group

    Params:
        vehicle_group_id: Group providing transport (vehicle group)
        passenger_group_id: Infantry/passenger group
        pickup: [x, y, z] pickup position
        dropoff: [x, y, z] dropoff position
    """
    def __init__(self, vehicle_group_id: str, passenger_group_id: str, pickup: List[float], dropoff: List[float], **kwargs):
        super().__init__(
            group_id=vehicle_group_id,
            type=CommandType.TRANSPORT_GROUP,
            params={
                "vehicle_group_id": vehicle_group_id,
                "passenger_group_id": passenger_group_id,
                "pickup": pickup,
                "dropoff": dropoff,
                **kwargs
            }
        )


@dataclass
class EscortCommand(Command):
    """
    Escort a target group within a radius

    Params:
        escort_group_id: Group providing escort (also stored as group_id)
        target_group_id: Group to protect
        radius: Follow/cover radius
    """
    def __init__(self, escort_group_id: str, target_group_id: str, radius: float = 75.0, **kwargs):
        super().__init__(
            group_id=escort_group_id,
            type=CommandType.ESCORT_GROUP,
            params={
                "escort_group_id": escort_group_id,
                "target_group_id": target_group_id,
                "radius": radius,
                **kwargs
            }
        )


@dataclass
class FireSupportCommand(Command):
    """
    Direct a vehicle/armor/air group to perform fire support in an area

    Params:
        position: Target area center [x, y, z]
        radius: Engagement radius
    """
    def __init__(self, group_id: str, position: List[float], radius: float = 250.0, **kwargs):
        super().__init__(
            group_id=group_id,
            type=CommandType.FIRE_SUPPORT,
            params={
                "position": position,
                "radius": radius,
                **kwargs
            }
        )


@dataclass
class DeployAssetCommand(Command):
    """
    Deploy a predefined asset type using the resource pool

    Params:
        side: Side to spawn for
        asset_type: Logical asset key (e.g., attack_heli, infantry_squad)
        position: [x, y, z] spawn position
        objective_id: Optional objective id
    """
    def __init__(self, side: str, asset_type: str, position: List[float], objective_id: Optional[str] = None, **kwargs):
        super().__init__(
            group_id=_generate_unique_group_id(f"DEPLOY_{side}"),
            type=CommandType.DEPLOY_ASSET,
            params={
                "side": side,
                "asset_type": asset_type,
                "position": position,
                "objective_id": objective_id,
                **kwargs
            }
        )
