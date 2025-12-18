"""
Task planning logic

Generates specific tasks for groups based on their objective assignments.
"""

import logging
from typing import List, Dict
from ..models.objectives import Objective, ObjectiveType
from ..models.tasks import Task, TaskType, GroupAssignment
from ..models.world import WorldState, Group

logger = logging.getLogger('batcom.decision.planner')


class TaskPlanner:
    """
    Generates tasks for group assignments
    """

    def __init__(self):
        self.task_counter = 0

    def plan_tasks(
        self,
        assignments: List[GroupAssignment],
        objectives: List[Objective],
        world_state: WorldState
    ) -> List[Task]:
        """
        Generate tasks for all assignments

        Args:
            assignments: Group assignments
            objectives: All objectives
            world_state: Current world state

        Returns:
            List of tasks
        """
        tasks = []

        for assignment in assignments:
            # Find objective
            objective = self._find_objective(assignment.objective_id, objectives)
            if objective is None:
                logger.warning('Objective %s not found for assignment', assignment.objective_id)
                continue

            # Find group
            group = world_state.get_group_by_id(assignment.group_id)
            if group is None:
                logger.warning('Group %s not found', assignment.group_id)
                continue

            # Generate task
            task = self._plan_task(assignment, objective, group, world_state)
            if task:
                tasks.append(task)

        logger.info('Generated %d tasks from %d assignments', len(tasks), len(assignments))

        return tasks

    def _plan_task(
        self,
        assignment: GroupAssignment,
        objective: Objective,
        group: Group,
        world_state: WorldState
    ) -> Task:
        """
        Generate task for a specific assignment

        Args:
            assignment: Group assignment
            objective: Target objective
            group: Assigned group
            world_state: Current world state

        Returns:
            Generated task
        """
        # Route by objective type
        if objective.type == ObjectiveType.PROTECT_HVT:
            return self._plan_protect_hvt(assignment, objective, group, world_state)

        elif objective.type == ObjectiveType.DEFEND_AREA:
            return self._plan_defend_area(assignment, objective, group, world_state)

        elif objective.type == ObjectiveType.ATTACK_AREA:
            return self._plan_attack_area(assignment, objective, group, world_state)

        elif objective.type == ObjectiveType.PATROL_AREA:
            return self._plan_patrol_area(assignment, objective, group, world_state)

        elif objective.type == ObjectiveType.ELIMINATE_UNITS:
            return self._plan_eliminate_units(assignment, objective, group, world_state)

        elif objective.type == ObjectiveType.CUSTOM:
            return self._plan_custom(assignment, objective, group, world_state)

        logger.warning('Unknown objective type: %s', objective.type)
        return None

    def _plan_protect_hvt(
        self,
        assignment: GroupAssignment,
        objective: Objective,
        group: Group,
        world_state: WorldState
    ) -> Task:
        """Generate task for PROTECT_HVT objective"""
        # Find HVT position
        hvt_position = self._find_hvt_position(objective, world_state)

        if hvt_position is None:
            logger.warning('Could not find HVT position for objective %s', objective.id)
            hvt_position = objective.position or [0, 0, 0]

        # Defend around HVT
        task = Task(
            id=self._generate_task_id(),
            group_id=group.id,
            type=TaskType.DEFEND_AREA,
            objective_id=objective.id,
            priority=assignment.priority,
            params={
                'position': hvt_position,
                'radius': 100,
                'behaviour': 'COMBAT',
                'combat_mode': 'YELLOW',
                'speed': 'LIMITED'
            },
            metadata={'role': assignment.role}
        )

        logger.debug('Task %s: %s defends HVT at %s',
                    task.id, group.id, hvt_position)

        return task

    def _plan_defend_area(
        self,
        assignment: GroupAssignment,
        objective: Objective,
        group: Group,
        world_state: WorldState
    ) -> Task:
        """Generate task for DEFEND_AREA objective"""
        if not objective.position:
            logger.warning('DEFEND_AREA objective %s has no position', objective.id)
            return None

        radius = objective.radius or 150

        # Primary defender stays in area, reserve moves to area
        if assignment.role == 'defender':
            task_type = TaskType.DEFEND_AREA
        else:
            # Reserve holds position nearby
            task_type = TaskType.HOLD_POSITION

        task = Task(
            id=self._generate_task_id(),
            group_id=group.id,
            type=task_type,
            objective_id=objective.id,
            priority=assignment.priority,
            params={
                'position': objective.position,
                'radius': radius,
                'behaviour': 'COMBAT',
                'combat_mode': 'YELLOW'
            },
            metadata={'role': assignment.role}
        )

        logger.debug('Task %s: %s defends area at %s (role: %s)',
                    task.id, group.id, objective.position, assignment.role)

        return task

    def _plan_attack_area(
        self,
        assignment: GroupAssignment,
        objective: Objective,
        group: Group,
        world_state: WorldState
    ) -> Task:
        """Generate task for ATTACK_AREA objective"""
        if not objective.position:
            logger.warning('ATTACK_AREA objective %s has no position', objective.id)
            return None

        # Check if enemies present
        enemy_count = objective.metadata.get('enemy_count', 0)

        if enemy_count > 0:
            # Enemies present - seek and destroy
            task = Task(
                id=self._generate_task_id(),
                group_id=group.id,
                type=TaskType.HUNT_ENEMY,
                objective_id=objective.id,
                priority=assignment.priority,
                params={
                    'position': objective.position,
                    'radius': objective.radius or 200,
                    'behaviour': 'COMBAT',
                    'combat_mode': 'RED',
                    'speed': 'FULL'
                },
                metadata={'role': assignment.role}
            )
        else:
            # Area clear - move to secure
            task = Task(
                id=self._generate_task_id(),
                group_id=group.id,
                type=TaskType.MOVE_TO,
                objective_id=objective.id,
                priority=assignment.priority,
                params={
                    'position': objective.position,
                    'behaviour': 'AWARE',
                    'combat_mode': 'YELLOW',
                    'speed': 'NORMAL'
                },
                metadata={'role': assignment.role}
            )

        logger.debug('Task %s: %s attacks area at %s (enemies: %d)',
                    task.id, group.id, objective.position, enemy_count)

        return task

    def _plan_patrol_area(
        self,
        assignment: GroupAssignment,
        objective: Objective,
        group: Group,
        world_state: WorldState
    ) -> Task:
        """Generate task for PATROL_AREA objective"""
        if not objective.position:
            logger.warning('PATROL_AREA objective %s has no position', objective.id)
            return None

        radius = objective.radius or 300

        task = Task(
            id=self._generate_task_id(),
            group_id=group.id,
            type=TaskType.PATROL_ROUTE,
            objective_id=objective.id,
            priority=assignment.priority,
            params={
                'position': objective.position,
                'radius': radius,
                'behaviour': 'SAFE',
                'combat_mode': 'YELLOW',
                'speed': 'LIMITED'
            },
            metadata={'role': assignment.role}
        )

        logger.debug('Task %s: %s patrols area at %s (radius: %dm)',
                    task.id, group.id, objective.position, radius)

        return task

    def _plan_eliminate_units(
        self,
        assignment: GroupAssignment,
        objective: Objective,
        group: Group,
        world_state: WorldState
    ) -> Task:
        """Generate task for ELIMINATE_UNITS objective"""
        # Find target units
        target_position = self._find_target_position(objective, world_state)

        if target_position is None:
            logger.debug('No targets found for ELIMINATE_UNITS objective %s', objective.id)
            # Default to objective position or hold
            target_position = objective.position or group.position

        task = Task(
            id=self._generate_task_id(),
            group_id=group.id,
            type=TaskType.HUNT_ENEMY,
            objective_id=objective.id,
            priority=assignment.priority,
            params={
                'position': target_position,
                'radius': 500,
                'behaviour': 'COMBAT',
                'combat_mode': 'RED',
                'speed': 'FULL'
            },
            metadata={'role': assignment.role}
        )

        logger.debug('Task %s: %s hunts targets near %s',
                    task.id, group.id, target_position)

        return task

    def _plan_custom(
        self,
        assignment: GroupAssignment,
        objective: Objective,
        group: Group,
        world_state: WorldState
    ) -> Task:
        """Generate task for CUSTOM objective"""
        # Default to move to objective position
        position = objective.position or group.position

        task = Task(
            id=self._generate_task_id(),
            group_id=group.id,
            type=TaskType.MOVE_TO,
            objective_id=objective.id,
            priority=assignment.priority,
            params={
                'position': position,
                'behaviour': 'AWARE',
                'combat_mode': 'YELLOW'
            },
            metadata={'role': assignment.role}
        )

        logger.debug('Task %s: %s custom task at %s',
                    task.id, group.id, position)

        return task

    def _find_hvt_position(self, objective: Objective, world_state: WorldState) -> List[float]:
        """Find position of HVT unit"""
        # TODO: Requires individual unit data - not yet implemented
        logger.warning('HVT position finding requires unit-level data (not yet implemented)')
        return objective.position if objective.position else None

    def _find_target_position(self, objective: Objective, world_state: WorldState) -> List[float]:
        """Find position of target units"""
        # TODO: Requires individual unit data - not yet implemented
        logger.warning('Target position finding requires unit-level data (not yet implemented)')
        return objective.position if objective.position else None

    def _find_objective(self, obj_id: str, objectives: List[Objective]) -> Objective:
        """Find objective by ID"""
        for obj in objectives:
            if obj.id == obj_id:
                return obj
        return None

    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        self.task_counter += 1
        return f"TASK_{self.task_counter:04d}"
