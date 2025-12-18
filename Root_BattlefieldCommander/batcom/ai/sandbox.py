"""
Command sandbox - validates all LLM-generated commands for safety
"""

import logging
from typing import Dict, Any, List, Optional
from ..models.commands import Command, CommandType, SpawnSquadCommand
from ..models.world import WorldState

logger = logging.getLogger('batcom.ai.sandbox')


class CommandValidator:
    """
    Safety validator for all LLM-generated commands

    Ensures commands are safe, valid, and within acceptable bounds.
    """

    def __init__(self, config: Dict[str, Any], state_manager=None):
        """
        Initialize command validator

        Args:
            config: Configuration dictionary with safety settings
        """
        self.state = state_manager
        self.enabled = config.get('sandbox_enabled', True)
        self.allowed_commands = set(config.get('allowed_commands', [
            'move_to', 'defend_area', 'patrol_route', 'seek_and_destroy', 'spawn_squad',
            'transport_group', 'escort_group', 'fire_support', 'deploy_asset'
        ]))
        self.blocked_commands = set(config.get('blocked_commands', []))
        self.max_units_per_side = config.get('max_units_per_side', 100)
        self.map_bounds = config.get('map_bounds', {'min_x': 0, 'min_y': 0, 'max_x': 40000, 'max_y': 40000})
        self.audit_log_enabled = config.get('audit_log', True)

        # Override map bounds with AO guardrails if provided by state
        if state_manager and getattr(state_manager, "ao_bounds", None):
            ao = state_manager.ao_bounds
            # Accept either box or circle; we only enforce box here
            if all(k in ao for k in ['min_x', 'max_x', 'min_y', 'max_y']):
                self.map_bounds = {
                    'min_x': ao.get('min_x'),
                    'min_y': ao.get('min_y'),
                    'max_x': ao.get('max_x'),
                    'max_y': ao.get('max_y')
                }

        logger.info("CommandValidator initialized (enabled: %s)", self.enabled)

    def validate_commands(
        self,
        commands: List[Command],
        world_state: WorldState
    ) -> List[Command]:
        """
        Validate a list of commands

        Args:
            commands: List of commands to validate
            world_state: Current world state

        Returns:
            List of valid commands (invalid ones are filtered out)
        """
        if not self.enabled:
            logger.warning("Sandbox validation is DISABLED - all commands pass through!")
            return commands

        valid_commands = []

        for cmd in commands:
            if self.is_safe(cmd, world_state):
                valid_commands.append(cmd)
                self._audit_log("ALLOWED", cmd, "Command passed validation")
            else:
                self._audit_log("BLOCKED", cmd, "Command failed validation")

        logger.info("Validated %d commands: %d allowed, %d blocked",
                   len(commands), len(valid_commands), len(commands) - len(valid_commands))

        return valid_commands

    def is_safe(self, command: Command, world_state: WorldState) -> bool:
        """
        Check if a command is safe to execute

        Args:
            command: Command to validate
            world_state: Current world state

        Returns:
            True if command is safe
        """
        try:
            # Check 1: Command type in allowed list
            if command.type.value not in self.allowed_commands:
                logger.warning("Command type '%s' not in allowed list", command.type.value)
                return False

            # Check 2: Command type not in blocked list
            if command.type.value in self.blocked_commands:
                logger.warning("Command type '%s' is in blocked list", command.type.value)
                return False

            # Check 3: Type-specific validation
            if command.type == CommandType.SPAWN_SQUAD:
                if not self._validate_spawn_command(command, world_state):
                    return False
            elif command.type == CommandType.TRANSPORT_GROUP:
                if not self._validate_transport_command(command, world_state):
                    return False
            elif command.type == CommandType.ESCORT_GROUP:
                if not self._validate_escort_command(command, world_state):
                    return False
            elif command.type == CommandType.FIRE_SUPPORT:
                if not self._validate_fire_support_command(command, world_state):
                    return False
            elif command.type == CommandType.DEPLOY_ASSET:
                if not self._validate_deploy_asset_command(command, world_state):
                    return False
            else:
                # For non-spawn commands, validate group exists and is controlled
                if not self._validate_group_controlled(command, world_state):
                    return False

            # Check 4: Validate position bounds
            if not self._validate_position_bounds(command):
                return False

            return True

        except Exception as e:
            logger.error("Exception during command validation: %s", e, exc_info=True)
            return False

    def _validate_group_controlled(self, command: Command, world_state: WorldState) -> bool:
        """
        Validate that the target group exists and is controlled

        Args:
            command: Command to validate
            world_state: Current world state

        Returns:
            True if group is valid and controlled
        """
        group = world_state.get_group_by_id(command.group_id)

        if not group:
            # Allow pending spawns (group_id starts with SPAWN_ or DEPLOY_)
            if command.group_id.startswith('SPAWN_') or command.group_id.startswith('DEPLOY_'):
                logger.debug("Group %s is a pending spawn, allowing command", command.group_id)
                return True

            logger.warning("Group %s not found in world state", command.group_id)
            return False

        if not group.is_controlled:
            logger.warning("Group %s is not controlled", command.group_id)
            return False

        return True

    def _validate_spawn_command(self, command: SpawnSquadCommand, world_state: WorldState) -> bool:
        """
        Validate spawn command

        Args:
            command: Spawn command to validate
            world_state: Current world state

        Returns:
            True if spawn is safe
        """
        side = command.params.get('side')
        unit_classes = command.params.get('unit_classes', [])

        # Validate side
        if side not in ['EAST', 'WEST', 'RESISTANCE']:
            logger.warning("Invalid side for spawn: %s", side)
            return False

        # Validate unit count
        if len(unit_classes) == 0:
            logger.warning("Empty unit_classes for spawn")
            return False

        if len(unit_classes) > 20:  # Prevent spawning huge groups
            logger.warning("Too many units in spawn command: %d (max 20)", len(unit_classes))
            return False

        # Check spawn limits per side
        current_deployment = world_state.ai_deployment.get(side.upper(), 0)
        if current_deployment + len(unit_classes) > self.max_units_per_side:
            logger.warning(
                "Spawn would exceed max units for %s: %d + %d > %d",
                side, current_deployment, len(unit_classes), self.max_units_per_side
            )
            return False

        return True

    def _validate_transport_command(self, command: Command, world_state: WorldState) -> bool:
        """Validate transport_group command"""
        vehicle_group_id = command.params.get('vehicle_group_id') or command.group_id
        passenger_group_id = command.params.get('passenger_group_id')

        vehicle_group = world_state.get_group_by_id(vehicle_group_id)
        passenger_group = world_state.get_group_by_id(passenger_group_id) if passenger_group_id else None

        if not vehicle_group or not passenger_group:
            logger.warning("Transport command groups not found (veh:%s, pax:%s)", vehicle_group_id, passenger_group_id)
            return False

        if not vehicle_group.is_controlled or not passenger_group.is_controlled:
            logger.warning("Transport command requires controlled vehicle and passenger groups")
            return False

        # Basic vehicle type sanity: must not be plain infantry
        if vehicle_group.type in ['infantry', 'unknown', 'player']:
            logger.warning("Transport vehicle group %s is not a vehicle type (%s)", vehicle_group_id, vehicle_group.type)
            return False

        return True

    def _validate_escort_command(self, command: Command, world_state: WorldState) -> bool:
        """Validate escort_group command"""
        escort_group_id = command.params.get('escort_group_id') or command.group_id
        target_group_id = command.params.get('target_group_id')

        escort_group = world_state.get_group_by_id(escort_group_id)
        target_group = world_state.get_group_by_id(target_group_id) if target_group_id else None

        if not escort_group or not target_group:
            logger.warning("Escort command groups not found (escort:%s, target:%s)", escort_group_id, target_group_id)
            return False

        if not escort_group.is_controlled:
            logger.warning("Escort group %s is not controlled", escort_group_id)
            return False

        # Target must be friendly or controlled
        if not target_group.is_controlled and not getattr(target_group, 'is_friendly', False):
            logger.warning("Escort target group %s is not friendly/controlled", target_group_id)
            return False

        return True

    def _validate_fire_support_command(self, command: Command, world_state: WorldState) -> bool:
        """Validate fire_support command"""
        group = world_state.get_group_by_id(command.group_id)

        if not group or not group.is_controlled:
            logger.warning("Fire support group %s not found or not controlled", command.group_id)
            return False

        # Must be a vehicle/air/armor class
        if group.type not in ['air_rotary', 'air_fixed', 'armor', 'mechanized', 'motorized']:
            logger.warning("Fire support group %s is not a vehicle/armor type (%s)", group.id, group.type)
            return False

        return True

    def _validate_deploy_asset_command(self, command: Command, world_state: WorldState) -> bool:
        """Validate deploy_asset command (lightweight, resource pool checked elsewhere)"""
        side = (command.params.get('side') or "").upper()
        asset_type = command.params.get('asset_type')

        if side not in ['EAST', 'WEST', 'RESISTANCE', 'INDEPENDENT']:
            logger.warning("deploy_asset invalid side: %s", side)
            return False

        if not asset_type:
            logger.warning("deploy_asset missing asset_type")
            return False

        if self.state:
            template = self.state.get_asset_template(side, asset_type)
            if not template:
                logger.warning("deploy_asset template not found for %s:%s", side, asset_type)
                return False

            # Check defense_only constraint
            # Defense-only assets can ONLY be deployed during GLOBAL AO Defense Phase
            # (not for individual defend_hq, defend_radiotower objectives)
            defense_only = template.get('defense_only', False)
            if defense_only:
                # Check if AO is in global defense phase (counterattack/defend AO scenario)
                is_ao_defense_phase = self.state.is_ao_defense_phase() if self.state else False

                if not is_ao_defense_phase:
                    # AO Defense Phase is NOT active - reject deployment
                    logger.warning("deploy_asset %s:%s is defense_only but AO Defense Phase is NOT active - REJECTED "
                                 "(defense_only assets require global AO defense, not individual objectives)",
                                 side, asset_type)
                    return False
                else:
                    # Global AO defense is active - allow defense_only assets
                    logger.info("deploy_asset %s:%s is defense_only and AO Defense Phase is ACTIVE - ALLOWED",
                               side, asset_type)

            unit_classes = template.get('unit_classes', [])
            if unit_classes and not command.params.get('unit_classes'):
                command.params['unit_classes'] = unit_classes
            if not self.state.reserve_asset(side, asset_type):
                logger.warning("deploy_asset exceeds pool for %s:%s", side, asset_type)
                return False
        else:
            # If no state, require unit_classes to be provided explicitly
            if not command.params.get('unit_classes'):
                logger.warning("deploy_asset missing unit_classes without state backing")
                return False

        return True

    def _validate_position_bounds(self, command: Command) -> bool:
        """
        Validate that all positions in command are within map bounds

        Args:
            command: Command to validate

        Returns:
            True if all positions are valid
        """
        positions = []

        # Extract positions based on command type
        if command.type == CommandType.SPAWN_SQUAD:
            positions.append(command.params.get('position'))
        elif command.type in [CommandType.MOVE_TO, CommandType.DEFEND_AREA, CommandType.SEEK_AND_DESTROY, CommandType.FIRE_SUPPORT]:
            positions.append(command.params.get('position'))
        elif command.type == CommandType.PATROL_ROUTE:
            positions.extend(command.params.get('waypoints', []))
        elif command.type == CommandType.TRANSPORT_GROUP:
            positions.append(command.params.get('pickup'))
            positions.append(command.params.get('dropoff'))
        elif command.type == CommandType.ESCORT_GROUP:
            # Escort has no fixed position; skip bounds check here
            pass
        elif command.type == CommandType.DEPLOY_ASSET:
            positions.append(command.params.get('position'))

        # Validate each position
        for pos in positions:
            if not pos or len(pos) < 2:
                logger.warning("Invalid position format")
                return False

            x, y = pos[0], pos[1]

            if not (self.map_bounds['min_x'] <= x <= self.map_bounds['max_x']):
                logger.warning("Position X out of bounds: %f (bounds: %d-%d)",
                             x, self.map_bounds['min_x'], self.map_bounds['max_x'])
                return False

            if not (self.map_bounds['min_y'] <= y <= self.map_bounds['max_y']):
                logger.warning("Position Y out of bounds: %f (bounds: %d-%d)",
                             y, self.map_bounds['min_y'], self.map_bounds['max_y'])
                return False

        return True

    def _audit_log(self, action: str, command: Command, reason: str):
        """
        Log command validation action for audit trail

        Args:
            action: "ALLOWED" or "BLOCKED"
            command: Command being validated
            reason: Reason for decision
        """
        if not self.audit_log_enabled:
            return

        logger.info(
            "[AUDIT] %s: %s for group %s - %s",
            action,
            command.type.value,
            command.group_id,
            reason
        )
