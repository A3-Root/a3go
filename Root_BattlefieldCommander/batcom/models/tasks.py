"""
Task data models

Tasks represent specific actions assigned to groups.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class TaskType(str, Enum):
    """Types of tasks"""
    MOVE_TO = "move_to"
    DEFEND_AREA = "defend_area"
    PATROL_ROUTE = "patrol_route"
    HUNT_ENEMY = "hunt_enemy"
    HOLD_POSITION = "hold_position"
    RETREAT = "retreat"


@dataclass
class Task:
    """
    Represents a task assigned to a group

    Attributes:
        id: Unique task identifier
        group_id: Target group ID
        type: Task type
        objective_id: Associated objective ID (optional)
        priority: Task priority
        params: Task-specific parameters
        metadata: Additional task data
    """
    id: str
    group_id: str
    type: TaskType
    objective_id: Optional[str] = None
    priority: int = 5
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "group_id": self.group_id,
            "type": self.type.value,
            "objective_id": self.objective_id,
            "priority": self.priority,
            "params": self.params,
            "metadata": self.metadata
        }


@dataclass
class GroupAssignment:
    """
    Represents a group assigned to an objective

    Attributes:
        group_id: Group ID
        objective_id: Objective ID
        role: Role in objective (e.g., "defender", "attacker", "reserve")
        priority: Assignment priority
    """
    group_id: str
    objective_id: str
    role: str = "default"
    priority: int = 5
