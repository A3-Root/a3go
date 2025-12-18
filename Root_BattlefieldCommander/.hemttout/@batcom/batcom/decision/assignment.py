"""
Group assignment logic

Assigns available groups to objectives based on priorities and constraints.
"""

import logging
from typing import List, Dict, Set
from ..models.objectives import Objective, ObjectiveState
from ..models.tasks import GroupAssignment
from ..models.world import WorldState, Group
from .priority import PriorityCalculator

logger = logging.getLogger('batcom.decision.assignment')


class GroupAssigner:
    """
    Assigns groups to objectives
    """

    def __init__(self, priority_calculator: PriorityCalculator):
        self.priority_calc = priority_calculator

    def assign_groups(
        self,
        objectives: List[Objective],
        world_state: WorldState,
        existing_assignments: List[GroupAssignment] = None
    ) -> List[GroupAssignment]:
        """
        Assign controlled groups to objectives

        Args:
            objectives: Active objectives
            world_state: Current world state
            existing_assignments: Previous assignments (for continuity)

        Returns:
            List of group assignments
        """
        if existing_assignments is None:
            existing_assignments = []

        # Filter to active objectives only
        active_objectives = [obj for obj in objectives if obj.state == ObjectiveState.ACTIVE]

        if not active_objectives:
            logger.debug('No active objectives, clearing assignments')
            return []

        # Get controlled groups
        controlled_groups = world_state.controlled_groups

        if not controlled_groups:
            logger.debug('No controlled groups available')
            return []

        # Rank objectives by priority
        ranked_objectives = self.priority_calc.rank_objectives(active_objectives, world_state)

        logger.debug('Assigning %d groups to %d objectives',
                    len(controlled_groups), len(active_objectives))

        # Track assigned groups
        assigned_groups: Set[str] = set()
        assignments: List[GroupAssignment] = []

        # Try to maintain existing assignments first (continuity)
        for assignment in existing_assignments:
            # Check if objective still active
            obj = self._find_objective(assignment.objective_id, active_objectives)
            if obj is None:
                logger.debug('Objective %s no longer active, releasing group %s',
                           assignment.objective_id, assignment.group_id)
                continue

            # Check if group still exists
            group = world_state.get_group_by_id(assignment.group_id)
            if group is None:
                logger.debug('Group %s no longer exists', assignment.group_id)
                continue

            # Maintain assignment
            assigned_groups.add(group.id)
            assignments.append(assignment)
            logger.debug('Maintaining assignment: %s -> %s', group.id, obj.id)

        # Get unassigned groups
        unassigned_groups = [g for g in controlled_groups if g.id not in assigned_groups]

        # Assign remaining groups using greedy algorithm
        for obj, obj_priority in ranked_objectives:
            # Skip if no unassigned groups
            if not unassigned_groups:
                break

            # Determine how many groups this objective needs
            needed = self._calculate_groups_needed(obj, world_state, assignments)

            if needed <= 0:
                logger.debug('Objective %s has sufficient groups', obj.id)
                continue

            # Rank groups for this objective
            ranked_groups = self.priority_calc.rank_groups_for_objective(
                obj, unassigned_groups, world_state
            )

            # Assign top-ranked groups
            assigned_count = 0
            for group, group_priority in ranked_groups:
                if assigned_count >= needed:
                    break

                # Create assignment
                role = self._determine_role(obj, group, assignments)
                assignment = GroupAssignment(
                    group_id=group.id,
                    objective_id=obj.id,
                    role=role,
                    priority=int(obj_priority)
                )

                assignments.append(assignment)
                assigned_groups.add(group.id)
                unassigned_groups.remove(group)
                assigned_count += 1

                logger.info('Assigned %s (%s) to objective %s as %s',
                           group.id, group.type, obj.id, role)

        # Log summary
        logger.info('Assignment complete: %d groups assigned to %d objectives',
                   len(assignments), len(set(a.objective_id for a in assignments)))

        return assignments

    def _find_objective(self, obj_id: str, objectives: List[Objective]) -> Objective:
        """Find objective by ID"""
        for obj in objectives:
            if obj.id == obj_id:
                return obj
        return None

    def _calculate_groups_needed(
        self,
        objective: Objective,
        world_state: WorldState,
        existing_assignments: List[GroupAssignment]
    ) -> int:
        """
        Calculate how many additional groups an objective needs

        Args:
            objective: Target objective
            world_state: Current world state
            existing_assignments: Current assignments

        Returns:
            Number of groups needed
        """
        # Count already assigned groups
        assigned = sum(1 for a in existing_assignments if a.objective_id == objective.id)

        # Base requirements by objective type
        from ..models.objectives import ObjectiveType

        base_needed = 1  # Default: 1 group per objective

        # For CUSTOM objectives, scale by priority
        if objective.type == ObjectiveType.CUSTOM:
            # High priority (8+) = use all available groups
            if objective.priority >= 8:
                # Count all controlled groups
                total_groups = len(world_state.controlled_groups)
                # Assign all groups to high-priority objectives
                base_needed = total_groups
                logger.info('High-priority CUSTOM objective %s: assigning all %d groups',
                           objective.id, base_needed)
            elif objective.priority >= 5:
                base_needed = 2  # Medium priority gets 2 groups
            else:
                base_needed = 1  # Low priority gets 1 group

        elif objective.type == ObjectiveType.PROTECT_HVT:
            # HVT protection should use multiple groups for layered defense
            base_needed = min(3, len(world_state.controlled_groups))  # Use up to 3 groups

        elif objective.type == ObjectiveType.DEFEND_AREA:
            # Scale by threat level
            threat_level = objective.metadata.get('threat_level', 0)
            if threat_level > 5:
                base_needed = 3
            elif threat_level > 2:
                base_needed = 2
            else:
                base_needed = 1

        elif objective.type == ObjectiveType.ATTACK_AREA:
            # Scale by enemy count
            enemy_count = objective.metadata.get('enemy_count', 0)
            if enemy_count > 20:
                base_needed = 4
            elif enemy_count > 10:
                base_needed = 3
            elif enemy_count > 5:
                base_needed = 2
            else:
                base_needed = 1

        elif objective.type == ObjectiveType.PATROL_AREA:
            base_needed = 1  # One patrol group

        elif objective.type == ObjectiveType.ELIMINATE_UNITS:
            # Scale by targets
            remaining = objective.metadata.get('remaining_targets', 0)
            if remaining > 10:
                base_needed = 2
            else:
                base_needed = 1

        # Calculate needed
        needed = max(0, base_needed - assigned)

        logger.debug('Objective %s needs %d more groups (has %d, wants %d)',
                    objective.id, needed, assigned, base_needed)

        return needed

    def _determine_role(
        self,
        objective: Objective,
        group: Group,
        existing_assignments: List[GroupAssignment]
    ) -> str:
        """
        Determine role for group in objective

        Args:
            objective: Target objective
            group: Group to assign
            existing_assignments: Current assignments for this objective

        Returns:
            Role string (e.g., "attacker", "defender", "reserve")
        """
        from ..models.objectives import ObjectiveType

        # Count existing roles
        obj_assignments = [a for a in existing_assignments if a.objective_id == objective.id]
        role_index = len(obj_assignments)  # 0-indexed position for this group

        # For CUSTOM objectives, distribute roles intelligently
        if objective.type == ObjectiveType.CUSTOM:
            # Check if this is a protection/defense objective from description
            desc_lower = objective.description.lower()
            is_protection = any(word in desc_lower for word in ['protect', 'defend', 'hvt', 'guard', 'secure'])

            if is_protection:
                # Layered defense roles
                if role_index == 0:
                    return "primary_defender"
                elif role_index == 1:
                    return "support_defender"
                elif role_index == 2:
                    return "patrol"
                elif role_index == 3:
                    return "reserve"
                else:
                    return "reserve"
            else:
                # General roles
                if role_index == 0:
                    return "primary"
                elif role_index == 1:
                    return "support"
                else:
                    return "reserve"

        elif objective.type == ObjectiveType.PROTECT_HVT:
            # Layered HVT protection
            if role_index == 0:
                return "close_protector"
            elif role_index == 1:
                return "perimeter_defender"
            else:
                return "reserve"

        elif objective.type == ObjectiveType.DEFEND_AREA:
            # First group is primary defender
            if not obj_assignments:
                return "defender"
            else:
                return "reserve"

        elif objective.type == ObjectiveType.ATTACK_AREA:
            # Heavy units are attackers, light units are support
            if group.type in ['armor', 'mechanized']:
                return "attacker"
            else:
                return "support"

        elif objective.type == ObjectiveType.PATROL_AREA:
            return "patrol"

        elif objective.type == ObjectiveType.ELIMINATE_UNITS:
            return "hunter"

        return "default"

    def get_assignment_for_group(self, group_id: str, assignments: List[GroupAssignment]) -> GroupAssignment:
        """Get assignment for a specific group"""
        for assignment in assignments:
            if assignment.group_id == group_id:
                return assignment
        return None

    def get_assignments_for_objective(self, obj_id: str, assignments: List[GroupAssignment]) -> List[GroupAssignment]:
        """Get all assignments for a specific objective"""
        return [a for a in assignments if a.objective_id == obj_id]
