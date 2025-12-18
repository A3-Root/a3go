"""
Global state manager for BATCOM

Manages mission state including objectives, AI context, and runtime configuration.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from ..models.objectives import Objective
from ..tracking.effectiveness import EffectivenessTracker
from ..learning.ao_analyzer import AOAnalyzer
from .ao_result_logger import AOResultLogger

logger = logging.getLogger('batcom.runtime.state')


class StateManager:
    """
    Manages global BATCOM state
    """

    def __init__(self):
        self.mission_intent = ""
        self.friendly_sides = []
        self.controlled_sides = []
        self.objectives = []
        self.deployed = False
        self.ai_context_memory = []
        self.ao_bounds: Dict[str, Any] = {}
        self.resource_pool: Dict[str, Dict[str, Any]] = {}
        self.resource_usage: Dict[str, Dict[str, int]] = {}
        self.controlled_group_overrides = set()
        self.key_assets: Dict[str, Any] = {}
        # Provider -> data (key, endpoint, deployment, etc.)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        # Runtime AI config overrides (provider/model/endpoint/min_interval/etc.)
        self.runtime_ai_config: Dict[str, Any] = {}
        # AO Defense Phase (when entire AO switches to defense mode, e.g., counterattack)
        self.ao_defense_active: bool = False

        # NEW: AO tracking
        self.effectiveness_tracker = EffectivenessTracker()
        self.ao_analyzer = AOAnalyzer()
        self.ao_result_logger = AOResultLogger()
        self.current_ao_id: Optional[str] = None
        self.ao_active: bool = False

        # AO Order History (for post-mission analysis)
        self.ao_orders: List[Dict[str, Any]] = []  # All orders for current AO
        self.ao_metadata: Dict[str, Any] = {}  # AO-specific metadata (map, mission, etc.)

        # AO intelligence for next commander (lessons learned from previous AO)
        self.previous_ao_intel: Optional[Dict[str, Any]] = None

    def set_mission_intent(self, intent: str, clear_memory: bool = False):
        """
        Set mission intent/description

        Args:
            intent: Mission description
            clear_memory: Whether to clear AI context memory
        """
        self.mission_intent = intent

        if clear_memory:
            self.ai_context_memory.clear()
            logger.info('Mission intent set (memory cleared): %s', intent)
        else:
            logger.info('Mission intent set: %s', intent)

    def set_friendly_sides(self, sides: List[str]):
        """
        Set friendly sides

        Args:
            sides: List of side strings (e.g., ["EAST", "GUER"])
        """
        self.friendly_sides = sides
        logger.info('Friendly sides set: %s', sides)

    def set_controlled_sides(self, sides: List[str]):
        """
        Set controlled sides (sides AI can command)

        Args:
            sides: List of side strings
        """
        self.controlled_sides = sides
        logger.info('Controlled sides set: %s', sides)

    def set_api_key(self, provider: str, api_key: str, **kwargs):
        """
        Inject an API key for a provider at runtime (server-side only)

        Args:
            provider: Provider identifier (e.g., gemini, openai, azure, claude, deepseek, local)
            api_key: API key string
            kwargs: Additional provider-specific fields (endpoint, deployment, etc.)
        """
        provider = (provider or "").lower()
        self.api_keys[provider] = {"key": api_key, **kwargs}
        if api_key:
            logger.info('%s API key injected (length: %d)', provider.upper(), len(api_key))
        else:
            logger.info('%s API key cleared', provider.upper())

    def update_ai_config(self, config: Dict[str, Any]):
        """
        Update runtime AI configuration (provider/model/endpoint/rate limits/api key)

        Args:
            config: Dictionary of overrides
        """
        if not isinstance(config, dict):
            raise ValueError("AI config must be a dictionary")

        # Normalize common aliases
        normalized = dict(config)
        if "api_url" in normalized and "endpoint" not in normalized:
            normalized["endpoint"] = normalized["api_url"]
        if "base_url" in normalized and "endpoint" not in normalized:
            normalized["endpoint"] = normalized["base_url"]
        if "key" in normalized and "api_key" not in normalized:
            normalized["api_key"] = normalized["key"]
        if "rpm" in normalized and "rate_limit" not in normalized:
            normalized["rate_limit"] = normalized["rpm"]

        # Store provider-specific key if present
        provider = (normalized.get("provider") or self.runtime_ai_config.get("provider") or "gemini").lower()
        api_key = normalized.get("api_key")
        extras = {k: v for k, v in normalized.items() if k not in ["api_key", "key"]}
        if api_key:
            self.set_api_key(provider, api_key, **extras)

        # Merge overrides
        self.runtime_ai_config.update(normalized)
        redacted = {k: ("<redacted>" if k in ["api_key", "key"] else v) for k, v in normalized.items()}
        logger.info("AI runtime config updated: %s", redacted)

    def add_objective(self, objective: Objective):
        """
        Add an objective

        Args:
            objective: Objective to add
        """
        self.objectives.append(objective)
        logger.info('Objective added: %s (priority: %d)', objective.description, objective.priority)

    def get_objective_by_id(self, obj_id: str) -> Objective:
        """Get objective by ID"""
        for obj in self.objectives:
            if obj.id == obj_id:
                return obj
        return None

    def deploy(self):
        """Mark commander as deployed"""
        self.deployed = True
        logger.info('Commander deployed')

    def undeploy(self):
        """Mark commander as undeployed"""
        self.deployed = False
        logger.info('Commander undeployed')

    def is_deployed(self) -> bool:
        """Check if commander is deployed"""
        return self.deployed

    def get_state_summary(self) -> Dict[str, Any]:
        """Get state summary"""
        return {
            "mission_intent": self.mission_intent,
            "friendly_sides": self.friendly_sides,
            "controlled_sides": self.controlled_sides,
            "objectives_count": len(self.objectives),
            "deployed": self.deployed,
            "ao_bounds": self.ao_bounds or {},
            "resource_pool": {k: list(v.keys()) for k, v in self.resource_pool.items()}
        }

    # ---------------- Guardrails / AO ----------------
    def set_ao_bounds(self, bounds: Dict[str, Any]):
        """Set area of operations bounds"""
        if not isinstance(bounds, dict):
            raise ValueError("AO bounds must be a dictionary")
        self.ao_bounds = bounds
        logger.info("AO bounds updated: %s", bounds)

    # ---------------- Resource pool ----------------
    def set_resource_pool(self, pool: Dict[str, Any]):
        """Configure resource pool"""
        if not isinstance(pool, dict):
            raise ValueError("Resource pool must be a dictionary")
        self.resource_pool = pool
        self.resource_usage = {side: {} for side in pool.keys()}
        logger.info("Resource pool configured for sides: %s", list(pool.keys()))

    def get_asset_template(self, side: str, asset_type: str) -> Dict[str, Any]:
        """Get asset template definition"""
        side_cfg = self.resource_pool.get(side.upper(), {})
        return side_cfg.get(asset_type, {}) if isinstance(side_cfg, dict) else {}

    def can_deploy_asset(self, side: str, asset_type: str, amount: int = 1) -> bool:
        """Check if asset can be deployed within limits"""
        template = self.get_asset_template(side, asset_type)
        if not template:
            return False
        max_count = template.get("max")
        used = self.resource_usage.get(side.upper(), {}).get(asset_type, 0)
        if max_count is None:
            return True
        return used + amount <= max_count

    def reserve_asset(self, side: str, asset_type: str, amount: int = 1) -> bool:
        """Reserve an asset from pool (returns False if limit exceeded)"""
        if not self.can_deploy_asset(side, asset_type, amount):
            return False
        side_key = side.upper()
        if side_key not in self.resource_usage:
            self.resource_usage[side_key] = {}
        self.resource_usage[side_key][asset_type] = self.resource_usage[side_key].get(asset_type, 0) + amount
        return True

    def get_resource_status(self) -> Dict[str, Any]:
        """Summarize remaining resources with constraints"""
        status = {}
        for side, assets in self.resource_pool.items():
            side_status = {}
            for asset_type, cfg in assets.items():
                max_count = cfg.get("max", 0)
                used = self.resource_usage.get(side, {}).get(asset_type, 0)
                defense_only = cfg.get("defense_only", False)
                description = cfg.get("description", "")

                side_status[asset_type] = {
                    "max": max_count,
                    "used": used,
                    "remaining": max_count - used if isinstance(max_count, (int, float)) else None,
                    "defense_only": defense_only,
                    "description": description
                }
            status[side] = side_status
        return status

    # ---------------- Controlled group overrides ----------------
    def set_controlled_group_overrides(self, group_ids):
        """Define specific groups that may be controlled regardless of side"""
        if not isinstance(group_ids, (list, set, tuple)):
            raise ValueError("Group overrides must be a list/set")
        self.controlled_group_overrides = set(group_ids)
        logger.info("Controlled group overrides set: %s", self.controlled_group_overrides)

    # ---------------- AO Management ----------------
    def start_ao(self, ao_id: str, map_name: str = None, mission_name: str = None, ao_number: int = None):
        """
        Start tracking a new AO

        Args:
            ao_id: Unique AO identifier
            map_name: Map name (e.g., "Altis", "Tanoa")
            mission_name: Mission name (e.g., "Defend_Base", "Attack_Convoy")
            ao_number: AO sequence number
        """
        self.current_ao_id = ao_id
        self.ao_active = True
        self.effectiveness_tracker.start_ao(ao_id, time.time())

        # Start AO result logging
        self.ao_result_logger.start_ao(ao_id, ao_number or 0, map_name or 'unknown', mission_name or 'unknown')

        # Reset order tracking for new AO
        self.ao_orders = []
        self.ao_metadata = {
            'ao_id': ao_id,
            'map_name': map_name or 'unknown',
            'mission_name': mission_name or 'unknown',
            'ao_number': ao_number or 0,
            'start_time': time.time(),
            'objectives': []  # Will be populated as objectives are added
        }

        logger.info(f'AO started: {ao_id} (map: {map_name}, mission: {mission_name}, ao#: {ao_number})')

    def end_ao(self):
        """End current AO and analyze results"""
        if not self.ao_active:
            return None

        ao_data = self.effectiveness_tracker.end_ao(time.time())

        # Add order history to ao_data for analysis
        if ao_data:
            ao_data['orders_issued'] = self.ao_orders
            ao_data['metadata'] = self.ao_metadata
            ao_data['end_time'] = time.time()

            analysis = self.ao_analyzer.analyze_ao(ao_data)
            logger.info(f'AO {self.current_ao_id} analysis: {analysis}')

        # Finalize AO result log and get intelligence for next commander
        self.previous_ao_intel = self.ao_result_logger.finalize_ao()

        self.ao_active = False
        self.current_ao_id = None

        return ao_data

    def record_ao_order(self, cycle: int, mission_time: float, orders: List[Dict], commentary: str = None, objectives: List[Dict] = None, order_summary: List[str] = None):
        """
        Record orders issued during AO for post-mission analysis

        Args:
            cycle: Decision cycle number
            mission_time: Mission time when orders were issued
            orders: List of order dictionaries from LLM
            commentary: LLM's tactical commentary/reasoning
            objectives: Active objectives at time of decision
            order_summary: Brief summary lines returned by the LLM
        """
        if not self.ao_active:
            return

        order_entry = {
            'cycle': cycle,
            'mission_time': round(mission_time, 1),
            'timestamp': time.time(),
            'order_count': len(orders),
            'orders': orders,
            'commentary': commentary or '',
            'objectives': objectives or [],
            'order_summary': order_summary or []
        }

        self.ao_orders.append(order_entry)
        logger.debug(f'Recorded {len(orders)} orders for AO {self.current_ao_id} (cycle {cycle})')

    def get_ao_order_history(self) -> List[Dict[str, Any]]:
        """Get complete order history for current AO"""
        return self.ao_orders

    def get_ao_analysis_data(self) -> Dict[str, Any]:
        """
        Get complete AO data for post-mission analysis including:
        - All objectives and their states
        - All orders issued with commentary
        - Mission metadata
        """
        return {
            'metadata': self.ao_metadata,
            'objectives_summary': [
                {
                    'id': obj.id,
                    'description': obj.description,
                    'state': obj.state.value if hasattr(obj.state, 'value') else str(obj.state),
                    'priority': obj.priority
                }
                for obj in self.objectives
            ],
            'orders_history': self.ao_orders,
            'total_cycles': len(self.ao_orders),
            'total_orders_issued': sum(entry['order_count'] for entry in self.ao_orders)
        }

    def is_ao_active(self) -> bool:
        """Check if AO is currently active"""
        return self.ao_active

    def get_previous_ao_intel(self) -> Optional[Dict[str, Any]]:
        """
        Get intelligence from previous AO for next commander

        Returns:
            Dictionary with previous AO results, or None if no previous AO
        """
        return self.previous_ao_intel

    def clear_previous_ao_intel(self):
        """Clear previous AO intelligence (called after it's been used)"""
        self.previous_ao_intel = None
        logger.debug('Previous AO intelligence cleared')

    # ---------------- AO Defense Phase ----------------
    def set_ao_defense_phase(self, active: bool):
        """
        Set AO defense phase status

        When True, the entire AO is in defense mode (e.g., counterattack phase).
        This allows defense_only assets to be deployed regardless of individual objective types.

        Args:
            active: True to enable AO defense phase, False to disable
        """
        self.ao_defense_active = active
        if active:
            logger.info("AO Defense Phase ACTIVATED - defense_only assets now available for deployment")
        else:
            logger.info("AO Defense Phase DEACTIVATED - defense_only assets restricted to defense objectives")

    def is_ao_defense_phase(self) -> bool:
        """
        Check if AO is in defense phase

        Returns:
            True if AO defense phase is active
        """
        return self.ao_defense_active
