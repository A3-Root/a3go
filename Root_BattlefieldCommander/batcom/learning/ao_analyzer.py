"""
AO outcome analysis and learning
"""

import logging
from typing import Dict, List
from ..models.effectiveness import AOPerformanceData

logger = logging.getLogger('batcom.learning.ao_analyzer')


class AOAnalyzer:
    """Analyzes AO outcomes to improve AI performance"""

    def analyze_ao(self, ao_data: AOPerformanceData) -> Dict[str, any]:
        """Analyze AO outcome and generate insights"""

        analysis = {
            "outcome": self._determine_outcome(ao_data),
            "ai_effectiveness": self._calculate_ai_effectiveness(ao_data),
            "key_failures": self._identify_failures(ao_data),
            "tactical_insights": self._generate_insights(ao_data)
        }

        logger.info(f"AO Analysis - Outcome: {analysis['outcome']}, AI Effectiveness: {analysis['ai_effectiveness']:.1f}%")

        return analysis

    def _determine_outcome(self, ao_data: AOPerformanceData) -> str:
        """Determine if AI won, lost, or stalemate"""
        if ao_data.objectives_lost > ao_data.objectives_held:
            return "DEFEAT"
        elif ao_data.objectives_held > ao_data.objectives_lost:
            return "VICTORY"
        else:
            # Use casualty ratios
            if ao_data.blufor_casualties > ao_data.ai_casualties * 2:
                return "VICTORY"
            elif ao_data.ai_casualties > ao_data.blufor_casualties * 2:
                return "DEFEAT"
            return "STALEMATE"

    def _calculate_ai_effectiveness(self, ao_data: AOPerformanceData) -> float:
        """Calculate AI effectiveness score (0-100)"""
        # Faster AO = worse for AI
        speed_penalty = max(0, 100 - (ao_data.duration / 60))  # Penalty if under 100 minutes

        # More AI losses = worse
        casualty_ratio = 50  # Base
        if ao_data.blufor_casualties > 0:
            ratio = ao_data.ai_casualties / ao_data.blufor_casualties
            casualty_ratio = max(0, 100 - (ratio * 50))

        # Objectives lost = bad
        obj_penalty = ao_data.objectives_lost * 20

        effectiveness = max(0, 100 - speed_penalty - obj_penalty + casualty_ratio)
        return min(100, effectiveness)

    def _identify_failures(self, ao_data: AOPerformanceData) -> List[str]:
        """Identify key failures"""
        failures = []

        if ao_data.objectives_lost > 2:
            failures.append("Failed to defend multiple objectives")

        if ao_data.duration < 1800:  # Less than 30 minutes
            failures.append("AO ended too quickly - insufficient resistance")

        if ao_data.ai_casualties > ao_data.blufor_casualties * 3:
            failures.append("Excessive casualties - poor tactical decisions")

        return failures

    def _generate_insights(self, ao_data: AOPerformanceData) -> List[str]:
        """Generate tactical insights for next AO"""
        insights = []

        # Analyze HVT effectiveness
        if ao_data.hvt_players:
            hvt_impact = sum(
                ao_data.player_stats[uid].objectives_cleared
                for uid in ao_data.hvt_players
                if uid in ao_data.player_stats
            )
            if hvt_impact > len(ao_data.hvt_players) * 2:
                insights.append("HVT players highly effective - increase priority on neutralizing them")

        # Analyze objective defense patterns
        # (Would analyze which task_types were lost first)

        insights.append(f"AO Duration: {ao_data.duration/60:.1f} min - Adjust pacing")

        return insights
