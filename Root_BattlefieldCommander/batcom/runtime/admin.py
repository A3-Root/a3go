"""
Admin command handlers

Processes admin commands from the debug console.
"""

import logging
import json
from typing import Any, Dict
from .state import StateManager
from ..models.objectives import Objective, ObjectiveType, ObjectiveState

logger = logging.getLogger('batcom.runtime.admin')


class AdminCommandHandler:
    """
    Handles admin commands from SQF
    """

    def __init__(self, state_manager: StateManager, commander=None, guardrails_path: str = None):
        self.state = state_manager
        self.commander = commander  # Reference to batcom for token stats
        self.guardrails_path = guardrails_path

    def handle_command(self, command: str, params: Any, flag: bool) -> Dict[str, Any]:
        """
        Route and handle admin command

        Args:
            command: Command identifier
            params: Command parameters
            flag: Additional boolean flag

        Returns:
            Result dictionary with status and message
        """
        logger.info('Admin command received: %s', command)

        try:
            if command == "commanderBrief":
                return self._handle_mission_init(params, flag)
            elif command == "commanderAllies":
                return self._handle_ai_friends_with(params)
            elif command == "commanderSides":
                return self._handle_ai_control_side(params)
            elif command == "setGeminiApiKey":
                return self._handle_set_gemini_api_key(params)
            elif command == "setLLMApiKey":
                return self._handle_set_llm_api_key(params)
            elif command == "setLLMConfig":
                return self._handle_set_llm_config(params)
            elif command == "deployCommander":
                return self._handle_deploy_commander(flag)
            elif command == "commanderTask":
                return self._handle_mission_objective(params)
            elif command == "getTokenStats":
                return self._handle_get_token_stats()
            elif command == "commanderGuardrails":
                return self._handle_guardrails(params)
            elif command == "commanderControlGroups":
                return self._handle_control_groups(params)
            elif command == "commanderStartAO":
                return self._handle_start_ao(params)
            elif command == "commanderEndAO":
                return self._handle_end_ao()
            elif command == "commanderSetHVT":
                return self._handle_set_hvt(params)
            elif command == "aoProgress":
                return self._handle_ao_progress(params)
            elif command == "setThinkingConfig":
                return self._handle_set_thinking_config(params)
            elif command == "toggleThinking":
                return self._handle_toggle_thinking(flag)
            elif command == "emergencyStop":
                return self._handle_emergency_stop()
            else:
                return {
                    "status": "error",
                    "error": f"Unknown command: {command}"
                }

        except Exception as e:
            logger.exception('Error handling admin command: %s', command)
            return {
                "status": "error",
                "error": str(e)
            }

    def _handle_mission_init(self, intent: str, clear_memory: bool) -> Dict[str, Any]:
        """Handle commanderBrief command"""
        if not intent or not isinstance(intent, str):
            return {
                "status": "error",
                "error": "Mission intent must be a non-empty string"
            }

        self.state.set_mission_intent(intent, clear_memory)

        return {
            "status": "ok",
            "message": f"Mission intent set{' (memory cleared)' if clear_memory else ''}"
        }

    def _handle_ai_friends_with(self, sides: list) -> Dict[str, Any]:
        """Handle commanderAllies command"""
        if not isinstance(sides, list):
            return {
                "status": "error",
                "error": "Sides must be an array"
            }

        self.state.set_friendly_sides(sides)

        return {
            "status": "ok",
            "message": f"Friendly sides set: {', '.join(sides)}"
        }

    def _handle_ai_control_side(self, sides: list) -> Dict[str, Any]:
        """Handle commanderSides command"""
        if not isinstance(sides, list):
            return {
                "status": "error",
                "error": "Sides must be an array"
            }

        self.state.set_controlled_sides(sides)

        return {
            "status": "ok",
            "message": f"Controlled sides set: {', '.join(sides)}"
        }

    def _handle_set_gemini_api_key(self, api_key: Any) -> Dict[str, Any]:
        """Handle setGeminiApiKey command"""
        if not isinstance(api_key, str) or not api_key:
            return {
                "status": "error",
                "error": "API key must be a non-empty string"
            }

        self.state.set_api_key("gemini", api_key)

        return {
            "status": "ok",
            "message": "Gemini API key updated"
        }

    def _handle_set_llm_api_key(self, params: Any) -> Dict[str, Any]:
        """Handle setLLMApiKey command - params: [provider, key, extras (optional hashmap)]"""
        if not isinstance(params, list) or len(params) < 2:
            return {
                "status": "error",
                "error": "Usage: [provider, key, extras]"
            }

        provider = params[0]
        api_key = params[1]
        extras = params[2] if len(params) > 2 and isinstance(params[2], dict) else {}

        if not isinstance(provider, str) or not provider:
            return {"status": "error", "error": "Provider must be a string"}
        if not isinstance(api_key, str) or not api_key:
            return {"status": "error", "error": "API key must be a non-empty string"}

        # Store key and merge extras/runtime settings so they persist
        self.state.update_ai_config({"provider": provider, "api_key": api_key, **extras})
        self._persist_llm_config()

        return {
            "status": "ok",
            "message": f"{provider} API key updated"
        }

    def _handle_set_llm_config(self, params: Any) -> Dict[str, Any]:
        """Handle setLLMConfig command - params should be a dict/hashmap"""
        if not isinstance(params, dict):
            return {
                "status": "error",
                "error": "LLM config must be a hashmap/dictionary"
            }

        try:
            self.state.update_ai_config(params)
            self._persist_llm_config()
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

        provider = (params.get("provider") or "gemini").upper()
        return {
            "status": "ok",
            "message": f"LLM config updated for {provider}"
        }

    def _handle_deploy_commander(self, deploy: bool) -> Dict[str, Any]:
        """Handle deployCommander command"""
        if deploy:
            # Validate configuration
            if not self.state.controlled_sides:
                return {
                    "status": "error",
                    "error": "No controlled sides configured. Use commanderSides first."
                }

            self.state.deploy()

            return {
                "status": "ok",
                "message": "Commander deployed - AI is now active"
            }
        else:
            self.state.undeploy()

            return {
                "status": "ok",
                "message": "Commander undeployed - AI is now inactive"
            }

    def _persist_llm_config(self):
        """Persist current runtime AI config to guardrails file (including API key)"""
        if not self.guardrails_path:
            return

        try:
            current = dict(self.state.runtime_ai_config)
            if not current:
                return

            provider = (current.get("provider") or "gemini").lower()
            # Pull key from runtime config or state api_keys
            if "api_key" not in current or not current.get("api_key"):
                key_entry = self.state.api_keys.get(provider) or {}
                if key_entry.get("key"):
                    current["api_key"] = key_entry["key"]

            # Preserve existing templates from file
            templates = {}
            try:
                with open(self.guardrails_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if isinstance(existing, dict):
                        templates = existing.get("templates", {})
            except FileNotFoundError:
                templates = {}
            except Exception as read_err:
                logger.warning("Failed reading guardrails for templates: %s", read_err)

            data = {
                "current": current,
                "templates": templates
            }

            with open(self.guardrails_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
            logger.info("Persisted LLM config (provider=%s) to %s", provider, self.guardrails_path)
        except Exception as e:
            logger.warning("Failed to persist LLM config to %s: %s", self.guardrails_path, e)

    def _handle_mission_objective(self, params: Any) -> Dict[str, Any]:
        """
        Handle commanderTask command - supports both legacy array format and new hashmap format

        Legacy format: [description, unit_classes, priority, position?, radius?]
        New format: hashmap with keys: description, priority, position?, radius?, unit_classes?,
                    target_unit?, target_group?, patrol_waypoints?, metadata?
        """
        # Support both legacy array format and new hashmap format
        if isinstance(params, dict):
            # New flexible hashmap format
            description = params.get('description', '')
            priority = params.get('priority', 5)
            position = params.get('position', [])
            radius = params.get('radius', 0)
            unit_classes = params.get('unit_classes', [])

            # Extract additional metadata
            metadata = params.get('metadata', {})

            # Add common fields to metadata if provided
            if 'target_unit' in params:
                metadata['target_unit'] = params['target_unit']
            if 'target_group' in params:
                metadata['target_group'] = params['target_group']
            if 'patrol_waypoints' in params:
                metadata['patrol_waypoints'] = params['patrol_waypoints']
            if 'area_center' in params:
                metadata['area_center'] = params['area_center']
            if 'area_radius' in params:
                metadata['area_radius'] = params['area_radius']
            if 'spawn_assets' in params:
                metadata['spawn_assets'] = params['spawn_assets']
            if 'task_type' in params:
                metadata['task_type'] = params['task_type']

        elif isinstance(params, list) and len(params) >= 3:
            # Legacy array format: [description, unit_classes, priority, position?, radius?]
            description = params[0]
            unit_classes = params[1] if len(params) > 1 else []
            priority = params[2] if len(params) > 2 else 5
            position = params[3] if len(params) > 3 else []
            radius = params[4] if len(params) > 4 else 0
            metadata = {}
        else:
            return {
                "status": "error",
                "error": "Mission objective requires either [description, unit_classes, priority] or hashmap with 'description' and 'priority'"
            }

        if not description or not isinstance(description, str):
            return {
                "status": "error",
                "error": "Objective description must be a non-empty string"
            }

        # Attempt to parse coordinates from description if no position provided
        if (not position or not isinstance(position, list)) and isinstance(description, str):
            import re
            match = re.search(r'\[([0-9\.\-,\s]+)\]', description)
            if match:
                try:
                    parts = match.group(1).split(',')
                    if len(parts) >= 2:
                        nums = [float(p) for p in parts]
                        # pad to 3 values
                        while len(nums) < 3:
                            nums.append(0.0)
                        position = nums[:3]
                except Exception:
                    pass

        # If still no position, try mission intent text
        if (not position or not isinstance(position, list)) and isinstance(self.state.mission_intent, str):
            import re
            match = re.search(r'\[([0-9\.\-,\s]+)\]', self.state.mission_intent)
            if match:
                try:
                    parts = match.group(1).split(',')
                    if len(parts) >= 2:
                        nums = [float(p) for p in parts]
                        while len(nums) < 3:
                            nums.append(0.0)
                        position = nums[:3]
                except Exception:
                    pass

        # Create objective
        obj_id = f"OBJ_RUNTIME_{len(self.state.objectives) + 1}"
        objective = Objective(
            id=obj_id,
            type=ObjectiveType.CUSTOM,
            description=description,
            priority=priority,
            unit_classes=unit_classes if isinstance(unit_classes, list) else [],
            position=position if isinstance(position, list) else [],
            radius=radius if isinstance(radius, (int, float)) else 0,
            state=ObjectiveState.PENDING,
            metadata=metadata
        )

        self.state.add_objective(objective)

        return {
            "status": "ok",
            "message": f"Objective added: {description} (priority: {priority})"
        }

    def _handle_get_token_stats(self) -> Dict[str, Any]:
        """Handle getTokenStats command - returns token usage statistics"""
        if not self.commander:
            return {
                "status": "error",
                "error": "Commander not initialized"
            }

        if not hasattr(self.commander, 'token_tracker'):
            return {
                "status": "error",
                "error": "Token tracker not available"
            }

        try:
            stats = self.commander.token_tracker.get_stats()

            # Log formatted stats to console
            formatted_stats = self.commander.token_tracker.get_stats_formatted()
            logger.info("\n" + formatted_stats)

            return {
                "status": "ok",
                "stats": stats,
                "message": "Token statistics retrieved (see logs for formatted output)"
            }

        except Exception as e:
            logger.exception("Error getting token stats")
            return {
                "status": "error",
                "error": f"Failed to get token stats: {str(e)}"
            }

    def _handle_guardrails(self, params: Any) -> Dict[str, Any]:
        """Handle commanderGuardrails (AO bounds and resource pool)"""
        if not isinstance(params, dict):
            return {"status": "error", "error": "Guardrails must be a hashmap/dictionary"}

        ao = params.get("ao_bounds") or params.get("ao") or params.get("bounds")
        resources = params.get("resources") or params.get("resource_pool")

        if ao:
            try:
                self.state.set_ao_bounds(ao)
            except Exception as e:
                return {"status": "error", "error": f"Invalid AO bounds: {e}"}

        if resources:
            try:
                self.state.set_resource_pool(resources)
            except Exception as e:
                return {"status": "error", "error": f"Invalid resource pool: {e}"}

        return {
            "status": "ok",
            "message": "Guardrails updated",
            "ao_bounds": ao or self.state.ao_bounds,
            "resources": list(resources.keys()) if isinstance(resources, dict) else None
        }

    def _handle_control_groups(self, params: Any) -> Dict[str, Any]:
        """Handle commanderControlGroups to mark specific groups as controllable"""
        if not isinstance(params, (list, tuple, set)):
            return {"status": "error", "error": "Control groups must be an array of group ids"}

        try:
            group_ids = [str(g) for g in params]
            self.state.set_controlled_group_overrides(group_ids)
        except Exception as e:
            return {"status": "error", "error": str(e)}

        return {
            "status": "ok",
            "message": f"Control overrides updated ({len(params)} groups)"
        }

    def _handle_start_ao(self, params) -> Dict[str, Any]:
        """Handle commanderStartAO command"""
        # Handle both old string format and new dict format for backwards compatibility
        if isinstance(params, str):
            # Old format: just ao_id as string
            ao_id = params
            map_name = 'unknown'
            mission_name = 'unknown'
        elif isinstance(params, dict):
            # New format: dict with ao_id, world_name, mission_name
            ao_id = params.get('ao_id', '')
            map_name = params.get('world_name', 'unknown')
            full_mission_name = params.get('mission_name', 'unknown')

            # Extract just the mission name without the map suffix (e.g., "apex_jsoc_mission" from "apex_jsoc_mission.Altis")
            if isinstance(full_mission_name, str) and '.' in full_mission_name:
                mission_name = full_mission_name.split('.')[0]
            else:
                mission_name = full_mission_name
        else:
            return {"status": "error", "error": "Invalid parameters for commanderStartAO"}

        if not ao_id:
            return {"status": "error", "error": "AO ID must be a non-empty string"}

        # Extract AO number from ao_id if it contains a number
        import re
        ao_number = 0
        ao_num_match = re.search(r'(\d+)', ao_id)
        if ao_num_match:
            ao_number = int(ao_num_match.group(1))

        # Start AO tracking in state manager
        self.state.start_ao(ao_id, map_name, mission_name, ao_number)

        # Start API logging in commander (file will be created on first LLM call)
        if self.commander:
            self.commander.start_ao_tracking(ao_id, map_name, mission_name, ao_number)

        return {
            "status": "ok",
            "message": f"AO tracking started: {ao_id}"
        }

    def _handle_end_ao(self) -> Dict[str, Any]:
        """Handle commanderEndAO command"""
        ao_data = self.state.end_ao()

        if not ao_data:
            return {"status": "error", "error": "No active AO to end"}

        # Return HVT designations to SQF
        hvt_data = {
            "players": ao_data.hvt_players,
            "groups": ao_data.hvt_groups
        }

        return {
            "status": "ok",
            "message": f"AO ended: {ao_data.ao_id}",
            "hvt_data": hvt_data,
            "analysis": {
                "duration": ao_data.duration,
                "blufor_casualties": ao_data.blufor_casualties,
                "ai_casualties": ao_data.ai_casualties,
                "objectives_lost": ao_data.objectives_lost,
                "objectives_held": ao_data.objectives_held
            }
        }

    def _handle_set_hvt(self, params: Any) -> Dict[str, Any]:
        """Handle commanderSetHVT - manually designate HVTs"""
        if not isinstance(params, dict):
            return {"status": "error", "error": "HVT params must be a hashmap"}

        player_uids = params.get("players", [])
        group_ids = params.get("groups", [])

        # Store HVT designations (to be applied to next world scan)
        if not hasattr(self.state, 'hvt_designations'):
            self.state.hvt_designations = {}

        self.state.hvt_designations = {
            "players": player_uids,
            "groups": group_ids
        }

        return {
            "status": "ok",
            "message": f"HVT designations updated: {len(player_uids)} players, {len(group_ids)} groups"
        }

    def _handle_ao_progress(self, params: Any) -> Dict[str, Any]:
        """
        Handle aoProgress - record objective completion events

        Expected params format (list or dict):
        List: ["eventType", "playerUID", "objectiveID", "objectiveType", "completionMethod", nearbyPlayers]
        Dict: {"event": str, "player": str, "objective": str, "type": str, "method": str, "nearby": []}

        Event types:
        - "commanderKilled": HQ commander killed
        - "commanderCaptured": HQ commander captured alive (more valuable)
        - "hvtEliminated": HVT killed
        - "hvtCaptured": HVT captured alive (more valuable)
        - "radioTowerDestroyed": Radio tower destroyed
        - "radioTowerNeutralized": Radio tower disabled
        - "gpsJammerDestroyed": GPS jammer destroyed
        - "gpsJammerDisabled": GPS jammer disabled by engineer
        - "supplyDepotCaptured": Supply depot captured
        - "mortarPitNeutralized": Mortar pit neutralized (gunners eliminated)
        - "aaSiteDestroyed": AA site destroyed
        - "hmgTowerNeutralized": HMG tower neutralized
        """
        # Handle dict format
        if isinstance(params, dict):
            event_type = params.get("event", "")
            player_uid = params.get("player", "")
            objective_id = params.get("objective", event_type)
            objective_type = params.get("type", self._infer_objective_type(event_type))
            completion_method = params.get("method", self._infer_completion_method(event_type))
            nearby_players_data = params.get("nearby", [])
        # Handle list format
        elif isinstance(params, list):
            if len(params) < 2:
                return {
                    "status": "error",
                    "error": "Usage: aoProgress expects [eventType, playerUID, objectiveID (opt), objectiveType (opt), completionMethod (opt), nearbyPlayers (opt)]"
                }
            event_type = params[0]
            player_uid = params[1]
            objective_id = params[2] if len(params) > 2 else event_type
            objective_type = params[3] if len(params) > 3 else self._infer_objective_type(event_type)
            completion_method = params[4] if len(params) > 4 else self._infer_completion_method(event_type)
            nearby_players_data = params[5] if len(params) > 5 else []
        else:
            return {
                "status": "error",
                "error": "params must be list or dict"
            }

        # Get player info from current world state
        player_name = "Unknown"
        group_id = "Unknown"
        if hasattr(self.state, 'world_state') and self.state.world_state:
            for player in self.state.world_state.players:
                if player.uid == player_uid:
                    player_name = player.name
                    group_id = player.group_id
                    break

        # Process nearby players (format: [[uid, name, group_id], ...])
        nearby_players = []
        if nearby_players_data and isinstance(nearby_players_data, list):
            for nearby in nearby_players_data:
                if isinstance(nearby, list) and len(nearby) >= 3:
                    nearby_players.append([nearby[0], nearby[1], nearby[2]])

        # Record the completion
        tracker = self.state.effectiveness_tracker
        tracker.record_objective_completion(
            objective_id=objective_id,
            objective_type=objective_type,
            player_uid=player_uid,
            player_name=player_name,
            group_id=group_id,
            completion_method=completion_method,
            nearby_players=nearby_players
        )

        bonus_msg = f" (+{len(nearby_players)} proximity bonuses)" if nearby_players else ""
        return {
            "status": "ok",
            "message": f"Recorded {event_type} by {player_name} on {objective_id}{bonus_msg}"
        }

    def _infer_objective_type(self, event_type: str) -> str:
        """Infer objective type from event type"""
        mapping = {
            "commanderKilled": "defend_hq",
            "commanderCaptured": "defend_hq",
            "hvtEliminated": "defend_hvt",
            "hvtCaptured": "defend_hvt",
            "radioTowerDestroyed": "defend_radiotower",
            "radioTowerNeutralized": "defend_radiotower",
            "gpsJammerDestroyed": "defend_gps_jammer",
            "gpsJammerDisabled": "defend_gps_jammer",
            "supplyDepotCaptured": "defend_supply_depot",
            "mortarPitNeutralized": "defend_mortar_pit",
            "aaSiteDestroyed": "defend_aa_site",
            "hmgTowerNeutralized": "defend_hmg_tower"
        }
        return mapping.get(event_type, "unknown")

    def _infer_completion_method(self, event_type: str) -> str:
        """Infer completion method from event type"""
        if "Captured" in event_type:
            return "captured"
        elif "Killed" in event_type or "Eliminated" in event_type:
            return "killed"
        elif "Destroyed" in event_type:
            return "destroyed"
        elif "Disabled" in event_type:
            return "disabled"
        elif "Neutralized" in event_type:
            return "neutralized"
        return "completed"

    def _handle_set_thinking_config(self, params: Any) -> Dict[str, Any]:
        """
        Handle setThinkingConfig command

        Updates Gemini thinking/reasoning configuration.

        Expected params (hashmap):
        {
            "enabled": true/false,
            "mode": "native_sdk" or "openai_compat",
            "budget": -1 (dynamic), 0 (disabled), or 512-24576,
            "level": "low" or "high" (Gemini 3),
            "reasoning_effort": "minimal"|"low"|"medium"|"high"|"none",
            "include_thoughts": true/false,
            "log_thoughts_to_file": true/false
        }
        """
        if not isinstance(params, dict):
            return {
                "status": "error",
                "error": "Thinking config must be a hashmap/dict"
            }

        # Validate thinking mode if provided
        if 'mode' in params:
            mode = params['mode']
            if mode not in ['native_sdk', 'openai_compat']:
                return {
                    "status": "error",
                    "error": f"Invalid thinking_mode: {mode}. Must be 'native_sdk' or 'openai_compat'"
                }

        # Build update dict from provided params
        update = {}
        if 'enabled' in params:
            update['thinking_enabled'] = bool(params['enabled'])
        if 'mode' in params:
            update['thinking_mode'] = params['mode']
        if 'budget' in params:
            try:
                update['thinking_budget'] = int(params['budget'])
            except (ValueError, TypeError):
                return {"status": "error", "error": "thinking_budget must be an integer"}
        if 'level' in params:
            update['thinking_level'] = params['level']
        if 'reasoning_effort' in params:
            update['reasoning_effort'] = params['reasoning_effort']
        if 'include_thoughts' in params:
            update['include_thoughts'] = bool(params['include_thoughts'])
        if 'log_thoughts_to_file' in params:
            update['log_thoughts_to_file'] = bool(params['log_thoughts_to_file'])

        # Apply update to state
        self.state.update_ai_config(update)

        # Persist to guardrails.json
        self._persist_llm_config()

        # Reinitialize LLM client with new config
        if self.commander:
            self.commander._init_llm()

        logger.info("Thinking config updated: %s", update)

        return {
            "status": "ok",
            "message": f"Thinking configuration updated (mode: {update.get('thinking_mode', 'unchanged')})",
            "config": update
        }

    def _handle_toggle_thinking(self, enabled: bool) -> Dict[str, Any]:
        """
        Handle toggleThinking command

        Quick enable/disable thinking without changing other settings.

        Args:
            enabled: True to enable thinking, False to disable
        """
        # Update state
        self.state.update_ai_config({'thinking_enabled': enabled})

        # Persist to guardrails.json
        self._persist_llm_config()

        # Reinitialize LLM client
        if self.commander:
            self.commander._init_llm()

        status_msg = "enabled" if enabled else "disabled"
        logger.info("Thinking %s via toggleThinking command", status_msg)

        return {
            "status": "ok",
            "message": f"Thinking {status_msg}",
            "thinking_enabled": enabled
        }

    def _handle_emergency_stop(self) -> Dict[str, Any]:
        """
        Handle emergencyStop command - HARD KILL SWITCH

        Immediately stops all LLM operations and clears all context/caches/conversation history.
        
        This will:
        1. Disable LLM completely (circuit breaker open)
        2. Clear all conversation context and caches
        3. Reset order history
        4. Clear previous AO intelligence
        5. Reset all LLM client state

        After this, you'll need to either:
        - Call deployCommander again to restart with fresh state
        - Restart the mission to reinitialize BATCOM
        """
        logger.warning("=" * 80)
        logger.warning("EMERGENCY STOP ACTIVATED - Shutting down LLM operations")
        logger.warning("=" * 80)

        try:
            # 1. Open circuit breaker to prevent any new LLM calls
            if self.commander:
                self.commander.llm_circuit_open = True
                self.commander.llm_enabled = False
                self.commander.fatal_error = False  # Clear fatal error if set
                logger.warning("LLM circuit breaker opened - all LLM calls disabled")

                # 2. Clear conversation history and order summaries
                self.commander.order_summaries = []
                self.commander.order_history = []
                logger.warning("Cleared order history and summaries")

                # 3. Clear LLM client caches
                if self.commander.llm_client:
                    # Clear OpenAI conversation state
                    if hasattr(self.commander.llm_client, '_cached_system_prompt'):
                        self.commander.llm_client._cached_system_prompt = None
                    if hasattr(self.commander.llm_client, '_cached_system_prompt_hash'):
                        self.commander.llm_client._cached_system_prompt_hash = None
                    if hasattr(self.commander.llm_client, '_prompt_cache_key'):
                        self.commander.llm_client._prompt_cache_key = None
                    logger.warning("Cleared LLM client caches")

                    # Clear Gemini caches if present
                    if hasattr(self.commander.llm_client, 'delete_all_caches'):
                        try:
                            self.commander.llm_client.delete_all_caches()
                            logger.warning("Deleted all Gemini caches")
                        except Exception as e:
                            logger.warning(f"Failed to delete Gemini caches: {e}")

                # 4. Reset cached context tracking
                self.commander.last_cached_objectives = None
                logger.warning("Reset cached context tracking")

            # 5. Clear previous AO intelligence
            if self.state:
                self.state.previous_ao_intel = None
                logger.warning("Cleared previous AO intelligence")

            # 6. Undeploy commander
            self.state.undeploy()
            logger.warning("Commander undeployed")

            logger.warning("=" * 80)
            logger.warning("EMERGENCY STOP COMPLETE")
            logger.warning("All LLM operations stopped and context cleared")
            logger.warning("To restart: Use deployCommander or restart mission")
            logger.warning("=" * 80)

            return {
                "status": "ok",
                "message": "EMERGENCY STOP: All LLM operations halted, all context/caches cleared",
                "llm_enabled": False,
                "circuit_breaker_open": True,
                "context_cleared": True,
                "note": "Use deployCommander to restart or restart mission for clean state"
            }

        except Exception as e:
            logger.error(f"Error during emergency stop: {e}", exc_info=True)
            return {
                "status": "error",
                "error": f"Emergency stop failed: {str(e)}",
                "note": "Restart mission recommended"
            }
