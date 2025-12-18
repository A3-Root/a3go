"""
Order parser - converts LLM JSON orders into Command objects
"""

import logging
from typing import List, Dict, Any, Optional

from ..models.commands import (
    Command, CommandType,
    MoveCommand, DefendCommand, PatrolCommand, SeekCommand, SpawnSquadCommand,
    TransportCommand, EscortCommand, FireSupportCommand, DeployAssetCommand
)

logger = logging.getLogger('batcom.ai.order_parser')


class OrderParser:
    """
    Parses LLM-generated JSON orders into Command objects
    """

    def __init__(self):
        """Initialize order parser"""
        self.spawned_group_ids = []  # Track group IDs from spawn commands

    def _validate_and_fix_position(self, position: Any, command_type: str) -> Optional[List[float]]:
        """
        Validate and normalize position data from LLM

        LLMs sometimes provide:
        - 2D positions [x, y] instead of 3D [x, y, z]
        - String coordinates that need parsing
        - Non-numeric values

        Args:
            position: Position data from LLM order
            command_type: Command type for logging

        Returns:
            Normalized [x, y, z] position or None if invalid
        """
        if not position:
            logger.warning("Missing position for %s order", command_type)
            return None

        # Handle non-list positions
        if not isinstance(position, (list, tuple)):
            logger.warning("Position is not a list/array for %s order (got %s)", command_type, type(position))
            return None

        # Convert to list if tuple
        if isinstance(position, tuple):
            position = list(position)

        # Check length - should be 2 or 3 elements
        if len(position) < 2:
            logger.warning("Position has fewer than 2 coordinates for %s order: %s", command_type, position)
            return None

        # Extract first 2-3 numeric values
        coords = []
        for i, val in enumerate(position[:3]):  # Only take first 3 values
            if isinstance(val, (int, float)):
                coords.append(float(val))
            elif isinstance(val, str):
                # Try to parse string numbers
                try:
                    coords.append(float(val))
                except (ValueError, TypeError):
                    logger.warning("Position coordinate %d is non-numeric string '%s' for %s order", i, val, command_type)
                    return None
            else:
                logger.warning("Position coordinate %d is invalid type %s for %s order", i, type(val), command_type)
                return None

        # Ensure we have at least X, Y
        if len(coords) < 2:
            logger.warning("Could not extract 2 valid coordinates from position for %s order: %s", command_type, position)
            return None

        # Add Z coordinate if missing (default to 0)
        if len(coords) == 2:
            coords.append(0.0)
            logger.debug("Added Z=0 to 2D position for %s order: %s -> %s", command_type, position, coords)

        return coords[:3]  # Return exactly [x, y, z]

    def parse_llm_orders(self, orders: List[Dict[str, Any]]) -> List[Command]:
        """
        Parse LLM orders with two-pass parsing

        Two-pass ensures spawn commands are executed first, then other commands
        can reference the spawned groups.

        Args:
            orders: List of order dictionaries from LLM

        Returns:
            List of Command objects
        """
        if not orders:
            logger.warning("No orders to parse")
            return []

        # Filter out non-dict orders (LLM sometimes returns strings or other types)
        valid_orders = []
        for i, order in enumerate(orders):
            if not isinstance(order, dict):
                logger.warning("Skipping non-dict order at index %d (type: %s): %s",
                             i, type(order).__name__, order)
                continue
            valid_orders.append(order)

        if len(valid_orders) < len(orders):
            logger.warning("Filtered out %d non-dict orders, %d valid orders remaining",
                         len(orders) - len(valid_orders), len(valid_orders))

        if not valid_orders:
            logger.warning("No valid orders after filtering")
            return []

        commands = []

        # Pass 1: Parse spawn/deploy commands
        spawn_orders = [o for o in valid_orders if o.get('type') in ['spawn_squad', 'deploy_asset']]
        for order in spawn_orders:
            if order.get('type') == 'spawn_squad':
                cmd = self._parse_spawn_squad(order)
            else:
                cmd = self._parse_deploy_asset(order)
            if cmd:
                commands.append(cmd)
                self.spawned_group_ids.append(cmd.group_id)
                logger.debug("Parsed spawn command: %s", cmd.group_id)

        # Pass 2: Parse other commands (can now reference spawned groups)
        other_orders = [o for o in valid_orders if o.get('type') not in ['spawn_squad', 'deploy_asset']]
        for order in other_orders:
            cmd = self._parse_order(order)
            if cmd:
                commands.append(cmd)
                logger.debug("Parsed %s command for group %s", cmd.type.value, cmd.group_id)

        logger.info("Parsed %d commands (%d spawns, %d tactical)",
                   len(commands), len(spawn_orders), len(other_orders))

        return commands

    def _parse_order(self, order: Dict[str, Any]) -> Optional[Command]:
        """
        Parse a single order into the appropriate Command type

        Args:
            order: Order dictionary

        Returns:
            Command object or None if parsing failed
        """
        try:
            order_type = order.get('type')
            if not order_type:
                logger.warning("Order missing 'type' field. Received order: %s", order)
                return None

            # Commands that don't use 'group_id' field (use command-specific fields instead)
            commands_with_alternate_id_fields = [
                'transport_group',  # Uses vehicle_group_id
                'escort_group',     # Uses escort_group_id
                'spawn_squad',      # No group_id (creates new group)
                'deploy_asset'      # No group_id (creates new group)
            ]

            # Validate group_id exists for commands that require it
            if order_type not in commands_with_alternate_id_fields:
                # Accept both 'group_id' and 'group' field names (LLM may use either)
                group_id = order.get('group_id') or order.get('group')
                if not group_id:
                    logger.warning("Order missing 'group_id' or 'group' field for command type '%s'. Received order: %s",
                                 order_type, order)
                    return None

            # Route to specific parser
            if order_type == 'move_to':
                return self._parse_move_to(order)
            elif order_type == 'defend_area':
                return self._parse_defend_area(order)
            elif order_type == 'patrol_route':
                return self._parse_patrol_route(order)
            elif order_type == 'seek_and_destroy':
                return self._parse_seek_and_destroy(order)
            elif order_type == 'transport_group':
                return self._parse_transport_group(order)
            elif order_type == 'escort_group':
                return self._parse_escort_group(order)
            elif order_type == 'fire_support':
                return self._parse_fire_support(order)
            else:
                logger.warning("Unknown order type: %s", order_type)
                return None

        except Exception as e:
            logger.error("Failed to parse order: %s", e, exc_info=True)
            return None

    def _parse_move_to(self, order: Dict[str, Any]) -> Optional[MoveCommand]:
        """Parse move_to order"""
        # Accept both 'group_id' and 'group' field names (LLM may use either)
        group_id = order.get('group_id') or order.get('group')
        # Accept both 'position' and 'location' field names (LLM may use either)
        position = self._validate_and_fix_position(
            order.get('position') or order.get('location'), 'move_to')

        if not position:
            return None

        # Optional parameters
        speed = order.get('speed', 'NORMAL')
        behaviour = order.get('behaviour', 'AWARE')
        combat_mode = order.get('combat_mode', 'YELLOW')

        return MoveCommand(
            group_id=group_id,
            position=position,
            speed=speed,
            behaviour=behaviour,
            combat_mode=combat_mode
        )

    def _parse_defend_area(self, order: Dict[str, Any]) -> Optional[DefendCommand]:
        """Parse defend_area order"""
        # Accept both 'group_id' and 'group' field names (LLM may use either)
        group_id = order.get('group_id') or order.get('group')
        # Accept both 'position' and 'location' field names (LLM may use either)
        position = self._validate_and_fix_position(
            order.get('position') or order.get('location'), 'defend_area')
        radius = order.get('radius', 100)

        if not position:
            return None

        if not isinstance(radius, (int, float)) or radius <= 0:
            logger.warning("Invalid radius for defend_area order")
            return None

        behaviour = order.get('behaviour', 'COMBAT')

        return DefendCommand(
            group_id=group_id,
            position=position,
            radius=radius,
            behaviour=behaviour
        )

    def _parse_patrol_route(self, order: Dict[str, Any]) -> Optional[PatrolCommand]:
        """Parse patrol_route order"""
        # Accept both 'group_id' and 'group' field names (LLM may use either)
        group_id = order.get('group_id') or order.get('group')
        waypoints_raw = order.get('waypoints', [])

        if not waypoints_raw or len(waypoints_raw) < 2:
            logger.warning("Patrol route needs at least 2 waypoints")
            return None

        # Validate and fix each waypoint
        waypoints = []
        for i, wp in enumerate(waypoints_raw):
            fixed_wp = self._validate_and_fix_position(wp, f'patrol_route[waypoint_{i}]')
            if not fixed_wp:
                logger.warning("Invalid waypoint %d in patrol route, skipping patrol command", i)
                return None
            waypoints.append(fixed_wp)

        speed = order.get('speed', 'NORMAL')
        behaviour = order.get('behaviour', 'SAFE')

        return PatrolCommand(
            group_id=group_id,
            waypoints=waypoints,
            speed=speed,
            behaviour=behaviour
        )

    def _parse_seek_and_destroy(self, order: Dict[str, Any]) -> Optional[SeekCommand]:
        """Parse seek_and_destroy order"""
        # Accept both 'group_id' and 'group' field names (LLM may use either)
        group_id = order.get('group_id') or order.get('group')
        # Accept both 'position' and 'location' field names (LLM may use either)
        position = self._validate_and_fix_position(
            order.get('position') or order.get('location'), 'seek_and_destroy')
        radius = order.get('radius', 200)

        if not position:
            return None

        if not isinstance(radius, (int, float)) or radius <= 0:
            logger.warning("Invalid radius for seek_and_destroy order")
            return None

        behaviour = order.get('behaviour', 'COMBAT')

        return SeekCommand(
            group_id=group_id,
            position=position,
            radius=radius,
            behaviour=behaviour
        )

    def _parse_transport_group(self, order: Dict[str, Any]) -> Optional[TransportCommand]:
        """Parse transport_group order"""
        vehicle_group_id = order.get('vehicle_group_id') or order.get('group_id')
        passenger_group_id = order.get('passenger_group_id')
        pickup = self._validate_and_fix_position(order.get('pickup'), 'transport_group[pickup]')
        dropoff = self._validate_and_fix_position(order.get('dropoff'), 'transport_group[dropoff]')

        if not vehicle_group_id or not passenger_group_id:
            logger.warning("transport_group missing vehicle or passenger group ids")
            return None

        if not pickup or not dropoff:
            logger.warning("transport_group missing valid pickup or dropoff position")
            return None

        return TransportCommand(
            vehicle_group_id=vehicle_group_id,
            passenger_group_id=passenger_group_id,
            pickup=pickup,
            dropoff=dropoff
        )

    def _parse_escort_group(self, order: Dict[str, Any]) -> Optional[EscortCommand]:
        """Parse escort_group order"""
        escort_group_id = order.get('escort_group_id') or order.get('group_id')
        target_group_id = order.get('target_group_id')
        radius = order.get('radius', 75)

        if not escort_group_id or not target_group_id:
            logger.warning("escort_group missing escort or target ids")
            return None

        if not isinstance(radius, (int, float)) or radius <= 0:
            logger.warning("escort_group invalid radius")
            return None

        return EscortCommand(
            escort_group_id=escort_group_id,
            target_group_id=target_group_id,
            radius=radius
        )

    def _parse_fire_support(self, order: Dict[str, Any]) -> Optional[FireSupportCommand]:
        """Parse fire_support order"""
        # Accept both 'group_id' and 'group' field names (LLM may use either)
        group_id = order.get('group_id') or order.get('group')
        # Accept both 'position' and 'location' field names (LLM may use either)
        position = self._validate_and_fix_position(
            order.get('position') or order.get('location'), 'fire_support')
        radius = order.get('radius', 250)

        if not group_id:
            logger.warning("fire_support missing group_id")
            return None

        if not position:
            return None

        if not isinstance(radius, (int, float)) or radius <= 0:
            logger.warning("fire_support invalid radius")
            return None

        return FireSupportCommand(
            group_id=group_id,
            position=position,
            radius=radius
        )

    def _parse_deploy_asset(self, order: Dict[str, Any]) -> Optional[DeployAssetCommand]:
        """Parse deploy_asset order (resource-pool backed spawn)"""
        side = order.get('side')
        asset_type = order.get('asset_type')
        # Accept both 'position' and 'location' field names (LLM may use either)
        position = self._validate_and_fix_position(
            order.get('position') or order.get('location'), 'deploy_asset')
        objective_id = order.get('objective_id')

        if not side or not asset_type:
            logger.warning("deploy_asset missing side or asset_type")
            return None

        if not position:
            return None

        return DeployAssetCommand(
            side=side,
            asset_type=asset_type,
            position=position,
            objective_id=objective_id
        )

    def _parse_spawn_squad(self, order: Dict[str, Any]) -> Optional[SpawnSquadCommand]:
        """Parse spawn_squad order"""
        side = order.get('side')
        unit_classes = order.get('unit_classes', [])
        # Accept both 'position' and 'location' field names (LLM may use either)
        position = self._validate_and_fix_position(
            order.get('position') or order.get('location'), 'spawn_squad')

        if not side:
            logger.warning("spawn_squad missing 'side' field")
            return None

        if side not in ['EAST', 'WEST', 'RESISTANCE']:
            logger.warning("Invalid side for spawn_squad: %s", side)
            return None

        if not unit_classes or not isinstance(unit_classes, list):
            logger.warning("spawn_squad missing or invalid 'unit_classes'")
            return None

        if len(unit_classes) == 0:
            logger.warning("spawn_squad has empty unit_classes")
            return None

        if not position:
            return None

        objective_id = order.get('objective_id')

        return SpawnSquadCommand(
            side=side,
            unit_classes=unit_classes,
            position=position,
            objective_id=objective_id
        )

    def reset(self):
        """Reset parser state (clear spawned group IDs)"""
        self.spawned_group_ids = []
