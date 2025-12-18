"""
World state data models

These classes represent the game world state at a point in time.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class UnitEquipment:
    """Represents equipment status for a single unit"""
    has_nvg: bool = False
    has_flashlight: bool = False
    primary_weapon: str = ""


@dataclass
class CasualtyEvent:
    """Record of a unit death"""
    victim_id: str  # Unit ID or group ID
    victim_side: str
    victim_type: str  # infantry, vehicle, etc.
    killer_id: Optional[str] = None  # Player UID or group ID
    killer_side: Optional[str] = None
    timestamp: float = 0.0
    position: List[float] = field(default_factory=list)
    weapon: str = ""
    objective_id: Optional[str] = None  # If death occurred near objective


@dataclass
class KnownEnemy:
    """Represents a known enemy group"""
    id: str
    side: str
    type: str
    position: List[float]
    unit_count: int
    knowledge: float  # knowsAbout value
    last_seen: float  # seconds since last seen


@dataclass
class Group:
    """Represents an AI group"""
    id: str
    side: str
    type: str  # infantry, motorized, mechanized, armor, air_rotary, air_fixed, naval
    position: List[float]
    unit_count: int
    casualties: int = 0
    behaviour: str = "AWARE"
    combat_mode: str = "YELLOW"
    speed_mode: str = "NORMAL"
    formation: str = "WEDGE"
    current_waypoint: int = 0
    waypoint_count: int = 0
    is_controlled: bool = False
    is_player_group: bool = False
    is_friendly: bool = False
    in_combat: bool = False
    current_waypoint_type: str = ""
    current_waypoint_pos: List[float] = field(default_factory=list)
    known_enemies: List[KnownEnemy] = field(default_factory=list)
    knowledge: float = 0.0  # For non-controlled groups, how well we know them
    units_equipment: List[UnitEquipment] = field(default_factory=list)
    avg_night_capability: float = 0.0  # Percentage of units with NVG
    casualty_events: List[CasualtyEvent] = field(default_factory=list)  # Casualty tracking
    is_hvt_group: bool = False  # Designated as HVT group
    hvt_players: List[str] = field(default_factory=list)  # Player UIDs marked as HVTs in this group


@dataclass
class Player:
    """Represents a player"""
    name: str
    uid: str
    side: str
    group_id: str
    position: List[float]
    is_in_vehicle: bool = False
    vehicle_type: str = ""
    behaviour: str = "AWARE"
    damage: float = 0.0
    is_hvt: bool = False  # Designated HVT
    hvt_reason: str = ""  # Why they're an HVT
    threat_score: float = 0.0  # Calculated threat level


@dataclass
class Objective:
    """Represents a mission objective marker"""
    id: str
    position: List[float]
    radius: float
    shape: str
    type: str
    text: str
    color: str
    friendly_count: int = 0
    enemy_count: int = 0


@dataclass
class WorldState:
    """Complete world state snapshot"""
    timestamp: float
    daytime: float
    weather: List[float]  # [overcast, rain, fog, wind]
    groups: List[Group]
    players: List[Player]
    objectives: List[Objective]
    world_name: str = "unknown"
    mission_name: str = "unknown"
    mission_variables: Dict[str, Any] = field(default_factory=dict)
    mission_intent: str = ""
    friendly_sides: List[str] = field(default_factory=list)
    controlled_sides: List[str] = field(default_factory=list)
    mission_time: float = 0.0
    is_night: bool = False
    ai_deployment: Dict[str, int] = field(default_factory=dict)  # {"EAST": 45, "WEST": 20}

    @property
    def controlled_groups(self) -> List[Group]:
        """Get only controlled groups"""
        return [g for g in self.groups if g.is_controlled]

    @property
    def enemy_groups(self) -> List[Group]:
        """Get known enemy groups (non-controlled)"""
        return [g for g in self.groups if not g.is_controlled]

    def get_group_by_id(self, group_id: str) -> Optional[Group]:
        """Find a group by ID"""
        for group in self.groups:
            if group.id == group_id:
                return group
        return None

    def get_objective_by_id(self, obj_id: str) -> Optional[Objective]:
        """Find an objective by ID"""
        for obj in self.objectives:
            if obj.id == obj_id:
                return obj
        return None
