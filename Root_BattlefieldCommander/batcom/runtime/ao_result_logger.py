"""
AO Result Logger

Logs complete AO results including all orders, objectives, forces, threat levels,
and outcomes to a dedicated log file for historical analysis and learning.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger('batcom.runtime.ao_result_logger')


class AOResultLogger:
    """
    Logs complete AO results for historical analysis and commander learning
    """

    def __init__(self, log_dir: str = "@BATCOM"):
        """
        Initialize AO result logger

        Args:
            log_dir: Directory for AO result logs (default: @BATCOM/llm_calls)
        """
        # Use same directory as API logs
        self.log_dir = os.path.join(log_dir, "llm_calls")
        self.current_ao_file: Optional[str] = None
        self.current_ao_data: Dict[str, Any] = {}

        # Ensure log directory exists with fallback for Linux compatibility
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir, exist_ok=True)
                logger.info(f'Created AO result log directory: {self.log_dir}')
            except (OSError, PermissionError) as e:
                # Fallback to simpler path if @BATCOM fails (Linux compatibility)
                logger.warning(f'Failed to create AO result log directory {self.log_dir}: {e}')
                try:
                    fallback_dir = os.path.join(os.getcwd(), "batcom_logs", "llm_calls")
                    self.log_dir = fallback_dir
                    os.makedirs(self.log_dir, exist_ok=True)
                    logger.info(f'Using fallback AO log directory: {self.log_dir}')
                except Exception as fallback_error:
                    # Last resort: temp directory
                    import tempfile
                    self.log_dir = os.path.join(tempfile.gettempdir(), "batcom_logs", "llm_calls")
                    os.makedirs(self.log_dir, exist_ok=True)
                    logger.info(f'Using temp AO log directory: {self.log_dir}')

    def start_ao(self, ao_id: str, ao_number: int, map_name: str, mission_name: str):
        """
        Start logging for a new AO

        Args:
            ao_id: AO identifier
            ao_number: AO sequence number
            map_name: Map name
            mission_name: Mission name
        """
        # Generate filename: aoresult.<aonumber>.<mapname>.<missionname>.<timestamp>.log
        timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        filename = f'aoresult.{ao_number}.{map_name}.{mission_name}.{timestamp}.log'
        self.current_ao_file = os.path.join(self.log_dir, filename)

        # Initialize AO data structure
        self.current_ao_data = {
            'ao_id': ao_id,
            'ao_number': ao_number,
            'map_name': map_name,
            'mission_name': mission_name,
            'start_time': datetime.now().isoformat(),
            'start_timestamp': datetime.now().timestamp(),
            'objectives': [],
            'decision_cycles': [],
            'initial_forces': {},
            'final_forces': {},
            'threat_levels': [],
            'deployed_assets': [],
            'outcome': 'UNKNOWN',
            'lessons_learned': [],
            # Tactical analysis
            'first_objective_targeted': None,
            'first_objective_lost': None,
            'damage_hotspots': [],  # Areas where most enemy casualties occurred
            'longest_fight_location': None,
            'fight_durations': {},  # objective_id -> duration_seconds
            'objective_engagement_order': [],  # Chronological order of objective engagements
            'objective_loss_order': [],  # Chronological order of objectives lost
            # MVP tracking
            'mvp_player': None,
            'mvp_squad': None,
            'player_contributions': {},  # player_id -> {'kills': N, 'objectives_secured': [...]}
            'squad_contributions': {}  # squad_id -> {'kills': N, 'objectives_secured': [...]}
        }

        logger.info(f'AO result logging started: {filename}')

    def record_initial_forces(self, controlled_groups: int, controlled_units: int,
                             allied_groups: int, allied_units: int,
                             enemy_groups: int, enemy_units: int):
        """Record initial force composition"""
        if not self.current_ao_data:
            return

        self.current_ao_data['initial_forces'] = {
            'controlled_groups': controlled_groups,
            'controlled_units': controlled_units,
            'allied_groups': allied_groups,
            'allied_units': allied_units,
            'enemy_groups': enemy_groups,
            'enemy_units': enemy_units,
            'force_ratio': round((controlled_units + allied_units) / enemy_units, 2) if enemy_units > 0 else 999
        }

    def record_objective(self, obj_id: str, description: str, priority: int,
                        position: List[float] = None, task_type: str = None):
        """Record an objective"""
        if not self.current_ao_data:
            return

        obj_entry = {
            'id': obj_id,
            'description': description,
            'priority': priority,
            'position': position,
            'task_type': task_type,
            'state_changes': []  # Track state changes over time
        }
        self.current_ao_data['objectives'].append(obj_entry)

    def record_decision_cycle(self, cycle: int, mission_time: float,
                            order_count: int, order_summary: List[str],
                            commentary: str, threat_level: str,
                            current_forces: Dict[str, int]):
        """Record a decision cycle"""
        if not self.current_ao_data:
            return

        cycle_entry = {
            'cycle': cycle,
            'mission_time': round(mission_time, 1),
            'timestamp': datetime.now().isoformat(),
            'order_count': order_count,
            'order_summary': order_summary,
            'commentary': commentary,
            'threat_level': threat_level,
            'forces_at_cycle': current_forces
        }
        self.current_ao_data['decision_cycles'].append(cycle_entry)

        # Track threat levels over time
        self.current_ao_data['threat_levels'].append({
            'cycle': cycle,
            'mission_time': round(mission_time, 1),
            'level': threat_level
        })

    def record_deployed_asset(self, cycle: int, mission_time: float,
                             side: str, asset_type: str, position: List[float]):
        """Record an asset deployment"""
        if not self.current_ao_data:
            return

        self.current_ao_data['deployed_assets'].append({
            'cycle': cycle,
            'mission_time': round(mission_time, 1),
            'side': side,
            'asset_type': asset_type,
            'position': position
        })

    def record_final_forces(self, controlled_groups: int, controlled_units: int,
                          allied_groups: int, allied_units: int,
                          enemy_groups: int, enemy_units: int):
        """Record final force composition"""
        if not self.current_ao_data:
            return

        self.current_ao_data['final_forces'] = {
            'controlled_groups': controlled_groups,
            'controlled_units': controlled_units,
            'allied_groups': allied_groups,
            'allied_units': allied_units,
            'enemy_groups': enemy_groups,
            'enemy_units': enemy_units,
            'force_ratio': round((controlled_units + allied_units) / enemy_units, 2) if enemy_units > 0 else 999
        }

        # Calculate losses
        if self.current_ao_data.get('initial_forces'):
            initial = self.current_ao_data['initial_forces']
            final = self.current_ao_data['final_forces']
            self.current_ao_data['casualties'] = {
                'controlled_units_lost': initial['controlled_units'] - final['controlled_units'],
                'allied_units_lost': initial['allied_units'] - final['allied_units'],
                'enemy_units_destroyed': initial['enemy_units'] - final['enemy_units'],
                'loss_ratio': round(
                    (initial['enemy_units'] - final['enemy_units']) /
                    max(1, (initial['controlled_units'] - final['controlled_units']) +
                    (initial['allied_units'] - final['allied_units'])),
                    2
                )
            }

    def record_outcome(self, outcome: str, objectives_completed: int, objectives_total: int):
        """Record AO outcome"""
        if not self.current_ao_data:
            return

        self.current_ao_data['outcome'] = outcome
        self.current_ao_data['objectives_completed'] = objectives_completed
        self.current_ao_data['objectives_total'] = objectives_total
        self.current_ao_data['completion_rate'] = round(objectives_completed / objectives_total * 100, 1) if objectives_total > 0 else 0.0

    def add_lesson_learned(self, lesson: str):
        """Add a lesson learned from this AO"""
        if not self.current_ao_data:
            return

        self.current_ao_data['lessons_learned'].append({
            'timestamp': datetime.now().isoformat(),
            'lesson': lesson
        })

    def record_objective_engagement(self, obj_id: str, cycle: int, mission_time: float):
        """Record when an objective was first engaged/targeted"""
        if not self.current_ao_data:
            return

        # Track first objective targeted
        if not self.current_ao_data['first_objective_targeted']:
            self.current_ao_data['first_objective_targeted'] = {
                'objective_id': obj_id,
                'cycle': cycle,
                'mission_time': round(mission_time, 1)
            }

        # Add to engagement order if not already recorded
        if obj_id not in [e['objective_id'] for e in self.current_ao_data['objective_engagement_order']]:
            self.current_ao_data['objective_engagement_order'].append({
                'objective_id': obj_id,
                'cycle': cycle,
                'mission_time': round(mission_time, 1),
                'timestamp': datetime.now().isoformat()
            })

    def record_objective_lost(self, obj_id: str, cycle: int, mission_time: float):
        """Record when an objective was lost"""
        if not self.current_ao_data:
            return

        # Track first objective lost
        if not self.current_ao_data['first_objective_lost']:
            self.current_ao_data['first_objective_lost'] = {
                'objective_id': obj_id,
                'cycle': cycle,
                'mission_time': round(mission_time, 1)
            }

        # Add to loss order
        self.current_ao_data['objective_loss_order'].append({
            'objective_id': obj_id,
            'cycle': cycle,
            'mission_time': round(mission_time, 1),
            'timestamp': datetime.now().isoformat()
        })

    def record_damage_hotspot(self, position: List[float], enemy_casualties: int, area_description: str = None):
        """Record a damage hotspot where significant enemy casualties occurred"""
        if not self.current_ao_data:
            return

        self.current_ao_data['damage_hotspots'].append({
            'position': position,
            'enemy_casualties': enemy_casualties,
            'area_description': area_description or 'Unknown',
            'timestamp': datetime.now().isoformat()
        })

    def record_fight_duration(self, obj_id: str, duration_seconds: float):
        """Record how long a fight lasted at an objective"""
        if not self.current_ao_data:
            return

        self.current_ao_data['fight_durations'][obj_id] = round(duration_seconds, 1)

        # Update longest fight location
        current_longest = self.current_ao_data.get('longest_fight_location')
        if not current_longest or duration_seconds > current_longest.get('duration', 0):
            self.current_ao_data['longest_fight_location'] = {
                'objective_id': obj_id,
                'duration_seconds': round(duration_seconds, 1)
            }

    def record_player_contribution(self, player_id: str, player_name: str, kills: int = 0, objective_secured: str = None):
        """Record player contributions for MVP tracking"""
        if not self.current_ao_data:
            return

        if player_id not in self.current_ao_data['player_contributions']:
            self.current_ao_data['player_contributions'][player_id] = {
                'name': player_name,
                'kills': 0,
                'objectives_secured': []
            }

        contrib = self.current_ao_data['player_contributions'][player_id]
        contrib['kills'] += kills
        if objective_secured and objective_secured not in contrib['objectives_secured']:
            contrib['objectives_secured'].append(objective_secured)

    def record_squad_contribution(self, squad_id: str, kills: int = 0, objective_secured: str = None):
        """Record squad contributions for MVP tracking"""
        if not self.current_ao_data:
            return

        if squad_id not in self.current_ao_data['squad_contributions']:
            self.current_ao_data['squad_contributions'][squad_id] = {
                'kills': 0,
                'objectives_secured': []
            }

        contrib = self.current_ao_data['squad_contributions'][squad_id]
        contrib['kills'] += kills
        if objective_secured and objective_secured not in contrib['objectives_secured']:
            contrib['objectives_secured'].append(objective_secured)

    def calculate_mvp(self):
        """Calculate MVP player and squad based on contributions"""
        if not self.current_ao_data:
            return

        # Calculate MVP player
        players = self.current_ao_data['player_contributions']
        if players:
            mvp_player_id = max(players, key=lambda p: players[p]['kills'] + len(players[p]['objectives_secured']) * 5)
            self.current_ao_data['mvp_player'] = {
                'player_id': mvp_player_id,
                'name': players[mvp_player_id]['name'],
                'kills': players[mvp_player_id]['kills'],
                'objectives_secured': len(players[mvp_player_id]['objectives_secured']),
                'score': players[mvp_player_id]['kills'] + len(players[mvp_player_id]['objectives_secured']) * 5
            }

        # Calculate MVP squad
        squads = self.current_ao_data['squad_contributions']
        if squads:
            mvp_squad_id = max(squads, key=lambda s: squads[s]['kills'] + len(squads[s]['objectives_secured']) * 5)
            self.current_ao_data['mvp_squad'] = {
                'squad_id': mvp_squad_id,
                'kills': squads[mvp_squad_id]['kills'],
                'objectives_secured': len(squads[mvp_squad_id]['objectives_secured']),
                'score': squads[mvp_squad_id]['kills'] + len(squads[mvp_squad_id]['objectives_secured']) * 5
            }

    def finalize_ao(self):
        """Finalize and write AO result log"""
        if not self.current_ao_file or not self.current_ao_data:
            logger.warning('No AO data to finalize')
            return None

        # Calculate MVP before finalizing
        self.calculate_mvp()

        # Add end time
        self.current_ao_data['end_time'] = datetime.now().isoformat()
        self.current_ao_data['end_timestamp'] = datetime.now().timestamp()

        # Calculate duration
        if 'start_timestamp' in self.current_ao_data:
            duration_seconds = self.current_ao_data['end_timestamp'] - self.current_ao_data['start_timestamp']
            self.current_ao_data['duration_seconds'] = round(duration_seconds, 1)

        # Write to file
        try:
            with open(self.current_ao_file, 'w', encoding='utf-8') as f:
                # Write header
                f.write('='*80 + '\n')
                f.write(f'AO RESULT LOG - {self.current_ao_data["ao_id"]}\n')
                f.write('='*80 + '\n')
                f.write(f'Map: {self.current_ao_data["map_name"]}\n')
                f.write(f'Mission: {self.current_ao_data["mission_name"]}\n')
                f.write(f'AO Number: {self.current_ao_data["ao_number"]}\n')
                f.write(f'Started: {self.current_ao_data["start_time"]}\n')
                f.write(f'Ended: {self.current_ao_data["end_time"]}\n')
                f.write(f'Duration: {self.current_ao_data.get("duration_seconds", 0):.1f}s\n')
                f.write(f'Outcome: {self.current_ao_data["outcome"]}\n')
                f.write('='*80 + '\n\n')

                # Write complete JSON data for machine parsing
                f.write('COMPLETE AO DATA (JSON):\n')
                f.write('-'*80 + '\n')
                f.write(json.dumps(self.current_ao_data, indent=2, ensure_ascii=False))
                f.write('\n' + '-'*80 + '\n\n')

                # Write human-readable summary
                f.write('SUMMARY:\n')
                f.write('-'*80 + '\n')
                f.write(f'Total Decision Cycles: {len(self.current_ao_data["decision_cycles"])}\n')
                f.write(f'Total Orders Issued: {sum(c["order_count"] for c in self.current_ao_data["decision_cycles"])}\n')
                f.write(f'Assets Deployed: {len(self.current_ao_data["deployed_assets"])}\n')
                f.write(f'Objectives: {self.current_ao_data.get("objectives_completed", 0)}/{self.current_ao_data.get("objectives_total", 0)} completed\n')

                if self.current_ao_data.get('casualties'):
                    cas = self.current_ao_data['casualties']
                    f.write(f'\nCASUALTIES:\n')
                    f.write(f'  Friendly losses: {cas["controlled_units_lost"]} controlled, {cas["allied_units_lost"]} allied\n')
                    f.write(f'  Enemy destroyed: {cas["enemy_units_destroyed"]}\n')
                    f.write(f'  Loss ratio: {cas["loss_ratio"]:.2f} (enemy/friendly)\n')

                if self.current_ao_data['lessons_learned']:
                    f.write(f'\nLESSONS LEARNED ({len(self.current_ao_data["lessons_learned"])}):\n')
                    for i, lesson in enumerate(self.current_ao_data['lessons_learned'], 1):
                        f.write(f'  {i}. {lesson["lesson"]}\n')

                f.write('='*80 + '\n')

            logger.info(f'AO result log finalized: {self.current_ao_file}')

            # Return copy of data for next commander
            result_data = dict(self.current_ao_data)

            # Reset state
            self.current_ao_file = None
            self.current_ao_data = {}

            return result_data

        except Exception as e:
            logger.error(f'Failed to write AO result log: {e}', exc_info=True)
            return None

    def get_current_ao_file(self) -> Optional[str]:
        """Get current AO result log file path"""
        return self.current_ao_file
