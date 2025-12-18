"""
World scanner - processes world state snapshots from Arma
"""

import logging
from typing import Dict, Any, List
from ..models.world import WorldState, Group, Player, Objective, KnownEnemy, UnitEquipment

logger = logging.getLogger('batcom.world.scanner')


class WorldScanner:
    """
    Processes world state snapshots from SQF and maintains current world state
    """

    def __init__(self, state_manager=None):
        self.current_state: WorldState = None
        self.snapshot_count = 0
        self.state_manager = state_manager  # Reference to state manager for effectiveness tracking

    def ingest_snapshot(self, snapshot_data: Dict[str, Any]) -> WorldState:
        """
        Process a world state snapshot from SQF

        Args:
            snapshot_data: Dictionary containing world state data from SQF

        Returns:
            WorldState object

        Raises:
            ValueError: If snapshot data is invalid
        """
        try:
            logger.debug('Processing world snapshot')

            # Parse groups
            groups = []
            for group_data in snapshot_data.get('groups', []):
                # Parse known enemies
                known_enemies = []
                for enemy_data in group_data.get('known_enemies', []):
                    known_enemies.append(KnownEnemy(
                        id=enemy_data['id'],
                        side=enemy_data['side'],
                        type=enemy_data['type'],
                        position=enemy_data['position'],
                        unit_count=enemy_data['unit_count'],
                        knowledge=enemy_data['knowledge'],
                        last_seen=enemy_data['last_seen']
                    ))

                # Parse unit equipment
                units_equipment = []
                for equipment_data in group_data.get('units_equipment', []):
                    units_equipment.append(UnitEquipment(
                        has_nvg=equipment_data.get('has_nvg', False),
                        has_flashlight=equipment_data.get('has_flashlight', False),
                        primary_weapon=equipment_data.get('primary_weapon', '')
                    ))

                groups.append(Group(
                    id=group_data['id'],
                    side=group_data['side'],
                    type=group_data['type'],
                    position=group_data['position'],
                    unit_count=group_data['unit_count'],
                    casualties=group_data.get('casualties', 0),
                    behaviour=group_data.get('behaviour', 'AWARE'),
                    combat_mode=group_data.get('combat_mode', 'YELLOW'),
                    speed_mode=group_data.get('speed_mode', 'NORMAL'),
                    formation=group_data.get('formation', 'WEDGE'),
                    current_waypoint=group_data.get('current_waypoint', 0),
                    waypoint_count=group_data.get('waypoint_count', 0),
                    is_controlled=group_data.get('is_controlled', False),
                    is_player_group=group_data.get('is_player_group', False),
                    is_friendly=group_data.get('is_friendly', False),
                    in_combat=group_data.get('in_combat', False),
                    current_waypoint_type=group_data.get('current_waypoint_type', ''),
                    current_waypoint_pos=group_data.get('current_waypoint_pos', []),
                    known_enemies=known_enemies,
                    knowledge=group_data.get('knowledge', 0.0),
                    units_equipment=units_equipment,
                    avg_night_capability=group_data.get('avg_night_capability', 0.0)
                ))

            # Parse players
            players = []
            for player_data in snapshot_data.get('players', []):
                players.append(Player(
                    name=player_data['name'],
                    uid=player_data['uid'],
                    side=player_data['side'],
                    group_id=player_data['group_id'],
                    position=player_data['position'],
                    is_in_vehicle=player_data.get('is_in_vehicle', False),
                    vehicle_type=player_data.get('vehicle_type', ''),
                    behaviour=player_data.get('behaviour', 'AWARE'),
                    damage=player_data.get('damage', 0.0),
                    is_hvt=player_data.get('is_hvt', False),
                    hvt_reason=player_data.get('hvt_reason', ''),
                    threat_score=player_data.get('threat_score', 0.0)
                ))

            # Parse objectives
            objectives = []
            for obj_data in snapshot_data.get('objectives', []):
                objectives.append(Objective(
                    id=obj_data['id'],
                    position=obj_data['position'],
                    radius=obj_data['radius'],
                    shape=obj_data['shape'],
                    type=obj_data['type'],
                    text=obj_data['text'],
                    color=obj_data['color'],
                    friendly_count=obj_data.get('friendly_count', 0),
                    enemy_count=obj_data.get('enemy_count', 0)
                ))

            # Create world state
            world_state = WorldState(
                timestamp=snapshot_data.get('timestamp', 0.0),
                daytime=snapshot_data.get('daytime', 12.0),
                weather=snapshot_data.get('weather', [0.0, 0.0, 0.0, [0.0, 0.0]]),
                world_name=snapshot_data.get('world_name', 'unknown'),
                mission_name=snapshot_data.get('mission_name', 'unknown'),
                groups=groups,
                players=players,
                objectives=objectives,
                mission_variables=snapshot_data.get('mission_variables', {}),
                mission_intent=snapshot_data.get('mission_intent', ''),
                friendly_sides=snapshot_data.get('friendly_sides', []),
                controlled_sides=snapshot_data.get('controlled_sides', []),
                mission_time=snapshot_data.get('mission_time', 0.0),
                is_night=snapshot_data.get('is_night', False),
                ai_deployment=snapshot_data.get('ai_deployment', {})
            )

            self.current_state = world_state
            self.snapshot_count += 1

            # Update effectiveness tracking if AO is active
            if self.state_manager and hasattr(self.state_manager, 'ao_active') and self.state_manager.ao_active:
                casualty_data = snapshot_data.get('casualty_data', {})
                contribution_data = snapshot_data.get('contribution_data', {})
                self.state_manager.effectiveness_tracker.update_from_world(
                    world_state,
                    casualty_data,
                    contribution_data
                )

            logger.info(
                'Snapshot #%d processed: %d groups (%d controlled), %d players, %d objectives',
                self.snapshot_count,
                len(groups),
                len(world_state.controlled_groups),
                len(players),
                len(objectives)
            )

            return world_state

        except Exception as e:
            logger.exception('Failed to process snapshot')
            raise ValueError(f'Invalid snapshot data: {e}')

    def get_current_state(self) -> WorldState:
        """Get the current world state"""
        return self.current_state

    def has_state(self) -> bool:
        """Check if we have received at least one snapshot"""
        return self.current_state is not None
