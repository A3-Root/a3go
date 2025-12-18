"""
Priority calculation logic

Computes dynamic priorities for objectives and assignments based on
threat level, distance, base priority, and other factors.
"""

import logging
from typing import List, Dict, Tuple
from ..models.objectives import Objective, ObjectiveType
from ..models.world import WorldState, Group

logger = logging.getLogger('batcom.decision.priority')


class PriorityCalculator:
    """
    Calculates dynamic priorities for objectives and assignments
    """

    def __init__(self):
        self.weights = {
            'base_priority': 1.0,
            'threat_level': 2.0,
            'distance': 0.3,
            'force_ratio': 1.5,
            'objective_type': 1.0
        }

    def calculate_objective_priority(self, objective: Objective, world_state: WorldState) -> float:
        """
        Calculate dynamic priority for an objective

        Args:
            objective: Objective to prioritize
            world_state: Current world state

        Returns:
            Calculated priority score (higher = more urgent)
        """
        score = 0.0

        # Base priority from objective
        score += objective.priority * self.weights['base_priority']

        # Threat level modifier
        threat_level = objective.metadata.get('threat_level', 0)
        if threat_level > 0:
            score += threat_level * self.weights['threat_level']

        # Objective type modifiers
        type_modifier = self._get_type_modifier(objective.type)
        score += type_modifier * self.weights['objective_type']

        # Force ratio (if applicable)
        enemy_count = objective.metadata.get('enemy_count', 0)
        friendly_count = objective.metadata.get('friendly_count', 0)

        if enemy_count > 0:
            if friendly_count == 0:
                # No friendlies, high priority
                score += 10.0 * self.weights['force_ratio']
            else:
                # Outnumbered = higher priority
                ratio = enemy_count / friendly_count
                if ratio > 1.0:
                    score += ratio * self.weights['force_ratio']

        # HVT alive check
        if objective.type == ObjectiveType.PROTECT_HVT:
            if not objective.metadata.get('hvt_alive', False):
                score = 0.0  # Failed, no priority

        logger.debug('Objective %s priority: %.2f (base=%d, threat=%d)',
                    objective.id, score, objective.priority, threat_level)

        return score

    def calculate_assignment_priority(
        self,
        objective: Objective,
        group: Group,
        world_state: WorldState
    ) -> float:
        """
        Calculate priority for assigning a specific group to an objective

        Args:
            objective: Target objective
            group: Group to assign
            world_state: Current world state

        Returns:
            Assignment priority score
        """
        # Start with objective priority
        score = self.calculate_objective_priority(objective, world_state)

        # Distance penalty (closer = higher priority)
        if objective.position and group.position:
            distance = self._calculate_distance(group.position, objective.position)
            # Normalize distance (assume 1000m is typical engagement range)
            distance_factor = max(0, 1.0 - (distance / 1000.0))
            score += distance_factor * self.weights['distance'] * 10.0

        # Group capability match
        capability_score = self._calculate_capability_match(group, objective)
        score += capability_score

        return score

    def rank_objectives(self, objectives: List[Objective], world_state: WorldState) -> List[Tuple[Objective, float]]:
        """
        Rank objectives by priority

        Args:
            objectives: List of objectives
            world_state: Current world state

        Returns:
            List of (objective, priority) tuples, sorted by priority (descending)
        """
        ranked = []

        for obj in objectives:
            priority = self.calculate_objective_priority(obj, world_state)
            ranked.append((obj, priority))

        # Sort by priority (highest first)
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked

    def rank_groups_for_objective(
        self,
        objective: Objective,
        groups: List[Group],
        world_state: WorldState
    ) -> List[Tuple[Group, float]]:
        """
        Rank groups by suitability for an objective

        Args:
            objective: Target objective
            groups: Available groups
            world_state: Current world state

        Returns:
            List of (group, priority) tuples, sorted by priority (descending)
        """
        ranked = []

        for group in groups:
            priority = self.calculate_assignment_priority(objective, group, world_state)
            ranked.append((group, priority))

        # Sort by priority (highest first)
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked

    def _get_type_modifier(self, obj_type: ObjectiveType) -> float:
        """Get priority modifier based on objective type"""
        modifiers = {
            ObjectiveType.PROTECT_HVT: 3.0,      # High priority
            ObjectiveType.DEFEND_AREA: 2.0,      # Medium-high
            ObjectiveType.ATTACK_AREA: 1.5,      # Medium
            ObjectiveType.PATROL_AREA: 1.0,      # Normal
            ObjectiveType.ELIMINATE_UNITS: 2.0,  # Medium-high
            ObjectiveType.CUSTOM: 1.0            # Normal
        }
        return modifiers.get(obj_type, 1.0)

    def _calculate_distance(self, pos1: List[float], pos2: List[float]) -> float:
        """Calculate 2D distance between positions"""
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        return (dx * dx + dy * dy) ** 0.5

    def _calculate_capability_match(self, group: Group, objective: Objective) -> float:
        """
        Calculate how well a group's capabilities match objective needs

        Returns:
            Capability match score (0-10)
        """
        score = 0.0

        # Type-based matching
        if objective.type == ObjectiveType.DEFEND_AREA:
            # Prefer infantry and mechanized for defense
            if group.type in ['infantry', 'mechanized']:
                score += 3.0

        elif objective.type == ObjectiveType.ATTACK_AREA:
            # Prefer armor and mechanized for attacks
            if group.type in ['armor', 'mechanized']:
                score += 4.0
            elif group.type == 'infantry':
                score += 2.0

        elif objective.type == ObjectiveType.PATROL_AREA:
            # Prefer mobile units for patrol
            if group.type in ['motorized', 'mechanized', 'armor']:
                score += 3.0

        elif objective.type == ObjectiveType.PROTECT_HVT:
            # Prefer infantry for close protection
            if group.type == 'infantry':
                score += 4.0

        elif objective.type == ObjectiveType.ELIMINATE_UNITS:
            # Prefer combat-capable units
            if group.type in ['armor', 'mechanized', 'air_fixed', 'air_rotary']:
                score += 3.0

        # Size considerations
        unit_count = group.unit_count
        if unit_count >= 8:
            score += 1.0  # Larger groups more capable
        elif unit_count <= 3:
            score -= 1.0  # Small groups less capable

        return score
