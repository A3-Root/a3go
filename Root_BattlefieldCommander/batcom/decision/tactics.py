"""
Task-type driven tactical behaviors
"""

import logging
import math
from typing import Dict, List, Optional
from ..models.objectives import Objective
from ..models.world import WorldState

logger = logging.getLogger('batcom.decision.tactics')


class TacticalBehaviorEngine:
    """Defines tactical behaviors for different objective task types"""

    # Tactical profiles for each task_type
    TACTICAL_PROFILES = {
        'defend_hq': {
            'force_ratio': 3.0,  # 3x defenders vs expected attackers
            'stance': 'defensive',
            'patrol_radius': 150,
            'alert_level': 'high',
            'reinforcement_priority': 100,
            'description': 'Maximum defensive posture - HQ is critical'
        },
        'defend_radiotower': {
            'force_ratio': 2.0,
            'stance': 'defensive',
            'patrol_radius': 200,
            'alert_level': 'high',
            'reinforcement_priority': 80,
            'description': 'High priority - enables force multipliers'
        },
        'defend_gps_jammer': {
            'force_ratio': 2.0,
            'stance': 'defensive',
            'patrol_radius': 200,
            'alert_level': 'high',
            'reinforcement_priority': 80,
            'description': 'High priority - disrupts enemy coordination'
        },
        'defend_mortar_pit': {
            'force_ratio': 1.5,
            'stance': 'defensive',
            'patrol_radius': 150,
            'alert_level': 'medium',
            'reinforcement_priority': 50,
            'description': 'Support asset - defend but not at all costs'
        },
        'defend_supply_depot': {
            'force_ratio': 1.5,
            'stance': 'defensive',
            'patrol_radius': 150,
            'alert_level': 'medium',
            'reinforcement_priority': 50,
            'description': 'Support asset - defend but not at all costs'
        },
        'defend_hmg_tower': {
            'force_ratio': 1.0,
            'stance': 'defensive',
            'patrol_radius': 120,
            'alert_level': 'low',
            'reinforcement_priority': 20,
            'description': 'Low priority - acceptable loss if needed'
        },
        'defend_aa_site': {
            'force_ratio': 1.0,
            'stance': 'defensive',
            'patrol_radius': 150,
            'alert_level': 'low',
            'reinforcement_priority': 20,
            'description': 'Low priority unless air threat detected'
        },
    }

    def get_tactical_guidance(self, objective: Objective, world_state: WorldState) -> str:
        """Generate tactical guidance for an objective based on task_type"""
        task_type = objective.task_type

        if not task_type or task_type not in self.TACTICAL_PROFILES:
            return self._generic_guidance(objective)

        profile = self.TACTICAL_PROFILES[task_type].copy()

        # Calculate enemy threat
        enemy_count = self._count_enemies_near_objective(objective, world_state)
        recommended_defenders = max(1, int(enemy_count * profile['force_ratio']))

        guidance_parts = [
            f"**{objective.objective_name} ({task_type})**",
            f"- Priority: {objective.priority} | Alert: {profile['alert_level']}",
            f"- Tactical: {profile['description']}",
            f"- Enemy presence: ~{enemy_count} units",
            f"- Recommended defenders: {recommended_defenders}+ groups",
        ]

        # Add task-specific tactical notes
        if task_type == 'defend_hq':
            guidance_parts.append("- CRITICAL: This is your command post. Do not let it fall under any circumstances.")
            guidance_parts.append("- Use layered defense with fallback positions.")

        elif task_type in ['defend_radiotower', 'defend_gps_jammer']:
            guidance_parts.append("- Force multiplier: Loss significantly degrades capabilities.")
            guidance_parts.append("- Establish strong perimeter, consider QRF (Quick Reaction Force).")

        elif task_type == 'defend_aa_site':
            air_threat = self._assess_air_threat(world_state)
            if air_threat:
                guidance_parts.append("- Air threat detected! Increase priority.")
                profile['reinforcement_priority'] += 30
            else:
                guidance_parts.append("- No air threat - can be deprioritized if needed.")

        elif task_type in ['defend_mortar_pit', 'defend_supply_depot']:
            guidance_parts.append("- Support asset: Important but not critical.")
            guidance_parts.append("- Can sacrifice if required to defend HQ/radiotower.")

        return "\n".join(guidance_parts)

    def _count_enemies_near_objective(self, objective: Objective, world_state: WorldState) -> int:
        """Count enemy units near objective"""
        if not objective.position:
            return 0

        enemy_count = 0
        obj_pos = objective.position
        radius = objective.radius or 300

        for group in world_state.enemy_groups:
            dist = self._distance_2d(group.position, obj_pos)
            if dist < radius * 2:  # Enemies within 2x objective radius
                enemy_count += group.unit_count

        return enemy_count

    def _assess_air_threat(self, world_state: WorldState) -> bool:
        """Check if enemy air units are present"""
        for group in world_state.enemy_groups:
            if group.type in ['air_rotary', 'air_fixed']:
                return True
        return False

    def _distance_2d(self, pos1: List[float], pos2: List[float]) -> float:
        """Calculate 2D distance between positions"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

    def _generic_guidance(self, objective: Objective) -> str:
        """Generic guidance for objectives without task_type"""
        return f"**{objective.description}** (Priority: {objective.priority})"
