"""
Player and group effectiveness tracking
"""

import logging
import time
from typing import Dict, List, Optional
from ..models.effectiveness import PlayerStats, GroupStats, AOPerformanceData, ObjectiveCompletionEvent
from ..models.world import WorldState

logger = logging.getLogger('batcom.tracking.effectiveness')


class EffectivenessTracker:
    """Tracks player and group effectiveness across AOs"""

    def __init__(self):
        self.current_ao: Optional[AOPerformanceData] = None
        self.ao_history: List[AOPerformanceData] = []
        self.player_lifetime_stats: Dict[str, PlayerStats] = {}
        self.group_lifetime_stats: Dict[str, GroupStats] = {}

    def start_ao(self, ao_id: str, start_time: float):
        """Initialize tracking for new AO"""
        self.current_ao = AOPerformanceData(
            ao_id=ao_id,
            start_time=start_time,
            end_time=0.0,
            duration=0.0
        )
        logger.info(f"Started tracking AO: {ao_id}")

    def record_objective_completion(self, objective_id: str, objective_type: str,
                                    player_uid: str, player_name: str, group_id: str,
                                    completion_method: str, nearby_players: list = None):
        """
        Record an objective completion event

        Args:
            objective_id: ID of the objective (e.g., "obj_hq_1")
            objective_type: task_type (defend_hq, defend_radiotower, etc.)
            player_uid: UID of player who completed it
            player_name: Name of player
            group_id: Player's group ID
            completion_method: How it was completed ("killed", "captured", "destroyed", "disabled", "neutralized")
            nearby_players: List of [uid, name, group_id] for players within proximity (optional)
        """
        if not self.current_ao:
            logger.warning("Cannot record objective completion - no active AO")
            return

        # Ensure player stats exist
        if player_uid not in self.current_ao.player_stats:
            self.current_ao.player_stats[player_uid] = PlayerStats(
                uid=player_uid,
                name=player_name,
                group_id=group_id
            )

        stats = self.current_ao.player_stats[player_uid]

        # Create completion event
        event = ObjectiveCompletionEvent(
            objective_id=objective_id,
            objective_type=objective_type,
            player_uid=player_uid,
            player_name=player_name,
            group_id=group_id,
            timestamp=time.time(),
            completion_method=completion_method
        )
        stats.objective_completions.append(event)

        # Track if this is a high-value event (HQ or HVT)
        is_high_value_event = False

        # Update specific metrics based on objective type and completion method
        if objective_type == "defend_hq" or "hq" in objective_id.lower():
            if completion_method == "captured":
                stats.commander_captures += 1
                stats.objectives_cleared += 1
                is_high_value_event = True
                logger.info(f"Player {player_name} CAPTURED HQ commander alive (+40 pts)")
            else:
                stats.commander_kills += 1
                stats.objectives_cleared += 1
                is_high_value_event = True
                logger.info(f"Player {player_name} eliminated HQ commander (+30 pts)")

        elif objective_type in ["defend_hvt", "hvt"] or "hvt" in objective_id.lower():
            if completion_method == "captured":
                stats.hvt_captures += 1
                stats.objectives_cleared += 1
                is_high_value_event = True
                logger.info(f"Player {player_name} CAPTURED HVT alive (+35 pts)")
            else:
                stats.hvt_eliminations += 1
                stats.objectives_cleared += 1
                is_high_value_event = True
                logger.info(f"Player {player_name} eliminated HVT (+25 pts)")

        elif objective_type in ["defend_radiotower", "defend_gps_jammer"]:
            stats.high_value_destructions += 1
            stats.objectives_cleared += 1
            logger.info(f"Player {player_name} {completion_method} {objective_type} (+20 pts)")

        elif objective_type in ["defend_supply_depot", "supply_depot"]:
            stats.objectives_captured += 1
            stats.objectives_cleared += 1
            logger.info(f"Player {player_name} captured supply depot (+15 pts)")

        # For mortar pits, AA sites, HMG towers - these are typically not directly tracked
        # but handled through proximity and kill tracking

        # Award proximity bonuses to nearby players (excluding the completer)
        if is_high_value_event and nearby_players:
            for nearby in nearby_players:
                nearby_uid = nearby[0]
                nearby_name = nearby[1]
                nearby_group = nearby[2]

                if nearby_uid == player_uid:
                    continue  # Skip the player who completed it

                # Ensure nearby player stats exist
                if nearby_uid not in self.current_ao.player_stats:
                    self.current_ao.player_stats[nearby_uid] = PlayerStats(
                        uid=nearby_uid,
                        name=nearby_name,
                        group_id=nearby_group
                    )

                self.current_ao.player_stats[nearby_uid].proximity_bonuses += 1
                logger.info(f"Player {nearby_name} awarded proximity bonus for being near {completion_method} (+10 pts)")

        # Update group stats if this was a high-value objective
        if group_id in self.current_ao.group_stats:
            if objective_type in ["defend_hq", "defend_hvt", "defend_radiotower", "defend_gps_jammer", "defend_supply_depot"]:
                self.current_ao.group_stats[group_id].objectives_cleared += 1

    def update_from_world(self, world_state: WorldState, casualty_data: Dict, contribution_data: Dict):
        """Update effectiveness tracking from world state"""
        if not self.current_ao:
            return

        # Update player stats from casualty data
        player_kills = casualty_data.get('player_kills', {})
        for uid, kills in player_kills.items():
            if uid not in self.current_ao.player_stats:
                player = self._find_player_by_uid(world_state, uid)
                if player:
                    self.current_ao.player_stats[uid] = PlayerStats(
                        uid=uid,
                        name=player.name,
                        group_id=player.group_id
                    )

            if uid in self.current_ao.player_stats:
                self.current_ao.player_stats[uid].ai_kills = kills

        # Update objective contributions (proximity-based)
        for uid, contrib in contribution_data.items():
            if uid in self.current_ao.player_stats:
                objectives = contrib.get('objectives', [])
                self.current_ao.player_stats[uid].objective_contributions = objectives

        # Update group stats
        for group in world_state.controlled_groups:
            if group.id not in self.current_ao.group_stats:
                self.current_ao.group_stats[group.id] = GroupStats(
                    group_id=group.id,
                    side=group.side,
                    initial_strength=group.unit_count,
                    current_strength=group.unit_count
                )
            else:
                stats = self.current_ao.group_stats[group.id]
                stats.current_strength = group.unit_count
                stats.casualties_taken = stats.initial_strength - group.unit_count

    def end_ao(self, end_time: float) -> Optional[AOPerformanceData]:
        """Finalize AO tracking and designate HVTs"""
        if not self.current_ao:
            logger.warning("No active AO to end")
            return None

        self.current_ao.end_time = end_time
        self.current_ao.duration = end_time - self.current_ao.start_time

        # Designate HVTs based on performance
        self._designate_hvts()

        # Archive this AO
        self.ao_history.append(self.current_ao)
        result = self.current_ao
        self.current_ao = None

        logger.info(f"AO {result.ao_id} ended - Duration: {result.duration}s, HVT Players: {len(result.hvt_players)}")
        return result

    def _designate_hvts(self):
        """Designate top-performing players/groups as HVTs"""
        if not self.current_ao:
            return

        # Sort players by threat score
        player_scores = [
            (uid, stats.threat_score())
            for uid, stats in self.current_ao.player_stats.items()
        ]
        player_scores.sort(key=lambda x: x[1], reverse=True)

        # Top 20% or minimum 2 players become HVTs
        num_hvts = max(2, len(player_scores) // 5)
        self.current_ao.hvt_players = [uid for uid, score in player_scores[:num_hvts] if score > 10]

        # Sort groups by effectiveness
        group_scores = [
            (gid, stats.effectiveness_ratio())
            for gid, stats in self.current_ao.group_stats.items()
        ]
        group_scores.sort(key=lambda x: x[1], reverse=True)

        # Top 30% of groups become HVT groups
        num_hvt_groups = max(1, len(group_scores) // 3)
        self.current_ao.hvt_groups = [gid for gid, score in group_scores[:num_hvt_groups] if score > 5]

        logger.info(f"Designated {len(self.current_ao.hvt_players)} HVT players and {len(self.current_ao.hvt_groups)} HVT groups")

    def get_hvt_context(self) -> str:
        """Generate HVT context for LLM"""
        if not self.ao_history:
            return ""

        last_ao = self.ao_history[-1]
        if not last_ao.hvt_players and not last_ao.hvt_groups:
            return ""

        context_parts = ["**HIGH VALUE TARGETS (From Previous AO):**\n"]

        if last_ao.hvt_players:
            context_parts.append("Players to prioritize:")
            for uid in last_ao.hvt_players[:5]:  # Limit to top 5 for token efficiency
                if uid in last_ao.player_stats:
                    stats = last_ao.player_stats[uid]
                    context_parts.append(
                        f"- {stats.name} (Group: {stats.group_id}): "
                        f"{stats.objectives_cleared} obj, {stats.ai_kills} kills [THREAT: {stats.threat_score():.0f}]"
                    )

        if last_ao.hvt_groups:
            context_parts.append("\nGroups to prioritize:")
            for gid in last_ao.hvt_groups[:3]:  # Top 3 groups
                if gid in last_ao.group_stats:
                    stats = last_ao.group_stats[gid]
                    context_parts.append(
                        f"- {gid}: {stats.total_kills} kills, {stats.objectives_cleared} obj cleared"
                    )

        context_parts.append("\n*Tactical guidance: Be extra aggressive and cautious against HVTs. Allocate additional resources.*\n")

        return "\n".join(context_parts)

    def _find_player_by_uid(self, world_state: WorldState, uid: str) -> Optional[object]:
        """Find player object by UID"""
        for player in world_state.players:
            if player.uid == uid:
                return player
        return None
