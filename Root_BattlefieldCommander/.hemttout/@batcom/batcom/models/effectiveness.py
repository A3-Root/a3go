"""
Player and group effectiveness tracking models
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ObjectiveCompletionEvent:
    """Records a specific objective completion event"""
    objective_id: str
    objective_type: str  # task_type (defend_hq, defend_radiotower, etc.)
    player_uid: str  # Player who completed it
    player_name: str
    group_id: str
    timestamp: float
    completion_method: str  # "killed", "captured", "destroyed", "disabled", "neutralized"


@dataclass
class PlayerStats:
    """Track player performance within an AO"""
    uid: str
    name: str
    group_id: str

    # Effectiveness metrics
    ai_kills: int = 0  # AI units killed
    objectives_cleared: int = 0  # High-value objectives completed (HQ, HVT, Radio Tower, GPS Jammer)
    objectives_captured: int = 0  # Area-based captures (Supply Depot)
    hvt_eliminations: int = 0  # HVTs killed
    hvt_captures: int = 0  # HVTs captured alive (more valuable than kills)
    commander_kills: int = 0  # HQ commanders killed
    commander_captures: int = 0  # HQ commanders captured alive (more valuable than kills)
    high_value_destructions: int = 0  # Radio towers, GPS jammers destroyed
    proximity_bonuses: int = 0  # Times player was near high-value completions by teammates
    time_in_ao: float = 0.0  # Seconds in AO
    deaths: int = 0

    # Contribution tracking
    objective_contributions: List[str] = field(default_factory=list)  # Objective IDs player was near
    objective_completions: List[ObjectiveCompletionEvent] = field(default_factory=list)  # Direct completions
    last_objective_proximity: Dict[str, float] = field(default_factory=dict)  # obj_id -> distance

    def threat_score(self) -> float:
        """
        Calculate threat score (0-100) based on actual completion events

        Weights:
        - HQ Commander capture: 40 points (captured alive is more dangerous)
        - HQ Commander kill: 30 points
        - HVT capture: 35 points (captured alive shows superior tactics)
        - HVT kill: 25 points
        - Radio Tower/GPS Jammer: 20 points each
        - Supply Depot capture: 15 points
        - Proximity bonus: 10 points each (being near high-value capture/kill)
        - AI kills: 2 points each
        - Proximity contributions: 5 points each (being near objectives generally)
        """
        score = 0.0

        # High-value completions (captures worth more than kills)
        score += self.commander_captures * 40
        score += self.commander_kills * 30
        score += self.hvt_captures * 35
        score += self.hvt_eliminations * 25
        score += self.high_value_destructions * 20
        score += self.objectives_captured * 15

        # Proximity bonuses for being near high-value events
        score += self.proximity_bonuses * 10

        # Combat effectiveness
        score += self.ai_kills * 2

        # Proximity contributions (being present during objective actions)
        proximity_contributions = len(self.objective_contributions) - len(self.objective_completions)
        score += max(0, proximity_contributions) * 5

        return min(100, score)


@dataclass
class GroupStats:
    """Track group performance within an AO"""
    group_id: str
    side: str

    # Group metrics
    objectives_cleared: int = 0
    total_kills: int = 0
    casualties_taken: int = 0
    initial_strength: int = 0
    current_strength: int = 0

    def effectiveness_ratio(self) -> float:
        """Kill/death ratio weighted by objectives"""
        if self.casualties_taken == 0:
            return float(self.total_kills + self.objectives_cleared * 5)
        return (self.total_kills + self.objectives_cleared * 5) / self.casualties_taken


@dataclass
class AOPerformanceData:
    """Performance data for a complete AO"""
    ao_id: str
    start_time: float
    end_time: float
    duration: float

    # Outcome metrics
    blufor_casualties: int = 0
    ai_casualties: int = 0
    objectives_lost: int = 0
    objectives_held: int = 0

    # Player tracking
    player_stats: Dict[str, PlayerStats] = field(default_factory=dict)  # uid -> stats
    group_stats: Dict[str, GroupStats] = field(default_factory=dict)  # group_id -> stats

    # HVT designations for next AO
    hvt_players: List[str] = field(default_factory=list)  # UIDs
    hvt_groups: List[str] = field(default_factory=list)  # Group IDs
