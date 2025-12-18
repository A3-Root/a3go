"""
Objective data models

Objectives represent goals that the AI commander should pursue.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ObjectiveType(str, Enum):
    """Types of objectives"""
    PROTECT_HVT = "protect_hvt"
    DEFEND_AREA = "defend_area"
    ATTACK_AREA = "attack_area"
    PATROL_AREA = "patrol_area"
    ELIMINATE_UNITS = "eliminate_units"
    HUNT_ENEMY = "hunt_enemy"
    CUSTOM = "custom"


class ObjectiveState(str, Enum):
    """State of an objective"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Objective:
    """
    Represents a mission objective

    Attributes:
        id: Unique objective identifier
        type: Objective type
        description: Human-readable description
        priority: Priority level (0-10, higher = more important)
        state: Current state
        position: [x, y, z] coordinates (optional)
        radius: Area of effect in meters (optional)
        unit_classes: Unit class names for spawning (optional)
        metadata: Additional objective-specific data
    """
    id: str
    type: ObjectiveType
    description: str
    priority: int = 5
    state: ObjectiveState = ObjectiveState.PENDING
    position: List[float] = field(default_factory=list)
    radius: float = 0.0
    unit_classes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def task_type(self) -> Optional[str]:
        """Get task_type from metadata"""
        return self.metadata.get('task_type')

    @property
    def objective_name(self) -> str:
        """Get objective name from metadata"""
        return self.metadata.get('objective_name', self.description)

    @property
    def is_ao_linked(self) -> bool:
        """Check if objective is AO-linked"""
        return self.metadata.get('ao_linked', False)

    @property
    def tactical_importance(self) -> int:
        """Calculate tactical importance from task_type and priority"""
        task_type = self.task_type
        base = self.priority

        # Adjust based on task_type
        if task_type == 'defend_hq':
            return base  # HQ is already max priority (100)
        elif task_type in ['defend_radiotower', 'defend_gps_jammer']:
            return base + 10  # Force multipliers
        elif task_type in ['defend_mortar_pit', 'defend_supply_depot']:
            return base + 5  # Support assets
        else:
            return base

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "priority": self.priority,
            "state": self.state.value,
            "position": self.position,
            "radius": self.radius,
            "unit_classes": self.unit_classes,
            "metadata": self.metadata
        }
