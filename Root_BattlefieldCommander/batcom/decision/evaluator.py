"""
Objective evaluation logic

Assesses objective states based on current world state.
"""

import logging
from typing import List, Dict, Any
from ..models.objectives import Objective, ObjectiveType, ObjectiveState
from ..models.world import WorldState, Group

logger = logging.getLogger('batcom.decision.evaluator')


class ObjectiveEvaluator:
    """
    Evaluates objectives against current world state
    """

    def __init__(self):
        pass

    def evaluate_objectives(self, objectives: List[Objective], world_state: WorldState) -> List[Objective]:
        """
        Evaluate all objectives and update their states

        Args:
            objectives: List of objectives to evaluate
            world_state: Current world state

        Returns:
            Updated list of objectives
        """
        updated_objectives = []

        for obj in objectives:
            updated_obj = self._evaluate_objective(obj, world_state)
            updated_objectives.append(updated_obj)

        return updated_objectives

    def _evaluate_objective(self, objective: Objective, world_state: WorldState) -> Objective:
        """
        Evaluate single objective

        Args:
            objective: Objective to evaluate
            world_state: Current world state

        Returns:
            Updated objective
        """
        # Skip if already completed or failed
        if objective.state in [ObjectiveState.COMPLETED, ObjectiveState.FAILED]:
            return objective

        # Activate pending objectives
        if objective.state == ObjectiveState.PENDING:
            objective.state = ObjectiveState.ACTIVE
            logger.info('Objective %s activated: %s', objective.id, objective.description)

        # Type-specific evaluation
        if objective.type == ObjectiveType.PROTECT_HVT:
            return self._evaluate_protect_hvt(objective, world_state)
        elif objective.type == ObjectiveType.DEFEND_AREA:
            return self._evaluate_defend_area(objective, world_state)
        elif objective.type == ObjectiveType.ATTACK_AREA:
            return self._evaluate_attack_area(objective, world_state)
        elif objective.type == ObjectiveType.PATROL_AREA:
            return self._evaluate_patrol_area(objective, world_state)
        elif objective.type == ObjectiveType.ELIMINATE_UNITS:
            return self._evaluate_eliminate_units(objective, world_state)
        elif objective.type == ObjectiveType.CUSTOM:
            return self._evaluate_custom(objective, world_state)

        return objective

    def _evaluate_protect_hvt(self, objective: Objective, world_state: WorldState) -> Objective:
        """Evaluate PROTECT_HVT objective"""
        # TODO: Requires individual unit data which is not currently available in Group model
        logger.warning('PROTECT_HVT evaluation requires unit-level data (not yet implemented)')
        return objective

    def _evaluate_defend_area(self, objective: Objective, world_state: WorldState) -> Objective:
        """Evaluate DEFEND_AREA objective"""
        if not objective.position:
            return objective

        radius = objective.radius or 200

        # Count friendlies in area
        friendly_count = self._count_units_in_area(
            objective.position, radius, world_state.controlled_groups
        )

        # Count enemies in area
        enemy_count = self._count_units_in_area(
            objective.position, radius, world_state.enemy_groups
        )

        objective.metadata['friendly_count'] = friendly_count
        objective.metadata['enemy_count'] = enemy_count
        objective.metadata['area_secure'] = enemy_count == 0

        # Mark failed if enemies dominate
        if enemy_count > friendly_count * 2:
            objective.state = ObjectiveState.FAILED
            logger.info('DEFEND_AREA objective %s failed - area overrun', objective.id)

        return objective

    def _evaluate_attack_area(self, objective: Objective, world_state: WorldState) -> Objective:
        """Evaluate ATTACK_AREA objective"""
        if not objective.position:
            return objective

        radius = objective.radius or 200

        # Count enemies in area
        enemy_count = self._count_units_in_area(
            objective.position, radius, world_state.enemy_groups
        )

        # Count friendlies in area
        friendly_count = self._count_units_in_area(
            objective.position, radius, world_state.controlled_groups
        )

        objective.metadata['enemy_count'] = enemy_count
        objective.metadata['friendly_count'] = friendly_count

        # Mark completed if area cleared and friendlies present
        if enemy_count == 0 and friendly_count > 0:
            objective.state = ObjectiveState.COMPLETED
            logger.info('ATTACK_AREA objective %s completed - area secured', objective.id)

        return objective

    def _evaluate_patrol_area(self, objective: Objective, world_state: WorldState) -> Objective:
        """Evaluate PATROL_AREA objective"""
        # Patrol areas are ongoing - just check for threats
        if objective.position:
            radius = objective.radius or 500
            threat_count = self._count_nearby_threats(objective.position, world_state, radius)
            objective.metadata['threat_level'] = threat_count

        return objective

    def _evaluate_eliminate_units(self, objective: Objective, world_state: WorldState) -> Objective:
        """Evaluate ELIMINATE_UNITS objective"""
        # TODO: Requires individual unit data which is not currently available in Group model
        logger.warning('ELIMINATE_UNITS evaluation requires unit-level data (not yet implemented)')
        return objective

    def _evaluate_custom(self, objective: Objective, world_state: WorldState) -> Objective:
        """Evaluate CUSTOM objective"""
        # Custom objectives remain active until manually updated
        # Could add AI evaluation here in Phase 7
        return objective

    def _count_units_in_area(self, position: List[float], radius: float, groups: List[Group]) -> int:
        """Count units within radius of position"""
        count = 0

        for group in groups:
            if not group.position:
                continue

            # Calculate distance
            dx = group.position[0] - position[0]
            dy = group.position[1] - position[1]
            distance = (dx * dx + dy * dy) ** 0.5

            if distance <= radius:
                # Use unit_count instead of iterating over units
                count += group.unit_count

        return count

    def _count_nearby_threats(self, position: List[float], world_state: WorldState, radius: float) -> int:
        """Count enemy units near position"""
        return self._count_units_in_area(position, radius, world_state.enemy_groups)

    def get_active_objectives(self, objectives: List[Objective]) -> List[Objective]:
        """Get list of active objectives"""
        return [obj for obj in objectives if obj.state == ObjectiveState.ACTIVE]

    def get_objectives_needing_attention(self, objectives: List[Objective]) -> List[Objective]:
        """Get objectives that need immediate attention"""
        needs_attention = []

        for obj in objectives:
            if obj.state != ObjectiveState.ACTIVE:
                continue

            # High threat level
            if obj.metadata.get('threat_level', 0) > 5:
                needs_attention.append(obj)
                continue

            # Area being contested
            if obj.type in [ObjectiveType.DEFEND_AREA, ObjectiveType.ATTACK_AREA]:
                enemy_count = obj.metadata.get('enemy_count', 0)
                if enemy_count > 0:
                    needs_attention.append(obj)

        return needs_attention
