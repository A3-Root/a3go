"""
Command generation logic

Converts tasks into executable commands for the command queue.
"""

import logging
from typing import List
from ..models.tasks import Task, TaskType
from ..models.commands import Command, MoveCommand, DefendCommand, PatrolCommand, SeekCommand, CommandType

logger = logging.getLogger('batcom.commands.generator')


class CommandGenerator:
    """
    Generates commands from tasks
    """

    def __init__(self):
        pass

    def generate_commands(self, tasks: List[Task]) -> List[Command]:
        """
        Convert tasks to commands

        Args:
            tasks: List of tasks

        Returns:
            List of commands ready for execution
        """
        commands = []

        for task in tasks:
            command = self._task_to_command(task)
            if command:
                commands.append(command)

        logger.info('Generated %d commands from %d tasks', len(commands), len(tasks))

        return commands

    def _task_to_command(self, task: Task) -> Command:
        """
        Convert single task to command

        Args:
            task: Task to convert

        Returns:
            Command object
        """
        if task.type == TaskType.MOVE_TO:
            return self._generate_move_command(task)

        elif task.type == TaskType.DEFEND_AREA:
            return self._generate_defend_command(task)

        elif task.type == TaskType.PATROL_ROUTE:
            return self._generate_patrol_command(task)

        elif task.type == TaskType.HUNT_ENEMY:
            return self._generate_seek_command(task)

        elif task.type == TaskType.HOLD_POSITION:
            return self._generate_hold_command(task)

        elif task.type == TaskType.RETREAT:
            return self._generate_retreat_command(task)

        logger.warning('Unknown task type: %s', task.type)
        return None

    def _generate_move_command(self, task: Task) -> MoveCommand:
        """Generate MOVE_TO command"""
        position = task.params.get('position', [0, 0, 0])

        return MoveCommand(
            group_id=task.group_id,
            position=position,
            speed=task.params.get('speed', 'NORMAL'),
            formation=task.params.get('formation', 'WEDGE'),
            behaviour=task.params.get('behaviour', 'AWARE'),
            combat_mode=task.params.get('combat_mode', 'YELLOW')
        )

    def _generate_defend_command(self, task: Task) -> DefendCommand:
        """Generate DEFEND_AREA command"""
        position = task.params.get('position', [0, 0, 0])
        radius = task.params.get('radius', 150)

        return DefendCommand(
            group_id=task.group_id,
            position=position,
            radius=radius,
            behaviour=task.params.get('behaviour', 'COMBAT'),
            combat_mode=task.params.get('combat_mode', 'YELLOW')
        )

    def _generate_patrol_command(self, task: Task) -> PatrolCommand:
        """Generate PATROL_ROUTE command"""
        position = task.params.get('position', [0, 0, 0])
        radius = task.params.get('radius', 300)

        # Generate patrol waypoints in a circle
        waypoints = self._generate_patrol_waypoints(position, radius)

        return PatrolCommand(
            group_id=task.group_id,
            waypoints=waypoints,
            speed=task.params.get('speed', 'LIMITED'),
            behaviour=task.params.get('behaviour', 'SAFE'),
            combat_mode=task.params.get('combat_mode', 'YELLOW')
        )

    def _generate_seek_command(self, task: Task) -> SeekCommand:
        """Generate HUNT_ENEMY (seek and destroy) command"""
        position = task.params.get('position', [0, 0, 0])
        radius = task.params.get('radius', 500)

        # Generate search waypoints
        search_positions = self._generate_search_waypoints(position, radius)

        return SeekCommand(
            group_id=task.group_id,
            search_positions=search_positions,
            behaviour=task.params.get('behaviour', 'COMBAT'),
            combat_mode=task.params.get('combat_mode', 'RED')
        )

    def _generate_hold_command(self, task: Task) -> DefendCommand:
        """Generate HOLD_POSITION command (using defend with small radius)"""
        position = task.params.get('position', [0, 0, 0])

        return DefendCommand(
            group_id=task.group_id,
            position=position,
            radius=50,  # Small radius for holding position
            behaviour=task.params.get('behaviour', 'AWARE'),
            combat_mode=task.params.get('combat_mode', 'YELLOW')
        )

    def _generate_retreat_command(self, task: Task) -> MoveCommand:
        """Generate RETREAT command (fast move with defensive posture)"""
        position = task.params.get('position', [0, 0, 0])

        return MoveCommand(
            group_id=task.group_id,
            position=position,
            speed='FULL',
            formation='COLUMN',
            behaviour='AWARE',
            combat_mode='GREEN'  # Hold fire while retreating
        )

    def _generate_patrol_waypoints(self, center: List[float], radius: float) -> List[List[float]]:
        """
        Generate circular patrol waypoints

        Args:
            center: Center position [x, y, z]
            radius: Patrol radius

        Returns:
            List of waypoint positions
        """
        import math

        waypoints = []
        num_points = 4  # Square patrol pattern

        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            waypoints.append([x, y, 0])

        return waypoints

    def _generate_search_waypoints(self, center: List[float], radius: float) -> List[List[float]]:
        """
        Generate search pattern waypoints

        Args:
            center: Center position [x, y, z]
            radius: Search radius

        Returns:
            List of search positions
        """
        import random

        search_positions = []

        # Generate 3-5 random search positions within radius
        num_positions = random.randint(3, 5)

        for _ in range(num_positions):
            # Random angle and distance
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(radius * 0.5, radius)

            x = center[0] + distance * (angle ** 0.5)  # Using angle as pseudo-cos
            y = center[1] + distance * ((2 * 3.14159 - angle) ** 0.5)  # Using as pseudo-sin

            search_positions.append([x, y, 0])

        # Always include center as final position
        search_positions.append(center)

        return search_positions
