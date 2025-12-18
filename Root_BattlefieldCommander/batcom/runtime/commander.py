"""
Battlefield Commander - Main decision loop orchestrator

Coordinates all decision-making subsystems to generate commands.
"""

import os
import logging
import hashlib
import threading
import json
import time
from typing import List, Dict, Any, Optional
from .state import StateManager
from .token_tracker import TokenTracker
from .api_logger import AOAPILogger
from ..models.world import WorldState
from ..models.objectives import ObjectiveState
from ..models.tasks import GroupAssignment
from ..models.commands import Command, MoveCommand, DefendCommand
from ..decision.evaluator import ObjectiveEvaluator
from ..decision.priority import PriorityCalculator
from ..decision.assignment import GroupAssigner
from ..decision.planner import TaskPlanner
from ..decision.tactics import TacticalBehaviorEngine
from ..commands.generator import CommandGenerator
from ..commands.queue import CommandQueue
from ..ai.order_parser import OrderParser
from ..ai.sandbox import CommandValidator
from ..ai.provider_manager import LLMProviderManager
from ..ai.gemini import RateLimiter

logger = logging.getLogger('batcom.runtime.commander')


class batcom:
    """
    Main AI commander orchestrator

    Runs the decision loop: evaluate objectives -> assign groups -> plan tasks -> generate commands
    """

    def __init__(self, state_manager: StateManager, command_queue: CommandQueue, config: Optional[Dict[str, Any]] = None):
        """
        Initialize commander

        Args:
            state_manager: Global state manager
            command_queue: Command queue for output
            config: Optional configuration dictionary
        """
        self.state = state_manager
        self.command_queue = command_queue
        self.config = config or {}

        # Initialize subsystems
        self.evaluator = ObjectiveEvaluator()
        self.priority_calc = PriorityCalculator()
        self.assigner = GroupAssigner(self.priority_calc)
        self.planner = TaskPlanner()
        self.generator = CommandGenerator()
        self.tactical_engine = TacticalBehaviorEngine()

        # Persistent state
        self.current_assignments: List[GroupAssignment] = []
        self.decision_cycle = 0

        # State change detection
        self.last_world_hash: Optional[str] = None
        self.last_decision_time: float = 0.0
        self.min_decision_interval: float = 30.0  # Minimum seconds between decisions

        # Order history for context continuity
        self.order_history: List[Dict[str, Any]] = []  # Track last N orders and outcomes
        self.max_history_entries = 10  # Keep last 10 decision cycles
        self.last_cached_objectives: Optional[str] = None  # Hash of objectives for cache invalidation

        # Circuit breaker for error handling
        self.llm_error_count = 0
        self.llm_max_errors = 3  # Stop LLM after 3 consecutive errors
        self.llm_circuit_open = False  # Set to True to permanently disable LLM
        self.fatal_error = False  # Set to True to stop entire commander

        # Token usage tracking (legacy - kept for compatibility)
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_llm_calls = 0
        self.last_token_report_time: float = 0.0

        # New token tracker with file logging
        self.token_tracker = TokenTracker(log_dir="@BATCOM")

        # Per-AO API call logger
        self.api_logger = AOAPILogger(log_dir="@BATCOM")

        # Async LLM call support
        self.llm_pending = False  # True if LLM call is in progress
        self.llm_result_cache: Optional[List[Command]] = None  # Cached LLM result
        self.llm_result_lock = threading.Lock()  # Thread safety for result cache
        self.llm_thread: Optional[threading.Thread] = None  # Background LLM thread
        self.first_llm_call_completed = False  # Track if we've made at least one successful LLM call

        # Initialize LLM components
        self.llm_enabled = False
        self.llm_client = None
        self.rate_limiter = None
        self.order_parser = None
        self.command_validator = None
        self.provider_manager = None  # New: manages multiple providers with fallback
        self.current_provider_name = None  # Track which provider is active
        self.system_prompt = self._build_system_prompt()

        self._init_llm()

        logger.info('Battlefield Commander initialized (LLM: %s)', 'enabled' if self.llm_enabled else 'disabled')

        # Track concise summaries returned by the LLM (order_summary) for next-call context
        self.order_summaries: List[Dict[str, Any]] = []

    def _compute_world_hash(self, world_state: WorldState) -> str:
        """
        Compute a hash of significant world state to detect changes

        Args:
            world_state: Current world state

        Returns:
            Hash string representing the current state
        """
        # Only hash significant state that should trigger new decisions
        state_parts = []

        # Group positions and unit counts
        for group in sorted(world_state.controlled_groups, key=lambda g: g.id):
            pos = tuple(int(p / 10) * 10 for p in group.position[:2])  # Round to nearest 10m
            state_parts.append(f"{group.id}:{pos}:{group.unit_count}")

        # Objective states
        for obj in sorted(self.state.objectives, key=lambda o: o.id):
            state_parts.append(f"{obj.id}:{obj.state.value}:{obj.priority}")

        # Create hash
        state_str = "|".join(state_parts)
        return hashlib.md5(state_str.encode()).hexdigest()

    def process_world_state(self, world_state: WorldState):
        """
        Main decision loop - processes world state and generates commands

        Args:
            world_state: Current world state from scanner
        """
        # Check for fatal error state
        if self.fatal_error:
            logger.error('Commander in fatal error state - all processing stopped. Restart required.')
            return

        # Check if deployed
        if not self.state.is_deployed():
            logger.debug('Commander not deployed, skipping decision loop')
            return

        # Check if we have objectives
        if not self.state.objectives:
            logger.debug('No objectives defined, skipping decision loop')
            return

        # Check if we have controlled groups
        if not world_state.controlled_groups:
            logger.debug('No controlled groups available, skipping decision loop')
            return

        # Enforce minimum decision interval (always check time first)
        time_since_last = world_state.mission_time - self.last_decision_time

        if time_since_last < self.min_decision_interval:
            logger.debug('Too soon for new decision (%.1fs since last, minimum: %.1fs) - skipping cycle',
                        time_since_last, self.min_decision_interval)
            return

        # Check for significant state changes
        current_hash = self._compute_world_hash(world_state)

        if current_hash == self.last_world_hash:
            logger.debug('No significant state change detected (same hash) - skipping cycle')
            return

        # State changed AND enough time passed - proceed with decision cycle
        self.decision_cycle += 1
        self.last_world_hash = current_hash
        self.last_decision_time = world_state.mission_time

        logger.info('='*60)
        logger.info('Decision cycle %d started (%.1fs since last, state changed)',
                   self.decision_cycle, time_since_last)
        logger.info('='*60)

        try:
            # Step 1: Evaluate objectives
            logger.info('Step 1: Evaluating %d objectives', len(self.state.objectives))
            updated_objectives = self.evaluator.evaluate_objectives(
                self.state.objectives,
                world_state
            )
            self.state.objectives = updated_objectives

            # Get active objectives
            active_objectives = self.evaluator.get_active_objectives(updated_objectives)
            logger.info('Active objectives: %d', len(active_objectives))

            if not active_objectives:
                logger.info('No active objectives, clearing assignments')
                self.current_assignments = []
                return

            # Step 1.5: LLM-ONLY Decision Making (NO FALLBACK)
            if not self.llm_enabled:
                logger.error('LLM is REQUIRED but not enabled - cannot generate commands!')
                logger.error('Commander will not issue any orders until LLM is properly configured')
                return

            logger.info('Step 1.5: Requesting LLM tactical decisions')
            commands = self._get_llm_suggestions_async(world_state, active_objectives)

            if commands is None:
                logger.warning('LLM call failed or not ready - waiting for next decision cycle')
                return

            if not commands:
                logger.info('LLM returned no commands - situation stable, no new orders needed')
                logger.info('Units continue executing current orders')
                return

            # Step 5: Queue commands
            logger.info('Step 5: Queuing %d commands for execution', len(commands))
            self.command_queue.enqueue_batch(commands)
            queue_stats = self.command_queue.stats()
            logger.info('Command queue stats: %s', queue_stats)

            # Record order history for context continuity
            self._record_order_history(world_state, active_objectives, commands)

            # Log simple summary (detailed logging only for rule-based path)
            logger.info('Decision summary: %d objectives, %d commands', len(active_objectives), len(commands))

            # Periodic token usage report (every LLM call)
            if self.llm_enabled and self.total_llm_calls > 0:
                time_since_report = world_state.mission_time - self.last_token_report_time
                # Report every LLM call or every 30 seconds, whichever comes first
                if time_since_report >= 30.0 or self.last_token_report_time == 0.0:
                    self._report_token_usage()
                    self.last_token_report_time = world_state.mission_time

        except Exception as e:
            logger.exception('Error in decision loop cycle %d', self.decision_cycle)

        logger.info('Decision cycle %d complete', self.decision_cycle)

    def _log_decision_summary(self, objectives, assignments, tasks, commands):
        """Log summary of decision cycle"""
        logger.info('-'*60)
        logger.info('DECISION SUMMARY')
        logger.info('-'*60)

        # Objectives summary
        logger.info('Objectives:')
        for obj in objectives:
            threat = obj.metadata.get('threat_level', 0)
            logger.info('  %s: %s (priority: %d, threat: %d)',
                       obj.id, obj.description, obj.priority, threat)

        # Assignments summary
        logger.info('Assignments:')
        assignment_by_obj = {}
        for assignment in assignments:
            if assignment.objective_id not in assignment_by_obj:
                assignment_by_obj[assignment.objective_id] = []
            assignment_by_obj[assignment.objective_id].append(assignment)

        for obj_id, obj_assignments in assignment_by_obj.items():
            logger.info('  %s: %d groups assigned', obj_id, len(obj_assignments))
            for assignment in obj_assignments:
                logger.info('    - %s (role: %s)', assignment.group_id, assignment.role)

        # Commands summary
        logger.info('Commands:')
        command_types = {}
        for cmd in commands:
            cmd_type = cmd.type.value
            command_types[cmd_type] = command_types.get(cmd_type, 0) + 1

        for cmd_type, count in command_types.items():
            logger.info('  %s: %d', cmd_type, count)

        logger.info('-'*60)

    def _report_token_usage(self):
        """Log cumulative token usage statistics"""
        total_tokens = self.total_input_tokens + self.total_output_tokens
        avg_input = self.total_input_tokens / self.total_llm_calls if self.total_llm_calls > 0 else 0
        avg_output = self.total_output_tokens / self.total_llm_calls if self.total_llm_calls > 0 else 0
        avg_total = total_tokens / self.total_llm_calls if self.total_llm_calls > 0 else 0

        logger.info('='*60)
        logger.info('CUMULATIVE TOKEN USAGE REPORT')
        logger.info('='*60)
        logger.info('Total LLM calls: %d', self.total_llm_calls)
        logger.info('Total input tokens: %d (avg: %.1f per call)', self.total_input_tokens, avg_input)
        logger.info('Total output tokens: %d (avg: %.1f per call)', self.total_output_tokens, avg_output)
        logger.info('Total tokens: %d (avg: %.1f per call)', total_tokens, avg_total)
        logger.info('='*60)

    def reset(self):
        """Reset commander state"""
        self.current_assignments = []
        self.decision_cycle = 0
        if self.order_parser:
            self.order_parser.reset()
        logger.info('Commander state reset')

    def _init_llm(self):
        """Initialize LLM components with multi-provider fallback support"""
        # Reset any existing clients so this can be re-run after injecting a key
        self.llm_enabled = False
        self.llm_client = None
        self.rate_limiter = None
        self.order_parser = None
        self.command_validator = None
        self.provider_manager = None
        self.current_provider_name = None

        try:
            # Check for new llm_providers array configuration
            ai_config = dict(self.config.get('ai', {}))
            llm_providers_config = ai_config.get('llm_providers', [])

            if llm_providers_config:
                # New config format: use provider manager with fallback
                logger.info("Using new llm_providers configuration with fallback support")
                self.provider_manager = LLMProviderManager(llm_providers_config, state_manager=self.state)

                # Try to initialize the first available provider
                result = self.provider_manager.get_next_provider()
                if result:
                    provider_config, client, rate_limiter = result
                    self.llm_client = client
                    self.rate_limiter = rate_limiter
                    self.current_provider_name = provider_config.name
                    self.llm_enabled = True

                    # Initialize parser and validator
                    self.order_parser = OrderParser()
                    safety_config = self.config.get('safety', {})
                    if self.state.ao_bounds:
                        safety_config = dict(safety_config)
                        safety_config['map_bounds'] = self.state.ao_bounds
                    self.command_validator = CommandValidator(safety_config, state_manager=self.state)

                    logger.info("LLM enabled with provider: %s (fallback available)", self.current_provider_name)
                    return
                else:
                    logger.error("No LLM providers available - all failed to initialize")
                    return

            # Fallback to old config format (deprecated)
            logger.warning("Using deprecated 'ai' config format - consider migrating to 'llm_providers' array")

            # Apply runtime overrides (from admin commands)
            if self.state.runtime_ai_config:
                ai_config.update(self.state.runtime_ai_config)
            if not ai_config.get('enabled', False):
                logger.info("LLM disabled in configuration")
                return

            provider = ai_config.get('provider', 'gemini').lower()

            # OLD PROVIDER INITIALIZATION (kept for backwards compatibility)
            if provider == "gemini":
                api_key = (ai_config.get('api_key')
                           or (self.state.api_keys.get('gemini') or {}).get('key')
                           or os.getenv('GEMINI_API_KEY'))
                if not api_key:
                    logger.warning("Gemini API key not set (runtime or environment) - LLM disabled")
                    return

                # Initialize components
                # IMPORTANT: For caching to work, model MUST have explicit version suffix (-001, -002, etc.)
                # "gemini-2.0-flash" won't work, must be "gemini-2.0-flash-001"
                model = ai_config.get('model', 'gemini-2.0-flash-001')
                timeout = ai_config.get('timeout', 30)
                max_output_tokens = ai_config.get('max_output_tokens', 4096)
                min_interval = ai_config.get('min_interval', None)
                rate_limit = ai_config.get('rate_limit', None)
                if min_interval is None and rate_limit:
                    try:
                        rate_limit_val = float(rate_limit)
                        if rate_limit_val > 0:
                            min_interval = 60.0 / rate_limit_val
                    except Exception:
                        min_interval = None
                if min_interval is None:
                    min_interval = 10.0
                endpoint = ai_config.get('endpoint') or ai_config.get('api_url') or ai_config.get('base_url')

                # Extract thinking configuration
                thinking_config = {
                    'thinking_enabled': ai_config.get('thinking_enabled', False),
                    'thinking_mode': ai_config.get('thinking_mode', 'native_sdk'),
                    'thinking_budget': ai_config.get('thinking_budget', -1),
                    'thinking_level': ai_config.get('thinking_level', 'high'),
                    'reasoning_effort': ai_config.get('reasoning_effort', 'medium'),
                    'include_thoughts': ai_config.get('include_thoughts', True),
                    'log_thoughts_to_file': ai_config.get('log_thoughts_to_file', True)
                }

                # Choose client based on thinking mode
                mode = thinking_config.get('thinking_mode', 'native_sdk')

                if mode == "openai_compat":
                    # Use OpenAI compatibility endpoint
                    from batcom.ai.providers import GeminiOpenAICompatClient
                    self.llm_client = GeminiOpenAICompatClient(
                        api_key=api_key,
                        model=model,
                        timeout=timeout,
                        max_output_tokens=max_output_tokens,
                        thinking_config=thinking_config
                    )
                    logger.info("Gemini LLM: Using OpenAI-compat mode (model: %s, thinking: %s)",
                                model, "enabled" if thinking_config['thinking_enabled'] else "disabled")
                else:
                    # Use native Google GenAI SDK (default)
                    from batcom.ai.providers import GeminiLLMClient
                    self.llm_client = GeminiLLMClient(
                        api_key=api_key,
                        model=model,
                        timeout=timeout,
                        endpoint=endpoint,
                        max_output_tokens=max_output_tokens,
                        thinking_config=thinking_config
                    )
                    logger.info("Gemini LLM: Using native SDK mode (model: %s, thinking: %s)",
                                model, "enabled" if thinking_config['thinking_enabled'] else "disabled")

                self.rate_limiter = RateLimiter(min_interval=min_interval)
                self.order_parser = OrderParser()

                # Initialize validator with safety config
                safety_config = self.config.get('safety', {})
                # Inject AO bounds from state guardrails if present
                if self.state.ao_bounds:
                    safety_config = dict(safety_config)
                    safety_config['map_bounds'] = self.state.ao_bounds
                self.command_validator = CommandValidator(safety_config, state_manager=self.state)

                self.llm_enabled = True
                logger.info("Gemini LLM integration enabled (model: %s, interval: %.1fs, mode: %s)",
                            model, min_interval, mode)

            elif provider in ["openai", "gpt"]:
                api_key = ai_config.get('api_key') or (self.state.api_keys.get('openai') or {}).get('key') or os.getenv('OPENAI_API_KEY')
                if not api_key:
                    logger.warning("OpenAI API key not set - LLM disabled")
                    return
                endpoint = ai_config.get('endpoint') or ai_config.get('api_url') or ai_config.get('base_url')
                model = ai_config.get('model', 'gpt-4o-mini')
                timeout = ai_config.get('timeout', 30)
                max_output_tokens = ai_config.get('max_output_tokens', 4096)
                use_responses_api = ai_config.get('use_responses_api', True)  # Default to True for better caching
                self.llm_client = OpenAILLMClient(api_key, model=model, endpoint=endpoint, timeout=timeout, max_output_tokens=max_output_tokens, use_responses_api=use_responses_api)
                self.rate_limiter = RateLimiter(min_interval=ai_config.get('min_interval', 10.0))
                self.order_parser = OrderParser()
                safety_config = self.config.get('safety', {})
                self.command_validator = CommandValidator(safety_config)
                self.llm_enabled = True
                logger.info("OpenAI LLM integration enabled (model: %s, endpoint: %s)", model, endpoint or "default")

            elif provider in ["claude", "anthropic"]:
                api_key = ai_config.get('api_key') or (self.state.api_keys.get('claude') or {}).get('key') or os.getenv('ANTHROPIC_API_KEY')
                if not api_key:
                    logger.warning("Anthropic API key not set - LLM disabled")
                    return
                endpoint = ai_config.get('endpoint') or ai_config.get('api_url') or ai_config.get('base_url')
                model = ai_config.get('model', 'claude-3-5-sonnet-20240620')
                timeout = ai_config.get('timeout', 30)
                max_output_tokens = ai_config.get('max_output_tokens', 4096)
                self.llm_client = AnthropicLLMClient(api_key, model=model, endpoint=endpoint, timeout=timeout, max_output_tokens=max_output_tokens)
                self.rate_limiter = RateLimiter(min_interval=ai_config.get('min_interval', 10.0))
                self.order_parser = OrderParser()
                safety_config = self.config.get('safety', {})
                self.command_validator = CommandValidator(safety_config)
                self.llm_enabled = True
                logger.info("Claude/Anthropic LLM integration enabled (model: %s, endpoint: %s)", model, endpoint or "default")

            elif provider == "deepseek":
                api_key = ai_config.get('api_key') or (self.state.api_keys.get('deepseek') or {}).get('key') or os.getenv('DEEPSEEK_API_KEY')
                if not api_key:
                    logger.warning("DeepSeek API key not set - LLM disabled")
                    return
                endpoint = ai_config.get('endpoint') or ai_config.get('api_url') or ai_config.get('base_url') or "https://api.deepseek.com"
                model = ai_config.get('model', 'deepseek-chat')
                timeout = ai_config.get('timeout', 30)
                max_output_tokens = ai_config.get('max_output_tokens', 4096)
                self.llm_client = DeepSeekLLMClient(api_key, model=model, endpoint=endpoint, timeout=timeout, max_output_tokens=max_output_tokens)
                self.rate_limiter = RateLimiter(min_interval=ai_config.get('min_interval', 10.0))
                self.order_parser = OrderParser()
                safety_config = self.config.get('safety', {})
                self.command_validator = CommandValidator(safety_config)
                self.llm_enabled = True
                logger.info("DeepSeek LLM integration enabled (model: %s, endpoint: %s)", model, endpoint)

            elif provider in ["azure", "azureopenai"]:
                api_key = ai_config.get('api_key') or (self.state.api_keys.get('azure') or {}).get('key') or os.getenv('AZURE_OPENAI_API_KEY')
                endpoint = ai_config.get('endpoint') or ai_config.get('api_url') or ai_config.get('base_url') or os.getenv('AZURE_OPENAI_ENDPOINT')
                if not api_key or not endpoint:
                    logger.warning("Azure OpenAI requires both api_key and endpoint")
                    return
                model = ai_config.get('model', 'gpt-4o-mini')
                timeout = ai_config.get('timeout', 30)
                max_output_tokens = ai_config.get('max_output_tokens', 4096)
                api_version = ai_config.get('api_version', '2024-02-15-preview')
                self.llm_client = AzureOpenAILLMClient(api_key, model=model, endpoint=endpoint, api_version=api_version, timeout=timeout, max_output_tokens=max_output_tokens)
                self.rate_limiter = RateLimiter(min_interval=ai_config.get('min_interval', 10.0))
                self.order_parser = OrderParser()
                safety_config = self.config.get('safety', {})
                self.command_validator = CommandValidator(safety_config)
                self.llm_enabled = True
                logger.info("Azure OpenAI integration enabled (model: %s, endpoint: %s)", model, endpoint)

            elif provider == "local":
                self.llm_client = LocalLLMClient()
                self.rate_limiter = RateLimiter(min_interval=ai_config.get('min_interval', 10.0))
                self.order_parser = OrderParser()
                safety_config = self.config.get('safety', {})
                self.command_validator = CommandValidator(safety_config)
                self.llm_enabled = False  # local mode yields None, rules only
                logger.info("Local LLM mode selected - rule-based decisions only")
                return

            else:
                logger.warning("Unknown LLM provider '%s' - LLM disabled", provider)
                return

        except ImportError as e:
            logger.error("Failed to import LLM components: %s", e)
            logger.warning("LLM integration disabled")
        except Exception as e:
            logger.error("Failed to initialize LLM: %s", e)
            logger.warning("LLM integration disabled")

    def _build_system_prompt(self) -> str:
        """Build the system prompt for LLM"""
        return """
System: # Role and Objective
You are an elite, fully autonomous tactical AI commander for Arma 3. As the sole decision-maker, you have direct control over all forces and your choices define tactical outcomes. Think creatively and strategically to outmaneuver the enemy and control the battlefield.

# Instructions
- Analyze the full battlefield context: friendly and enemy forces, terrain, objectives.
- Apply creative, unconstrained problem-solving; avoid conventional or static thinking.
- Adapt strategies to evolving threats and objectives.
- Command all available units purposefully; never leave assets idle unless tactically advantageous.
- Make bold, decisive choices when necessary.

## Situation Awareness Inputs
For every decision cycle, you receive:
- **controlled_groups:** Groups under your direct command (use their `id` as `group_id` for orders).
- **allied_groups:** Friendly but non-commandable forces; coordinate but do not issue orders.
- **player_groups:** Human players; coordinate but do not issue orders.
- **enemy_groups:** Only detected/enemy contacts—undetected enemies aren't shown.
- **force_summary:** Force counts and ratios.
- **situation:** Threat assessments and posture advice.
- **constraints:** AO boundaries (stay within these coordinates).
- **resources:** Deployable assets with remaining counts and constraints.
  - Some assets have **defense_only=true**, meaning they can ONLY be deployed when **ao_defense_phase.active=true** (global AO defense mode).
  - Defense-only assets are NOT available for individual defend_hq, defend_radiotower objectives - only during global AO defense phase.
  - When ao_defense_phase is active, ALL defense_only restrictions are lifted - deploy tanks, artillery, heavy assets freely.
  - Attempting to deploy defense_only assets when ao_defense_phase is not active will be rejected by validation.
  - Check both the asset's defense_only flag and ao_defense_phase status before issuing deploy_asset commands.
- **ao_defense_phase:** (optional) When present with active=true, the entire AO is in global defense mode (counterattack scenario).
  - All defense_only assets become available for deployment.
  - This typically occurs when enemy forces launch a major counterattack requiring heavy reinforcements.
  - Use your full arsenal - tanks, artillery, AA systems - to attack and hold the HQ.
- **deployment_directive:** When present, indicates if assets **must** be deployed this cycle. Details availability by side.
- **controlled_sides, friendly_sides:** Your command and allied sides (never engage friendly_sides).
- **staging rule:** Every deployed asset spawns at least 2km outside the AO centerline and must travel in—deploy early, allow for transit time.

# Strategic Mindset
## Objective-Oriented Thinking
- Interpret mission intent—discern the real victory conditions.
- Understand that defending locations may mean dynamic repositioning or relocating assets (such as HVTs) to maintain safety according to the briefing.
- Always evaluate every order through the lens of actual mission success, rather than literal interpretations.

## Force Dispersion & Survivability
- Never consolidate all forces at a single location. Doing so invites defeat via artillery, MLRS, mortars, or drone strikes.
- Maintain dispersed, mutually supporting positions with overlapping fields of fire.
- Respond to distant threats with only the closest 1-2 groups.
- Reserve forces should be distributed across strongpoints, not stacked at HQ.
- Allocate defense based on proportionate objective priority rather than equal group distribution.

## Priority Hierarchy (Force Allocation)
1. **HQ (defend_hq):** Highest priority, but never abandon all other objectives for HQ. Assign 3-4 strong groups minimum if available.
2. **Force Multipliers (defend_radiotower, defend_gps_jammer):** High priority—defend assertively, even at cost of lesser objectives.
3. **Support Assets (defend_mortar_pit, defend_supply_depot):** Medium priority—can be sacrificed if higher objectives at risk.
4. **Tactical Assets (defend_hmg_tower, defend_aa_site):** Low; only escalate to high if specific air threat emerges.
- Allocate forces in proportion to the `priority` value of each objective, not equally.

## Strategic Withdrawal Doctrine
- Do **not** waste forces heroically at overwhelmed, low-priority objectives; withdraw and consolidate for defense elsewhere.
- Use delaying tactics (hit-and-run, air support) for abandoned positions.

## Decision Matrix
- Withdraw from low/medium priority objectives under overwhelming threat; reinforce higher-priority positions.
- If HQ or critical objectives are overwhelmed, deploy reinforcements but always protect the broader AO control.
- HQ loss is a setback, not mission failure—consider opportunities to recapture or strengthen other objectives.

## Force Employment
- Use every available group purposefully (assault, support, recon, reserve, etc.).
- Layer defenses and leverage terrain advantages.
- Keep reserves ready for counterattacks.

## Threat Assessment & Proportional Response
- Always match response size/type to real threat level and location.
- Never abandon broadly-distributed defense or overreact to isolated/distant threats.

## Spatial Intelligence
Review each groups radius to:
- Decide proportional response to enemys proximity to objectives.
- Avoid over-concentration at threatened or high-traffic zones.

## Tactical Decision Framework
For every decision, internally ask:
1. What is the *true* mission? (not just literal orders)
2. Who/what is the biggest threat currently?
3. Am I employing all forces in an optimal, creative way?
4. Which groups are closest to each threat/objective?
5. What creative or unconventional moves change the situation?
6. Is my plan proactive or reactive?
7. What would a brilliant real-world commander do?

## HVT Engagement Protocol
- Commit 1.5x typical force to high-value targets (HVTs).
- Use combined arms and coordinated attacks.
- Prioritize caution and aggression—HVT elimination critically reduces enemy effectiveness.

# Constraints
- Only issue commands to controlled_sides. Never engage friendly_sides.
- Always use valid `group_id` from controlled_groups.
- Provide valid `[x, y, z]` coordinates—confirm points are within AO bounds via constraints.
- Confirm sufficient asset availability in `resources` before deploying.

# Output Format

## CRITICAL: Strict JSON Schema
You MUST use these EXACT field names. Do NOT use variations or synonyms.

**Response Structure:**
```json
{
  "orders": [order objects - see schemas below],
  "commentary": "Concise explanation of your reasoning (≤40 words, no fluff).",
  "order_summary": [
    "Assigned X groups (GRP_ID1, GRP_ID2, ...) to ACTION at LOCATION (OBJ_ID) - REASON",
    "..."
  ]
}
```

**Order Object Schemas (use EXACT field names):**

1. **deploy_asset** - Deploy new units from resource pool
   ```json
   {"type": "deploy_asset", "side": "EAST"|"WEST"|"RESISTANCE", "asset_type": "ASSET_TYPE", "position": [x, y, z], "objective_id": "OBJ_ID"}
   ```
   Required fields: `type`, `side`, `asset_type`, `position`
   Field name MUST be `position` (NOT `location`, NOT `center`)

2. **move_to** - Move group to position
   ```json
   {"type": "move_to", "group_id": "GRP_ID", "position": [x, y, z], "speed": "FULL"|"NORMAL"|"LIMITED"}
   ```
   Required fields: `type`, `group_id`, `position`
   Field name MUST be `position` (NOT `location`, NOT `center`)

3. **defend_area** - Establish defensive position
   ```json
   {"type": "defend_area", "group_id": "GRP_ID", "position": [x, y, z], "radius": 200}
   ```
   Required fields: `type`, `group_id`, `position`, `radius`
   Field name MUST be `position` (NOT `location`, NOT `center`)

4. **patrol_route** - Patrol between waypoints
   ```json
   {"type": "patrol_route", "group_id": "GRP_ID", "waypoints": [[x1, y1, z1], [x2, y2, z2]]}
   ```
   Required fields: `type`, `group_id`, `waypoints`

5. **seek_and_destroy** - Offensive action in area
   ```json
   {"type": "seek_and_destroy", "group_id": "GRP_ID", "position": [x, y, z], "radius": 300}
   ```
   Required fields: `type`, `group_id`, `position`, `radius`
   Field name MUST be `position` (NOT `location`, NOT `center`)

6. **spawn_squad** - Spawn custom unit composition
   ```json
   {"type": "spawn_squad", "side": "EAST"|"WEST"|"RESISTANCE", "unit_classes": ["I_soldier_F", "I_officer_F"], "position": [x, y, z], "objective_id": "OBJ_ID"}
   ```
   Required fields: `type`, `side`, `unit_classes`, `position`
   Field name MUST be `position` (NOT `location`, NOT `center`)

**CRITICAL RULES:**
- Field name for coordinates MUST be `position` - never use `location`, `center`, or any other name
- Field name for order type MUST be `type` - never use `action` or any other name
- Use exact field names as shown above - parser will reject orders with incorrect field names

## Empty Orders
- If all groups are appropriately tasked and the battlefield is stable, you may return an empty `orders` array. Summarize current assignments per group and rationale for no changes.

## Command Types
- **deploy_asset:** Use to add new units when outnumbered or strengthening. Prioritize use when threat/risk is high, using `resources` availability.
- **move_to:** Reposition for maneuvers, withdrawal, or reinforcement.
- **defend_area:** Establish defensive postures.
- **patrol_route:** Recon and area security.
- **seek_and_destroy:** Offensive actions on threats.
- **transport_group:** Rapid infantry/HVT moves via vehicle.
- **escort_group:** Assign close protection to critical groups (HVTs, convoys).
- **fire_support:** Use for direct/indirect fire to deter, delay, or break up attacks.

## Asset Employment
- Air: Attack, fire support, avoid static hover over objectives.
- Armor/Mech: Defense, shock action, ambush (not idle at HVT).
- Transport: Use for fast redeployment; encourage escort pairing.
- Only deploy assets if their use bolsters tactical position per situational threat.

# Resource Management
- You can autonomously deploy assets from the resource pool at any time. Use tactical judgment; no explicit human direction required.
- Mandatory triggers for deployment:
  - `deployment_directive.must_deploy_now == true`
  - Force ratio <1.0 + enemy engaging objectives → deploy proportionally
  - Ratio <1.5 + significant threat → deploy as needed
  - Threat HIGH/CRITICAL → deploy armor/air as warranted
  - Moderate threat → reinforce weak points
  - Remember: Distance/activity matters more than force ratio alone.
- Additional deploy triggers: defending critical points, forming reserves, facing concentrated threats.
- Prioritize asset types (infantry, IFV, attack helicopter) depending on force ratio and threat context.
- Check `resources.by_side[SIDE][asset_type].remaining` prior to each deploy order.

# Guardrails
- Stay within AO bounds (constraints).
- Never over-commit assets—each should yield true tactical benefit.
- Never attack friendly sides.

# Summary Reminders
- You are the ONLY intelligence: think and act decisively.
- Be creative, adaptive, and always mission-focused.
- Issue purposeful orders to every unit.

# Output Verbosity
- All output must remain tightly controlled in length:
    - Commentary: At most 40 words, concise, no restatement of politeness.
    - Order summary: Maximum of 24 entries, 1 line per assigned group/action.
    - If user requests supervision/preamble updates, keep updates to 1-2 sentences unless longer supervision is explicitly requested.
- Prioritize complete, actionable answers within these length caps—avoid collapsing responses or omitting reasoning.
- If personality or stance emphasizes respect or clarity, do not increase length to restate politeness.

"""

    def _get_llm_suggestions_internal(self, world_state: WorldState, objectives: List[ObjectiveState]) -> Optional[List[Command]]:
        """
        Internal LLM suggestion function (bypasses rate limiter, called by async worker)

        Args:
            world_state: Current world state
            objectives: Active objectives

        Returns:
            List of commands from LLM, or None on failure
        """
        logger.info(">>> _get_llm_suggestions_internal ENTERED - llm_enabled=%s, circuit_open=%s, llm_client=%s",
                    self.llm_enabled, self.llm_circuit_open, self.llm_client is not None)

        if not self.llm_enabled:
            logger.warning("LLM not enabled - returning None immediately")
            return None

        if self.llm_circuit_open:
            logger.warning("LLM circuit breaker is open - returning None immediately")
            return None

        if not self.llm_client:
            logger.error("LLM client is None - cannot make LLM calls!")
            return None

        try:
            logger.info("LLM request starting: groups=%d (controlled=%d), players=%d, objectives=%d",
                        len(world_state.groups), len(world_state.controlled_groups),
                        len(world_state.players), len(objectives))

            # Convert world state to dict (dynamic, changes every cycle)
            world_state_dict = self._world_state_to_dict(world_state)

            # Build cached context (static/slow-changing: system prompt + objectives + history)
            # This will be cached by Gemini and reused until objectives change
            objectives_hash = self._objectives_hash(objectives)
            cache_needs_update = (self.last_cached_objectives != objectives_hash)

            cached_context = self._build_cached_context(objectives)

            # DEBUG: Log cache hash to track changes
            import hashlib
            cached_context_hash = hashlib.md5(cached_context.encode()).hexdigest()[:16]
            logger.info("CACHE TRACKING: objectives_hash=%s, cached_context_hash=%s",
                       objectives_hash[:16], cached_context_hash)

            if cache_needs_update:
                self.last_cached_objectives = objectives_hash
                logger.info("=" * 80)
                logger.info("OBJECTIVES CHANGED - Cache will be updated")
                logger.info("Objectives hash: %s", objectives_hash)
                logger.info("Cached context hash: %s", cached_context_hash)
                logger.info("=" * 80)
            else:
                logger.info("OBJECTIVES UNCHANGED - Cache should be reused (hash: %s)", cached_context_hash)

            # Call LLM - Log complete input for debugging
            provider_name = self.current_provider_name or self.config.get('ai', {}).get('provider', 'unknown')
            provider_model = "unknown"
            if self.provider_manager and self.current_provider_name:
                # Get model from active provider
                for p in self.provider_manager.providers:
                    if p.name == self.current_provider_name:
                        provider_model = p.model
                        break
            else:
                provider_model = self.config.get('ai', {}).get('model', 'unknown')

            logger.info("=" * 80)
            logger.info("LLM CALL START - Provider: %s, Model: %s",
                       provider_name, provider_model)
            logger.info("=" * 80)

            # Log what's being cached vs what's fresh
            logger.info("CACHED CONTEXT: %d chars (system prompt + objectives ONLY - no history to preserve cache)", len(cached_context))
            logger.info("FRESH CONTEXT: Mission intent + world state + order_summaries (sent every call)")

            # Log mission intent
            logger.info("-" * 80)
            logger.info("MISSION INTENT:")
            logger.info(world_state.mission_intent or "N/A")

            # Log world state (formatted for readability)
            logger.info("-" * 80)
            logger.info("WORLD STATE (DYNAMIC):")
            logger.info(json.dumps(world_state_dict, indent=2))

            logger.info("=" * 80)

            # Log API request to per-AO log file (COMPLETE RAW DATA)
            request_start_time = time.time()
            if self.state.is_ao_active():
                # Convert objectives to dict for logging
                objectives_dict = [self._objective_to_dict(obj) for obj in objectives]

                self.api_logger.log_request(
                    cycle=self.decision_cycle,
                    mission_time=world_state.mission_time,
                    provider=provider_name,
                    model=provider_model,
                    request_data={
                        'world_state': world_state_dict,
                        'mission_intent': world_state.mission_intent
                    },
                    cached_context=cached_context,  # COMPLETE cached context (system prompt + objectives + history)
                    objectives=objectives_dict  # COMPLETE objectives list
                )

            # Call LLM with separate cached context and fresh world state
            response = self.llm_client.generate_tactical_orders(
                world_state_dict,
                world_state.mission_intent,
                objectives,  # Pass objectives for backward compatibility
                cached_context  # This includes system prompt + objectives + history
            )

            # Calculate latency
            latency_ms = (time.time() - request_start_time) * 1000

            # Log response details
            logger.info("=" * 80)
            logger.info("LLM CALL COMPLETE - Response received")
            logger.info("=" * 80)

            if not response:
                logger.warning("LLM returned no response (None)")
                logger.info("=" * 80)
                return None

            # Extract and log full raw response
            raw_text = ""
            if isinstance(response, dict) and "__raw_text" in response:
                raw_text = response.pop("__raw_text") or ""
                logger.info("RAW LLM RESPONSE (FULL TEXT):")
                logger.info(raw_text)
                logger.info("-" * 80)

            # Extract and accumulate token usage
            token_usage = {}
            if isinstance(response, dict) and "__token_usage" in response:
                token_usage = response.pop("__token_usage", {})
                input_tokens = token_usage.get('input_tokens', 0)
                output_tokens = token_usage.get('output_tokens', 0)

                # Legacy counters
                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens
                self.total_llm_calls += 1

                # New token tracker with file logging
                self.token_tracker.record_call(input_tokens, output_tokens, provider_name)

                logger.info("Token usage this call: %d input, %d output | Total: %d input, %d output (%d calls)",
                           input_tokens, output_tokens,
                           self.total_input_tokens, self.total_output_tokens, self.total_llm_calls)

            # Parse orders, commentary, and LLM-provided order summary
            orders = response.get('orders', [])
            commentary = response.get('commentary', '')
            order_summary = response.get('order_summary', [])

            if isinstance(order_summary, str):
                order_summary_lines = [line.strip() for line in order_summary.splitlines() if line.strip()]
            elif isinstance(order_summary, list):
                order_summary_lines = [str(line).strip() for line in order_summary if str(line).strip()]
            else:
                order_summary_lines = []

            summary_text = "; ".join(order_summary_lines[:5]) if order_summary_lines else ""

            logger.info("PARSED LLM RESPONSE:")
            logger.info("Commentary: %s", commentary if commentary else "None")
            logger.info("Order Summary: %s", summary_text if summary_text else "None")
            logger.info("Orders (%d total):", len(orders))
            logger.info(json.dumps(orders, indent=2))
            logger.info("=" * 80)

            # Log API response to per-AO log file (COMPLETE RAW DATA)
            if self.state.is_ao_active():
                self.api_logger.log_response(
                    success=True,
                    response_data={'orders': orders, 'commentary': commentary, 'order_summary': order_summary_lines},
                    token_usage={
                        'input_tokens': input_tokens if token_usage else 0,
                        'output_tokens': output_tokens if token_usage else 0,
                        'cached_tokens': token_usage.get('cached_tokens', 0)
                    },
                    latency_ms=latency_ms,
                    raw_response=raw_text  # COMPLETE raw LLM response text (not truncated)
                )

                # Record orders with commentary to state for post-AO analysis
                objectives_dict = [self._objective_to_dict(obj) for obj in objectives]
                self.state.record_ao_order(
                    cycle=self.decision_cycle,
                    mission_time=world_state.mission_time,
                    orders=orders,
                    commentary=commentary,
                    order_summary=order_summary_lines,
                    objectives=objectives_dict
                )

                # Track recent order summaries for next-call context (max 5)
                if order_summary_lines:
                    self.order_summaries.append({
                        'cycle': self.decision_cycle,
                        'mission_time': round(world_state.mission_time),
                        'summary': summary_text
                    })
                    self.order_summaries = self.order_summaries[-5:]

            # Handle empty orders (situation stable, no changes needed)
            if not orders:
                logger.info("LLM returned no orders - situation stable, no changes needed")
                # This is valid - the LLM determined current orders are appropriate
                return []

            # Parse into Command objects
            commands = self.order_parser.parse_llm_orders(orders)
            commands = self._augment_deploy_followups(commands, objectives)

            if not commands:
                logger.warning("No valid commands after parsing (all orders rejected)")
                return []

            # Validate commands through sandbox
            validated_commands = self.command_validator.validate_commands(commands, world_state)

            if not validated_commands:
                logger.warning("All LLM commands rejected by sandbox")
                return None

            # Deduplicate commands - enforce STRICTLY 1 order per group (keep first order for each group)
            seen_group_ids = set()
            deduplicated_commands = []
            duplicate_count = 0

            for cmd in validated_commands:
                group_id = getattr(cmd, 'group_id', None)
                if group_id:
                    if group_id not in seen_group_ids:
                        seen_group_ids.add(group_id)
                        deduplicated_commands.append(cmd)
                    else:
                        duplicate_count += 1
                        logger.warning("Duplicate order for group %s - keeping first order only", group_id)
                else:
                    # Commands without group_id (like deploy_asset) pass through
                    deduplicated_commands.append(cmd)

            if duplicate_count > 0:
                logger.warning("Removed %d duplicate orders - enforcing 1 order per group", duplicate_count)

            validated_commands = deduplicated_commands

            logger.info("LLM generated %d commands (%d passed validation, %d after deduplication)",
                       len(commands), len(validated_commands) + duplicate_count, len(validated_commands))

            # Reset error counter on successful call
            self.llm_error_count = 0

            # Record success with provider manager (resets failure count)
            if self.provider_manager and self.current_provider_name:
                self.provider_manager.record_success(self.current_provider_name)

            return validated_commands

        except Exception as e:
            self.llm_error_count += 1
            logger.error("Error getting LLM suggestions from %s (error %d/%d): %s",
                        self.current_provider_name or "unknown", self.llm_error_count, self.llm_max_errors, e, exc_info=True)

            # Log API error to per-AO log file
            if self.state.is_ao_active():
                self.api_logger.log_response(
                    success=False,
                    error=str(e)
                )

            # Record failure with provider manager
            if self.provider_manager and self.current_provider_name:
                self.provider_manager.record_failure(self.current_provider_name)

            # Try to fallback to next provider if provider manager is available
            if self.provider_manager and self.llm_error_count < self.llm_max_errors:
                logger.warning("Attempting fallback to next provider...")
                self.provider_manager.fallback_to_next()

                # Try to initialize next provider
                result = self.provider_manager.get_next_provider()
                if result:
                    provider_config, client, rate_limiter = result
                    self.llm_client = client
                    self.rate_limiter = rate_limiter
                    self.current_provider_name = provider_config.name

                    logger.info("Switched to fallback provider: %s", self.current_provider_name)
                    # Reset error count for new provider
                    self.llm_error_count = 0
                    return None  # Return None for this cycle, will use new provider next cycle
                else:
                    logger.error("All fallback providers failed - no more providers available")

            # Circuit breaker: disable LLM after too many errors
            if self.llm_error_count >= self.llm_max_errors:
                self.llm_circuit_open = True
                self.llm_enabled = False
                logger.critical("LLM circuit breaker opened after %d consecutive errors - LLM disabled (all providers exhausted)",
                              self.llm_max_errors)

            return None

    def _augment_deploy_followups(self, commands: List[Command], objectives: List[ObjectiveState]) -> List[Command]:
        """
        Previously added hardcoded follow-up orders after deploy_asset commands.
        Now disabled - the LLM will decide what orders to give deployed assets in subsequent decision cycles.

        Deployed groups appear in controlled_groups on the next world scan, and the LLM
        will assign them tactical orders based on the current battlefield situation.
        """
        # Return commands unchanged - let LLM handle deployed asset orders
        return commands

    def _get_llm_suggestions(self, world_state: WorldState, objectives: List[ObjectiveState]) -> Optional[List[Command]]:
        """
        Get tactical suggestions from LLM (with rate limiter check)

        Args:
            world_state: Current world state
            objectives: Active objectives

        Returns:
            List of commands from LLM, or None on failure
        """
        if not self.llm_enabled or self.llm_circuit_open:
            return None

        # Check rate limiter
        if not self.rate_limiter.should_call_llm(world_state.mission_time):
            logger.debug("Rate limited - skipping LLM call")
            return None

        # Call internal function
        return self._get_llm_suggestions_internal(world_state, objectives)

    def _get_llm_suggestions_async(self, world_state: WorldState, objectives: List[ObjectiveState]) -> Optional[List[Command]]:
        """
        Get tactical suggestions from LLM asynchronously (non-blocking)

        This method:
        1. Returns cached result if available from previous call
        2. Starts a background LLM call if rate limit allows and no call is pending
        3. Returns None if LLM call is in progress or not ready

        Args:
            world_state: Current world state
            objectives: Active objectives

        Returns:
            List of commands from LLM (if ready), or None if not ready/unavailable
        """
        if not self.llm_enabled or self.llm_circuit_open:
            return None

        # Check if we have a cached result from previous async call
        with self.llm_result_lock:
            if self.llm_result_cache is not None:
                logger.info("Using cached LLM result from background call")
                result = self.llm_result_cache
                self.llm_result_cache = None  # Clear cache after use
                self.llm_pending = False
                return result

        # Check if LLM call is already in progress
        if self.llm_pending:
            logger.debug("LLM call already in progress - using rule-based fallback")
            return None

        # Check rate limiter to see if we should start a new call
        if not self.rate_limiter.should_call_llm(world_state.mission_time):
            logger.debug("Rate limited - not starting new LLM call")
            return None

        # Start background LLM call
        logger.info("Starting background LLM call (non-blocking) - llm_enabled=%s", self.llm_enabled)
        self.llm_pending = True
        mission_time_at_call = world_state.mission_time

        def llm_worker():
            """Background worker for LLM call"""
            logger.debug("LLM worker thread started")
            try:
                # Call LLM directly, bypassing rate limiter (already checked by async function)
                logger.debug("Calling _get_llm_suggestions_internal...")
                commands = self._get_llm_suggestions_internal(world_state, objectives)
                logger.debug("_get_llm_suggestions_internal returned: %s",
                           f"{len(commands)} commands" if commands else "None")

                if commands:
                    logger.info("Background LLM call completed successfully with %d commands", len(commands))
                    # Execute immediately so we don't wait for next decision cycle
                    self.command_queue.enqueue_batch(commands)
                    logger.info("Commands enqueued immediately from background LLM call (mission_time=%.1f)", mission_time_at_call)
                else:
                    logger.warning("Background LLM call completed but returned no commands (check logs above for errors)")

                with self.llm_result_lock:
                    self.llm_result_cache = commands
                    self.llm_pending = False
            except Exception as e:
                logger.error("Error in background LLM call: %s", e, exc_info=True)
                with self.llm_result_lock:
                    self.llm_pending = False

        # Start thread
        self.llm_thread = threading.Thread(target=llm_worker, daemon=True)
        self.llm_thread.start()

        # Return None for this cycle, LLM result will be ready next cycle
        logger.debug("LLM call started in background - no commands this cycle, waiting for LLM")
        return None

    def _world_state_to_dict(self, world_state: WorldState) -> Dict[str, Any]:
        """Convert WorldState to dictionary for LLM with comprehensive battlefield intel"""
        # Categorize all groups
        all_groups = world_state.groups
        controlled_groups = world_state.controlled_groups

        # Get objectives for spatial intelligence
        objectives = self.state.objectives if hasattr(self.state, 'objectives') else []

        # Separate groups by category
        player_groups = [g for g in all_groups if getattr(g, 'is_player_group', False)]
        allied_groups = [g for g in all_groups if getattr(g, 'is_friendly', False) and not g.is_controlled]
        enemy_groups = [g for g in all_groups if g.side not in self.state.controlled_sides and g.side not in self.state.friendly_sides]

        # Calculate force statistics
        total_controlled = sum(g.unit_count for g in controlled_groups)
        total_allied = sum(g.unit_count for g in allied_groups)
        total_player = sum(g.unit_count for g in player_groups)
        total_friendly = total_controlled + total_allied
        total_enemies = sum(g.unit_count for g in enemy_groups)
        force_ratio = round(total_friendly / total_enemies, 2) if total_enemies > 0 else 999
        situation = self._assess_situation(world_state, controlled_groups + allied_groups, enemy_groups)

        # Derive key asset hints from mission variables (conventions)
        key_assets = {}
        mv = world_state.mission_variables or {}
        if isinstance(mv, dict):
            if mv.get('BATCOM_missionIntel_HVTGroupId'):
                key_assets['hvt_group_id'] = mv.get('BATCOM_missionIntel_HVTGroupId')
            if mv.get('BATCOM_missionIntel_HVTPosition'):
                key_assets['hvt_position'] = mv.get('BATCOM_missionIntel_HVTPosition')

        # Format AO bounds for clarity
        ao_bounds_formatted = None
        if self.state.ao_bounds:
            ao_bounds_formatted = {
                'description': 'All movements and deployments MUST stay within these bounds',
                'bounds': self.state.ao_bounds
            }

        # Format resource pool status for clarity
        resources_formatted = None
        if hasattr(self.state, "get_resource_status"):
            resource_status = self.state.get_resource_status()
            if resource_status:
                resources_formatted = {
                    'description': 'Available assets that can be deployed using deploy_asset command. Each asset has a maximum limit.',
                    'by_side': resource_status,
                    'usage_note': 'Check "remaining" count before deploying. Once max is reached, no more can be deployed.'
                }

        # Get HVT context from effectiveness tracker
        hvt_context_text = self.state.effectiveness_tracker.get_hvt_context()

        # Build worldstate dict, excluding None values to avoid SQF nil errors
        worldstate_dict = {
            # Time and environment
            'mission_time': round(world_state.mission_time),
            'is_night': world_state.is_night,
            'time_of_day': 'NIGHT' if world_state.is_night else 'DAY',

            # Comprehensive force summary
            'force_summary': {
                'total_groups_on_server': len(all_groups),
                'controlled_groups': len(controlled_groups),
                'controlled_units': total_controlled,
                'allied_groups': len(allied_groups),
                'allied_units': total_allied,
                'player_groups': len(player_groups),
                'player_units': total_player,
                'total_friendly_groups': len(controlled_groups) + len(allied_groups),
                'total_friendly_units': total_friendly,
                'enemy_groups': len(enemy_groups),
                'enemy_units': total_enemies,
                'force_ratio': force_ratio
            },

            # Your controlled groups (full detail with orders and combat status)
            'controlled_groups': [self._group_to_dict(g, detailed=True, objectives=objectives, enemy_groups=enemy_groups[:30]) for g in controlled_groups],

            # Allied groups not under your control (detailed - these are friendly forces)
            'allied_groups': [self._group_to_dict(g, detailed=True, objectives=objectives, enemy_groups=enemy_groups[:30]) for g in allied_groups],

            # Player groups (detailed - important to coordinate with)
            'player_groups': [self._group_to_dict(g, detailed=True, objectives=objectives, enemy_groups=enemy_groups[:30]) for g in player_groups if g not in controlled_groups],

            # Known enemy groups (battlefield intelligence - only detected enemies, top 30 threats)
            'enemy_groups': [self._group_to_dict(g, detailed=False, objectives=objectives, friendly_groups=controlled_groups + allied_groups) for g in enemy_groups[:30]],

            # Battlefield situation assessment
            'situation': situation,

            # Faction information
            'controlled_sides': self.state.controlled_sides,
            'friendly_sides': self.state.friendly_sides,

            # Mission context
            'mission_variables': world_state.mission_variables,
            'key_assets': key_assets
        }

        # Provide concise history of prior LLM-returned order summaries (max 5) for continuity
        if self.order_summaries:
            worldstate_dict['order_summaries'] = self.order_summaries[-5:]

        # Add HVT context if available
        if hvt_context_text:
            worldstate_dict['hvt_intel'] = hvt_context_text

        # Previous AO intelligence is now added to cached_context (system prompt)
        # instead of world_state so it gets cached and doesn't bloat every request

        # Add optional fields only if they have values (avoid None/nil in SQF)
        if ao_bounds_formatted is not None:
            worldstate_dict['constraints'] = ao_bounds_formatted

        if resources_formatted is not None:
            worldstate_dict['resources'] = resources_formatted

            # Add AO defense phase status (enables defense_only assets globally)
            if self.state.is_ao_defense_phase():
                worldstate_dict['ao_defense_phase'] = {
                    'active': True,
                    'description': 'AO is under counterattack - ALL defense_only assets are now available for deployment'
                }

            # Deployment directive to push the LLM to use the pool when threatened
            assets_for_controlled = {
                side: resources_formatted['by_side'].get(side, {})
                for side in self.state.controlled_sides
                if resources_formatted['by_side'].get(side)
            }
            has_assets_remaining = any(
                any((asset_cfg.get('remaining', 0) or 0) > 0 for asset_cfg in side_assets.values())
                for side_assets in assets_for_controlled.values()
            )
            triggers = []
            if enemy_groups and has_assets_remaining:
                if force_ratio < 1.5:
                    triggers.append(f"force_ratio {force_ratio} below 1.5")
                if situation.get('threat_level') in ['MODERATE', 'HIGH', 'CRITICAL']:
                    triggers.append(f"threat {situation.get('threat_level')}")

            if triggers:
                worldstate_dict['deployment_directive'] = {
                    'must_deploy_now': True,
                    'triggers': triggers,
                    'assets_available': assets_for_controlled,
                    'force_ratio': force_ratio,
                    'enemy_groups_detected': len(enemy_groups)
                }

        return worldstate_dict

    def _distance_2d(self, pos1, pos2) -> float:
        """Calculate 2D distance between positions"""
        import math
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

    def _format_previous_ao_intel_for_cache(self, ao_data: Dict[str, Any]) -> str:
        """
        Format previous AO intelligence for cached context (system prompt).

        This includes comprehensive tactical analysis and complete order history
        so the new commander can learn from previous performance.
        """
        if not ao_data:
            return ""

        parts = []

        # Summary
        parts.append(f"\nPrevious AO: {ao_data.get('ao_id', 'unknown')}")
        parts.append(f"Map: {ao_data.get('map_name', 'unknown')} | Mission: {ao_data.get('mission_name', 'unknown')}")
        parts.append(f"Outcome: {ao_data.get('outcome', 'UNKNOWN')} | Duration: {ao_data.get('duration_seconds', 0):.1f}s")
        parts.append(f"Objectives: {ao_data.get('objectives_completed', 0)}/{ao_data.get('objectives_total', 0)} completed ({ao_data.get('completion_rate', 0):.1f}%)")

        # Casualties
        if ao_data.get('casualties'):
            cas = ao_data['casualties']
            parts.append(f"\nCasualties:")
            parts.append(f"  Friendly losses: {cas.get('controlled_units_lost', 0)} controlled + {cas.get('allied_units_lost', 0)} allied")
            parts.append(f"  Enemy destroyed: {cas.get('enemy_units_destroyed', 0)}")
            parts.append(f"  Loss ratio: {cas.get('loss_ratio', 0):.2f}:1 (enemy/friendly)")

        # MVP Intel (for HVT tracking)
        if ao_data.get('mvp_player'):
            mvp = ao_data['mvp_player']
            parts.append(f"\nMVP Player (Designate as HVT): {mvp.get('name', 'Unknown')}")
            parts.append(f"  Kills: {mvp.get('kills', 0)} | Objectives secured: {mvp.get('objectives_secured', 0)} | Score: {mvp.get('score', 0)}")

        if ao_data.get('mvp_squad'):
            mvp_sq = ao_data['mvp_squad']
            parts.append(f"MVP Squad (High-value asset): {mvp_sq.get('squad_id', 'Unknown')}")
            parts.append(f"  Kills: {mvp_sq.get('kills', 0)} | Objectives secured: {mvp_sq.get('objectives_secured', 0)}")

        # Tactical Analysis
        parts.append(f"\nTactical Analysis:")

        if ao_data.get('first_objective_targeted'):
            first_target = ao_data['first_objective_targeted']
            parts.append(f"  First objective engaged: {first_target.get('objective_id', 'unknown')} at T+{first_target.get('mission_time', 0)}s")

        if ao_data.get('first_objective_lost'):
            first_lost = ao_data['first_objective_lost']
            parts.append(f"  First objective lost: {first_lost.get('objective_id', 'unknown')} at T+{first_lost.get('mission_time', 0)}s")

        if ao_data.get('objective_engagement_order'):
            order_list = [e['objective_id'] for e in ao_data['objective_engagement_order']]
            parts.append(f"  Engagement priority: {' -> '.join(order_list)}")

        if ao_data.get('longest_fight_location'):
            longest = ao_data['longest_fight_location']
            parts.append(f"  Longest fight: {longest.get('objective_id', 'unknown')} ({longest.get('duration_seconds', 0):.1f}s)")

        if ao_data.get('damage_hotspots'):
            parts.append(f"  Damage hotspots: {len(ao_data['damage_hotspots'])} areas with heavy enemy casualties")
            for i, hotspot in enumerate(ao_data['damage_hotspots'][:3], 1):  # Top 3
                parts.append(f"    {i}. {hotspot.get('area_description', 'Unknown')}: {hotspot.get('enemy_casualties', 0)} casualties")

        # Decision-making metrics
        cycles = ao_data.get('decision_cycles', [])
        if cycles:
            total_orders = sum(c.get('order_count', 0) for c in cycles)
            avg_orders = total_orders / len(cycles) if cycles else 0
            parts.append(f"\nDecision Metrics:")
            parts.append(f"  Total cycles: {len(cycles)} | Orders issued: {total_orders} | Avg per cycle: {avg_orders:.1f}")

        # Complete order summary history (ALL decision cycles)
        if cycles:
            parts.append(f"\n\nCOMPLETE ORDER HISTORY (All {len(cycles)} Decision Cycles):")
            parts.append("=" * 60)
            for cycle_data in cycles:
                cycle_num = cycle_data.get('cycle', 0)
                mission_time = cycle_data.get('mission_time', 0)
                order_count = cycle_data.get('order_count', 0)
                summaries = cycle_data.get('order_summary', [])
                commentary = cycle_data.get('commentary', '')
                threat = cycle_data.get('threat_level', 'UNKNOWN')

                parts.append(f"\n[Cycle {cycle_num} | T+{mission_time}s | Threat: {threat} | {order_count} orders]")

                if summaries:
                    for summary in summaries:
                        parts.append(f"  - {summary}")

                if commentary:
                    parts.append(f"  Commentary: {commentary}")

        # Lessons learned
        if ao_data.get('lessons_learned'):
            parts.append(f"\n\nLessons Learned ({len(ao_data['lessons_learned'])}):")
            for i, lesson in enumerate(ao_data['lessons_learned'], 1):
                parts.append(f"  {i}. {lesson.get('lesson', '')}")

        parts.append("\n" + "=" * 80)
        parts.append("\nUse this intelligence to make better tactical decisions in the current AO.")
        parts.append("Pay special attention to what worked well and what failed in the previous AO.")

        return "\n".join(parts)

    def _format_previous_ao_intel(self, ao_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format previous AO intelligence for the next commander

        Provides a concise summary of what happened in the previous AO so the
        new commander can learn from successes and failures.
        """
        if not ao_data:
            return {}

        # Extract key metrics
        decision_cycles = ao_data.get('decision_cycles', [])
        deployed_assets = ao_data.get('deployed_assets', [])
        objectives = ao_data.get('objectives', [])
        casualties = ao_data.get('casualties', {})
        threat_levels = ao_data.get('threat_levels', [])

        # Summarize decision-making patterns
        total_orders = sum(c.get('order_count', 0) for c in decision_cycles)
        avg_orders_per_cycle = round(total_orders / len(decision_cycles), 1) if decision_cycles else 0

        # Get last 3 order summaries for context
        recent_orders = []
        for cycle in decision_cycles[-3:]:
            if cycle.get('order_summary'):
                recent_orders.extend(cycle['order_summary'][:3])  # Max 3 per cycle

        # Summarize threat progression
        threat_summary = "UNKNOWN"
        if threat_levels:
            first_threat = threat_levels[0].get('level', 'UNKNOWN')
            last_threat = threat_levels[-1].get('level', 'UNKNOWN')
            if first_threat != last_threat:
                threat_summary = f"{first_threat} -> {last_threat}"
            else:
                threat_summary = first_threat

        # Build concise intel package
        intel = {
            'previous_ao_summary': {
                'ao_id': ao_data.get('ao_id', 'unknown'),
                'map': ao_data.get('map_name', 'unknown'),
                'outcome': ao_data.get('outcome', 'UNKNOWN'),
                'duration_seconds': ao_data.get('duration_seconds', 0),
                'objectives_completed': f"{ao_data.get('objectives_completed', 0)}/{ao_data.get('objectives_total', 0)}",
                'completion_rate': ao_data.get('completion_rate', 0)
            },
            'tactical_metrics': {
                'total_decision_cycles': len(decision_cycles),
                'total_orders_issued': total_orders,
                'avg_orders_per_cycle': avg_orders_per_cycle,
                'assets_deployed': len(deployed_assets),
                'threat_progression': threat_summary
            },
            'casualties': casualties if casualties else None,
            'recent_order_patterns': recent_orders[-5:] if recent_orders else [],
            'lessons_learned': ao_data.get('lessons_learned', [])
        }

        # Remove None values
        return {k: v for k, v in intel.items() if v is not None}


    def _assess_situation(self, world_state: WorldState, friendly_groups, enemy_groups) -> Dict[str, Any]:
        """Assess the current battlefield situation with spatial awareness"""
        assessment = {
            'threat_level': 'UNKNOWN',
            'enemy_activity': 'Unknown',
            'recommended_posture': 'DEFENSIVE',
            'spatial_analysis': {}
        }

        if not enemy_groups:
            assessment['threat_level'] = 'MINIMAL'
            assessment['enemy_activity'] = 'No known enemies detected'
            assessment['recommended_posture'] = 'OFFENSIVE'
            return assessment

        # Calculate threat level
        total_enemy_units = sum(g.unit_count for g in enemy_groups)
        total_friendly_units = sum(g.unit_count for g in friendly_groups)

        # Spatial threat analysis - where are the enemies?
        objectives = self.state.objectives if hasattr(self.state, 'objectives') else []
        enemy_near_objectives = 0
        enemy_distant = 0
        objectives_under_threat = []
        critical_objectives_threatened = []
        high_value_objectives_threatened = []

        for obj in objectives:
            if hasattr(obj, 'position') and obj.position:
                enemies_at_obj = [g for g in enemy_groups
                                 if self._distance_2d(g.position, obj.position) < (getattr(obj, 'radius', 300) * 2)]
                if enemies_at_obj:
                    enemy_near_objectives += sum(g.unit_count for g in enemies_at_obj)
                    objectives_under_threat.append(obj.id)

                    # Track priority of threatened objectives
                    if obj.priority >= 90:
                        critical_objectives_threatened.append(obj.id)
                    elif obj.priority >= 70:
                        high_value_objectives_threatened.append(obj.id)

        enemy_distant = total_enemy_units - enemy_near_objectives

        # More nuanced threat assessment considering spatial distribution AND objective priority
        if critical_objectives_threatened:
            # HQ or critical objectives under threat = highest priority but maintain AO control
            assessment['threat_level'] = 'CRITICAL'
            assessment['recommended_posture'] = 'DEFEND_CRITICAL_OBJECTIVES_MAINTAIN_AO_CONTROL'
        elif total_enemy_units > total_friendly_units * 2 and enemy_near_objectives > 0:
            assessment['threat_level'] = 'CRITICAL'
            assessment['recommended_posture'] = 'PRIORITIZE_HIGH_VALUE_OBJECTIVES'
        elif high_value_objectives_threatened and total_enemy_units > total_friendly_units:
            assessment['threat_level'] = 'HIGH'
            assessment['recommended_posture'] = 'DEFEND_HIGH_PRIORITY_WITHDRAW_FROM_LOW'
        elif total_enemy_units > total_friendly_units and enemy_near_objectives > 0:
            assessment['threat_level'] = 'HIGH'
            assessment['recommended_posture'] = 'DEFEND_BY_PRIORITY_SACRIFICE_LOWEST'
        elif enemy_near_objectives > 0 and len(objectives_under_threat) > len(objectives) / 2:
            assessment['threat_level'] = 'MODERATE'
            assessment['recommended_posture'] = 'DEFEND_THREATENED_OBJECTIVES'
        elif total_enemy_units < total_friendly_units / 2 or enemy_distant == total_enemy_units:
            assessment['threat_level'] = 'LOW'
            assessment['recommended_posture'] = 'PROPORTIONAL_RESPONSE'
        else:
            assessment['threat_level'] = 'MODERATE'
            assessment['recommended_posture'] = 'BALANCED'

        # Detailed spatial analysis
        assessment['spatial_analysis'] = {
            'total_enemy_groups': len(enemy_groups),
            'total_enemy_units': total_enemy_units,
            'enemies_near_objectives': enemy_near_objectives,
            'enemies_distant': enemy_distant,
            'objectives_under_threat': objectives_under_threat,
            'critical_objectives_threatened': critical_objectives_threatened,
            'high_value_objectives_threatened': high_value_objectives_threatened,
            'threat_distribution': 'CONCENTRATED' if len(objectives_under_threat) <= 1 else 'DISPERSED'
        }

        # Activity description with spatial context and priority awareness
        if critical_objectives_threatened:
            assessment['enemy_activity'] = f"{len(enemy_groups)} enemy groups detected - CRITICAL THREAT: {', '.join(critical_objectives_threatened)} under attack!"
        elif high_value_objectives_threatened:
            assessment['enemy_activity'] = f"{len(enemy_groups)} enemy groups detected - HIGH-PRIORITY objectives threatened: {', '.join(high_value_objectives_threatened)}"
        elif len(objectives_under_threat) > 0:
            assessment['enemy_activity'] = f"{len(enemy_groups)} enemy groups detected - {len(objectives_under_threat)} objective(s) under threat: {', '.join(objectives_under_threat)}"
        else:
            assessment['enemy_activity'] = f"{len(enemy_groups)} enemy groups detected - ALL distant from objectives (reconnaissance or staging)"

        return assessment

    def _group_to_dict(self, group, detailed=True, objectives=None, enemy_groups=None, friendly_groups=None) -> Dict[str, Any]:
        """Convert Group to dictionary with variable detail level and spatial context"""
        import math

        group_type = getattr(group, 'type', 'unknown')
        base = {
            'id': group.id,
            'type': group_type,
            'side': group.side,
            'position': [round(group.position[0]), round(group.position[1])],
            'unit_count': group.unit_count
        }

        # Vehicle/role hints
        veh_types = ['motorized', 'mechanized', 'armor', 'air_rotary', 'air_fixed', 'naval']
        base['is_vehicle'] = group_type in veh_types
        base['is_air'] = group_type in ['air_rotary', 'air_fixed']
        base['is_armor'] = group_type in ['armor', 'mechanized']
        base['can_transport'] = group_type in ['motorized', 'mechanized', 'armor', 'air_rotary', 'air_fixed']

        # Add spatial awareness - distances to objectives
        if objectives:
            objective_distances = []
            for obj in objectives:
                if hasattr(obj, 'position') and obj.position:
                    dist = math.sqrt((group.position[0] - obj.position[0])**2 + (group.position[1] - obj.position[1])**2)
                    objective_distances.append({
                        'objective_id': obj.id,
                        'distance_m': round(dist)
                    })
            if objective_distances:
                # Sort by distance
                objective_distances.sort(key=lambda x: x['distance_m'])
                base['nearest_objectives'] = objective_distances[:3]  # Top 3 closest

        # Add distances to nearest enemies (for friendly groups)
        if enemy_groups:
            nearest_enemy = None
            min_dist = float('inf')
            for enemy in enemy_groups:
                dist = math.sqrt((group.position[0] - enemy.position[0])**2 + (group.position[1] - enemy.position[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_enemy = {'id': enemy.id, 'distance_m': round(dist), 'type': getattr(enemy, 'type', 'unknown')}
            if nearest_enemy:
                base['nearest_enemy'] = nearest_enemy

        # Add distances to nearest friendlies (for enemy groups)
        if friendly_groups:
            nearest_friendly = None
            min_dist = float('inf')
            for friendly in friendly_groups:
                dist = math.sqrt((group.position[0] - friendly.position[0])**2 + (group.position[1] - friendly.position[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_friendly = {'id': friendly.id, 'distance_m': round(dist), 'type': getattr(friendly, 'type', 'unknown')}
            if nearest_friendly:
                base['nearest_friendly'] = nearest_friendly

        if detailed:
            # Detailed info for controlled/allied groups
            base['behavior'] = getattr(group, 'behaviour', 'AWARE')  # Note: 'behaviour' not 'behavior'
            base['combat_mode'] = getattr(group, 'combat_mode', 'YELLOW')
            base['formation'] = getattr(group, 'formation', 'WEDGE')
            base['speed_mode'] = getattr(group, 'speed_mode', 'NORMAL')
            base['is_player_group'] = getattr(group, 'is_player_group', False)
            base['is_friendly'] = getattr(group, 'is_friendly', False)
            base['in_combat'] = getattr(group, 'in_combat', False)

            # Current waypoint/order information
            wp_type = getattr(group, 'current_waypoint_type', '')
            wp_pos = getattr(group, 'current_waypoint_pos', [])
            if wp_type:
                base['current_order'] = {
                    'type': wp_type,
                    'position': [round(wp_pos[0]), round(wp_pos[1])] if len(wp_pos) >= 2 else []
                }
            else:
                base['current_order'] = None

            # NVG capability
            nvg_cap = getattr(group, 'avg_night_capability', 0.0)
            base['nvg_capability'] = round(nvg_cap * 100)  # As percentage

            # Known enemies visible to this group
            if hasattr(group, 'known_enemies') and group.known_enemies:
                base['known_enemies'] = [
                    {
                        'id': e.id,
                        'type': e.type,
                        'position': [round(e.position[0]), round(e.position[1])],
                        'units': e.unit_count,
                        'distance': round(
                            ((group.position[0] - e.position[0])**2 +
                             (group.position[1] - e.position[1])**2) ** 0.5
                        )
                    }
                    for e in group.known_enemies[:5]  # Top 5 closest threats
                ]
                base['enemy_threat_level'] = len(group.known_enemies)
        else:
            # Less detailed info for enemy groups (still useful context)
            base['behaviour'] = getattr(group, 'behaviour', 'AWARE')
            base['in_combat'] = getattr(group, 'in_combat', False)
            base['knowledge'] = getattr(group, 'knowledge', 0.0)

        return base

    def _record_order_history(self, world_state: WorldState, objectives: List[ObjectiveState], commands: List[Command]):
        """Record order history for context continuity in LLM calls"""
        history_entry = {
            'cycle': self.decision_cycle,
            'mission_time': round(world_state.mission_time),
            'objectives_count': len(objectives),
            'commands_count': len(commands),
            'command_types': {},
            'commentary': f"Cycle {self.decision_cycle}: Issued {len(commands)} commands"
        }

        # Count command types
        for cmd in commands:
            cmd_type = cmd.type.value
            history_entry['command_types'][cmd_type] = history_entry['command_types'].get(cmd_type, 0) + 1

        # Add to history (keep last N entries)
        self.order_history.append(history_entry)
        if len(self.order_history) > self.max_history_entries:
            self.order_history = self.order_history[-self.max_history_entries:]

    def _build_cached_context(self, objectives: List[ObjectiveState]) -> str:
        """
        Build the cached context that includes static/slow-changing content:
        - System prompt (static tactical guidelines)
        - Current active objectives (slow-changing)
        - Previous AO intelligence (set once at AO start, then cached)

        This gets cached by LLM providers and reused until objectives change.
        """
        context_parts = []

        # Part 1: System prompt (static)
        context_parts.append(self.system_prompt)

        # Part 2: Previous AO Intelligence (if available - only added once at AO start)
        previous_ao = self.state.get_previous_ao_intel()
        if previous_ao:
            context_parts.append("\n\n" + "=" * 80)
            context_parts.append("\n**INTELLIGENCE FROM PREVIOUS AO (LESSONS LEARNED)**\n")
            context_parts.append("=" * 80)
            context_parts.append("\n")
            context_parts.append(self._format_previous_ao_intel_for_cache(previous_ao))
            # Clear it after using so it doesn't persist indefinitely
            self.state.clear_previous_ao_intel()
            logger.info("Added previous AO intelligence to cached context (will be cached for this AO)")

        # Part 3: Current Mission Objectives (slow-changing - only changes when objectives are added/removed/modified)
        context_parts.append("\n\n" + "=" * 80)
        context_parts.append("\n**CURRENT MISSION OBJECTIVES**\n")
        context_parts.append("=" * 80)

        if objectives:
            for obj in objectives:
                obj_dict = self._objective_to_dict(obj)
                context_parts.append(f"\n\nObjective: {obj_dict['id']}")
                context_parts.append(f"  Description: {obj_dict['description']}")
                context_parts.append(f"  Priority: {obj_dict['priority']}")
                context_parts.append(f"  State: {obj_dict['state']}")
                if 'position' in obj_dict:
                    context_parts.append(f"  Position: {obj_dict['position']}")
                if 'radius' in obj_dict:
                    context_parts.append(f"  Radius: {obj_dict['radius']}m")
                if 'metadata' in obj_dict and obj_dict['metadata']:
                    context_parts.append(f"  Metadata: {json.dumps(obj_dict['metadata'])}")
        else:
            context_parts.append("\nNo active objectives currently.")

        return "".join(context_parts)

    def _objectives_hash(self, objectives: List[ObjectiveState]) -> str:
        """Compute hash of objectives to detect when cache needs updating"""
        obj_strings = []
        for obj in sorted(objectives, key=lambda o: o.id):
            obj_strings.append(f"{obj.id}:{obj.state.value}:{obj.priority}:{obj.description}")
        return hashlib.md5("|".join(obj_strings).encode()).hexdigest()

    def _objective_to_dict(self, objective: ObjectiveState) -> Dict[str, Any]:
        """Convert Objective to dictionary with full context and priority guidance"""
        priority = objective.priority

        # Add priority tier description for LLM clarity
        if priority >= 90:
            priority_tier = "CRITICAL"
            allocation_guidance = "Primary focus - allocate 30-40% of available forces"
        elif priority >= 70:
            priority_tier = "HIGH"
            allocation_guidance = "Major objective - allocate 20-30% of available forces"
        elif priority >= 50:
            priority_tier = "MEDIUM"
            allocation_guidance = "Important but not critical - allocate 10-20% of forces"
        elif priority >= 30:
            priority_tier = "LOW"
            allocation_guidance = "Secondary objective - allocate 5-10% of forces, acceptable to sacrifice"
        else:
            priority_tier = "MINIMAL"
            allocation_guidance = "Tertiary objective - minimal forces, easily sacrificed if needed"

        obj_dict = {
            'id': objective.id,
            'description': objective.description,
            'priority': objective.priority,
            'priority_tier': priority_tier,
            'force_allocation_guidance': allocation_guidance,
            'state': objective.state.value if hasattr(objective.state, 'value') else str(objective.state)
        }

        # Add task type for tactical guidance
        if hasattr(objective, 'task_type') and objective.task_type:
            obj_dict['task_type'] = objective.task_type

            # Special guidance for HQ
            if objective.task_type == 'defend_hq':
                obj_dict['strategic_note'] = "COMMANDER LOCATION - Highest individual priority. Defend strongly but maintain AO control. If lost, can recapture or fortify other objectives."

        # Add position if available
        if hasattr(objective, 'position') and objective.position:
            obj_dict['position'] = [round(objective.position[0]), round(objective.position[1])]

        # Add radius if available
        if hasattr(objective, 'radius') and objective.radius:
            obj_dict['radius'] = round(objective.radius)

        # Add metadata if available
        if hasattr(objective, 'metadata') and objective.metadata:
            obj_dict['metadata'] = objective.metadata

        return obj_dict

    def start_ao_tracking(self, ao_id: str, map_name: str = 'unknown', mission_name: str = 'unknown', ao_number: int = 0):
        """
        Start AO tracking for order history and API logging

        Args:
            ao_id: AO identifier
            map_name: Map name (e.g., "Altis", "Tanoa")
            mission_name: Mission name (e.g., "Defend_Base")
            ao_number: AO sequence number
        """
        # Start API call logging
        self.api_logger.start_ao(ao_id, map_name, mission_name, ao_number)
        logger.info(f'Commander AO tracking started: {ao_id}')

    def end_ao_tracking(self):
        """End AO tracking and finalize logs"""
        # Finalize API call log
        self.api_logger.end_ao()
        logger.info('Commander AO tracking ended')

    def get_status(self):
        """Get commander status"""
        return {
            'decision_cycle': self.decision_cycle,
            'active_assignments': len(self.current_assignments),
            'deployed': self.state.is_deployed(),
            'ao_active': self.state.is_ao_active(),
            'api_log_file': self.api_logger.get_log_file_path()
        }
