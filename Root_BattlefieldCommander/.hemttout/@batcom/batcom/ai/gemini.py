"""
Google Gemini LLM client for tactical command generation
"""

import os
import time
import json
import logging
import re
from typing import Dict, List, Optional, Any

logger = logging.getLogger('batcom.ai.gemini')


class RateLimiter:
    """
    Rate limiter to prevent excessive LLM API calls
    """

    def __init__(self, min_interval: float = 10.0):
        """
        Initialize rate limiter

        Args:
            min_interval: Minimum seconds between API calls (default 10.0)
        """
        self.min_interval = min_interval
        self.last_call_time: float = 0.0

    def should_call_llm(self, current_time: float) -> bool:
        """
        Check if enough time has passed to make another LLM call

        Args:
            current_time: Current mission time in seconds

        Returns:
            True if enough time has passed since last call
        """
        if current_time - self.last_call_time >= self.min_interval:
            self.last_call_time = current_time
            return True
        return False

    def reset(self):
        """Reset the rate limiter"""
        self.last_call_time = 0.0


class GeminiClient:
    """
    Google Gemini API client for tactical command generation
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: int = 30):
        """
        Initialize Gemini client

        Args:
            api_key: Google Gemini API key
            model: Model name (default "gemini-2.5-flash")
            timeout: Request timeout in seconds (default 30)

        Raises:
            ImportError: If google-generativeai package is not installed
            ValueError: If API key is empty
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Please install with: pip install google-generativeai"
            )

        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.genai = genai
        self.types = types

        # Cache system prompt so subsequent calls send only world state/order context
        self._cached_system_prompt = None
        self._cached_system_bound = False

        # Initialize client
        self.client = genai.Client(api_key=api_key)

        logger.info("Gemini client initialized (model: %s, timeout: %ds)", model, timeout)

    def generate_tactical_orders(
        self,
        world_state: Dict[str, Any],
        mission_intent: str,
        objectives: List[Dict[str, Any]],
        system_prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate tactical orders using Gemini LLM

        Args:
            world_state: Current world state dictionary
            mission_intent: Mission intent/description
            objectives: List of mission objectives
            system_prompt: System prompt with constraints

        Returns:
            Dictionary with 'orders', 'commentary', and 'order_summary' fields, or None on failure
        """
        try:
            # Format the prompt
            prompt = self._format_prompt(world_state, mission_intent, objectives)

            logger.debug("Calling Gemini API (model: %s)", self.model)

            # Cache system prompt on first use; subsequent calls only send dynamic context
            parts = []
            if not self._cached_system_bound or self._cached_system_prompt != system_prompt:
                self._cached_system_prompt = system_prompt
                self._cached_system_bound = True
                parts.append(self.types.Part(text=system_prompt))
                logger.debug("Gemini system prompt cached for reuse")

            parts.append(self.types.Part(text=prompt))

            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    self.types.Content(
                        role="user",
                        parts=parts
                    )
                ],
                config=self.types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=65536,
                    timeout=self.timeout
                )
            )

            # Parse response
            result = self._parse_response(response)

            if result:
                logger.info("Gemini API call successful (%d orders generated)", len(result.get('orders', [])))
            else:
                logger.warning("Gemini API returned empty result")

            return result

        except Exception as e:
            logger.error("Gemini API call failed: %s", e, exc_info=True)
            return None

    def _format_prompt(
        self,
        world_state: Dict[str, Any],
        mission_intent: str,
        objectives: List[Dict[str, Any]]
    ) -> str:
        """
        Format the prompt for Gemini with world state context

        Args:
            world_state: Current world state
            mission_intent: Mission intent/description
            objectives: List of objectives

        Returns:
            Formatted prompt string
        """
        # Extract key information
        controlled_groups = [g for g in world_state.get('groups', []) if g.get('is_controlled', False)]
        enemy_groups = [g for g in world_state.get('groups', []) if not g.get('is_controlled', False)]
        mission_time = world_state.get('mission_time', 0.0)
        is_night = world_state.get('is_night', False)
        ai_deployment = world_state.get('ai_deployment', {})

        # Build prompt
        prompt = f"""## TACTICAL SITUATION

**Mission Intent:** {mission_intent if mission_intent else 'No specific mission intent provided'}

**Mission Time:** {mission_time:.1f} seconds ({mission_time / 60:.1f} minutes)
**Time of Day:** {'NIGHT' if is_night else 'DAY'}

**AI Deployment:**
"""
        for side, count in ai_deployment.items():
            prompt += f"- {side}: {count} units\n"

        prompt += f"\n**Controlled Groups ({len(controlled_groups)}):**\n"
        for group in controlled_groups:
            nvg_capability = group.get('avg_night_capability', 0.0) * 100
            prompt += f"""
- {group['id']}:
  - Side: {group['side']}
  - Type: {group['type']}
  - Position: [{group['position'][0]:.1f}, {group['position'][1]:.1f}]
  - Units: {group['unit_count']}
  - NVG Capability: {nvg_capability:.0f}%
  - Behaviour: {group.get('behaviour', 'AWARE')}
"""
            known_enemies = group.get('known_enemies', [])
            if known_enemies:
                prompt += f"  - Known Enemies: {len(known_enemies)}\n"
                for enemy in known_enemies[:3]:  # Show max 3 enemies
                    prompt += f"    - {enemy['id']} ({enemy['type']}) at [{enemy['position'][0]:.1f}, {enemy['position'][1]:.1f}]\n"

        if enemy_groups:
            prompt += f"\n**Known Enemy Groups ({len(enemy_groups)}):**\n"
            for enemy in enemy_groups[:5]:  # Show max 5 enemies
                prompt += f"- {enemy['id']} ({enemy['type']}) at [{enemy['position'][0]:.1f}, {enemy['position'][1]:.1f}], {enemy['unit_count']} units\n"

        if objectives:
            prompt += f"\n**Mission Objectives ({len(objectives)}):**\n"
            for obj in objectives:
                prompt += f"- {obj.get('id', 'OBJ')}: {obj.get('text', 'No description')}\n"
                prompt += f"  - Position: [{obj['position'][0]:.1f}, {obj['position'][1]:.1f}]\n"
                prompt += f"  - Radius: {obj.get('radius', 0):.0f}m\n"

        # Include prior order summaries for context continuity (if provided)
        prior_summaries = world_state.get('order_summaries', [])
        if prior_summaries:
            prompt += "\n**Recent Order Summaries (last 5 cycles):**\n"
            for idx, item in enumerate(prior_summaries[-5:], start=1):
                text = item.get('summary', '') if isinstance(item, dict) else str(item)
                prompt += f"- [{idx}] {text}\n"

        prompt += """\n## YOUR TASK

Generate tactical orders for controlled groups. Output JSON ONLY:

```json
{
  "orders": [
    {"type": "deploy_asset", "side": "EAST"|"WEST"|"RESISTANCE", "asset_type": "ASSET_TYPE", "position": [x, y, z], "objective_id": "OBJ_ID"},
    {"type": "move_to", "group_id": "GRP_ID", "position": [x, y, z], "speed": "FULL"|"NORMAL"|"LIMITED"},
    {"type": "defend_area", "group_id": "GRP_ID", "position": [x, y, z], "radius": 200},
    {"type": "patrol_route", "group_id": "GRP_ID", "waypoints": [[x1,y1,z1], [x2,y2,z2]]},
    {"type": "seek_and_destroy", "group_id": "GRP_ID", "position": [x, y, z], "radius": 300},
    {"type": "spawn_squad", "side": "EAST"|"WEST"|"RESISTANCE", "unit_classes": ["I_soldier_F"], "position": [x, y, z], "objective_id": "OBJ_ID"},
  ],
  "commentary": "Brief tactical explanation",
  "order_summary": [
    "Line 1 summarizing which groups were tasked and where/why",
    "Line 2 ...",
    "Line 3 ..."
  ]
}
```

Consider:
- Coordinate multiple groups for combined arms operations
- Exploit terrain and known enemy positions
"""

        return prompt

    def _parse_response(self, response) -> Optional[Dict[str, Any]]:
        """
        Parse Gemini API response and extract JSON

        Args:
            response: Gemini API response object

        Returns:
            Dictionary with orders, commentary, and order_summary, or None if parsing failed
        """
        try:
            # Extract text from response
            if not response.text:
                logger.warning("Gemini response has no text")
                return None

            text = response.text.strip()

            # Try to extract JSON from code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    logger.warning("Could not find JSON in Gemini response")
                    return None

            # Parse JSON
            result = json.loads(json_str)

            # Validate structure
            if 'orders' not in result:
                logger.warning("Gemini response missing 'orders' field")
                return None

            if not isinstance(result['orders'], list):
                logger.warning("Gemini response 'orders' is not a list")
                return None

            logger.debug("Successfully parsed Gemini response with %d orders", len(result['orders']))
            return result

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from Gemini response: %s", e)
            return None
        except Exception as e:
            logger.error("Error parsing Gemini response: %s", e)
            return None
