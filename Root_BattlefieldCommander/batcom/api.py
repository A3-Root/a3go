"""
BATCOM API - Entry points for SQF calls

This module provides the main interface between Arma 3 (via Pythia) and the
BATCOM Python core. All functions in this module can be called from SQF using:

    ["batcom.function_name", [args]] call py3_fnc_callExtension

"""

import logging
import json
import os
import sys

# Early debug output for Pythia diagnostics
print(f"[BATCOM.API] Module loading... Python {sys.version}", flush=True)

# Import BATCOM modules with error handling for Linux compatibility
try:
    from .utils.logging_setup import setup_logging, get_logger
    from .world.scanner import WorldScanner
    from .commands.queue import CommandQueue
    from .runtime.state import StateManager
    from .runtime.admin import AdminCommandHandler
    print("[BATCOM.API] All modules imported successfully", flush=True)
except ImportError as e:
    print(f"[BATCOM.API] CRITICAL: Failed to import modules: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise
except Exception as e:
    print(f"[BATCOM.API] CRITICAL: Unexpected error during imports: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise

# Module-level state
_logger = None
_config = None
_initialized = False
_commander = None
_world_scanner = None
_command_queue = None
_state_manager = None
_admin_handler = None
GUARDRAILS_PATH = os.path.join(os.path.dirname(__file__), "guardrails.json")


def _load_guardrails():
    """Load guardrails overrides from guardrails.json if present"""
    try:
        with open(GUARDRAILS_PATH, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"[BATCOM.PY] Guardrails load failed: {e}")
    return {}


def _array_to_dict(arr):
    """Convert nested array from Pythia to dictionary"""
    if not isinstance(arr, (list, tuple)):
        return arr

    # If this list looks like dict items (pairs), convert to dict
    if all(isinstance(item, (list, tuple)) and len(item) == 2 for item in arr):
        result = {}
        for key, value in arr:
            if isinstance(value, (list, tuple)):
                # If nested list is itself pairs, convert to dict
                if all(isinstance(v, (list, tuple)) and len(v) == 2 for v in value):
                    value = _array_to_dict(value)
                else:
                    # Recurse element-wise
                    value = [_array_to_dict(v) for v in value]
            result[key] = value
        return result

    # Otherwise return list with recursive conversion
    return [_array_to_dict(item) for item in arr]


def _dict_to_array(d):
    """Convert dictionary to nested array for Pythia (reverse of _array_to_dict)

    Pythia does not support returning Python dicts as SQF hashmaps.
    We must convert dicts to nested arrays of [key, value] pairs.
    """
    if not isinstance(d, dict):
        # Normalize None to empty string so SQF hashmap conversion never sees nil
        return "" if d is None else d

    result = []
    for key, value in d.items():
        # Replace None with empty string to avoid nil on SQF side
        if value is None:
            value = ""

        # Recursively convert nested dicts
        if isinstance(value, dict):
            value = _dict_to_array(value)
        # Convert lists of dicts
        elif isinstance(value, (list, tuple)):
            value = [_dict_to_array(item) if isinstance(item, dict) else item for item in value]

        result.append([key, value])

    return result


def init(config_array):
    """
    Initialize BATCOM with configuration from SQF

    Args:
        config_array: Configuration as nested array from SQF (converted from hashmap)

    Returns:
        Array with status and version (converted from dict for Pythia)

    Example from SQF:
        ["batcom.init", [_configArray]] call py3_fnc_callExtension
    """
    global _logger, _config, _initialized, _commander, _world_scanner, _command_queue, _state_manager, _admin_handler

    # Early debug logging to file
    try:
        with open('batcom_init_debug.txt', 'w') as f:
            import sys
            f.write("="*60 + "\n")
            f.write("BATCOM Python init() called\n")
            f.write("="*60 + "\n")
            f.write(f"Python version: {sys.version}\n")
            f.write(f"Received type: {type(config_array)}\n")
            f.write(f"Received value: {config_array}\n")
            f.write(f"Is list: {isinstance(config_array, (list, tuple))}\n")
            if isinstance(config_array, (list, tuple)):
                f.write(f"Length: {len(config_array)}\n")
                f.write(f"First element type: {type(config_array[0]) if len(config_array) > 0 else 'N/A'}\n")
    except Exception as e:
        # If file write fails, continue anyway
        pass

    try:
        print("[BATCOM.PY] init() called")
        print(f"[BATCOM.PY] Received config_array type: {type(config_array)}")

        # Convert array to dictionary (Pythia doesn't support hashmaps)
        print("[BATCOM.PY] Converting array to dict...")
        config_dict = _array_to_dict(config_array)
        print(f"[BATCOM.PY] Converted to dict with keys: {list(config_dict.keys())}")

        # Apply guardrails overrides
        guardrails = _load_guardrails()
        if guardrails:
            guardrails_current = guardrails.get("current", guardrails)
            ai_cfg = config_dict.get('ai', {})
            if isinstance(ai_cfg, dict):
                ai_cfg.update(guardrails_current)
                config_dict['ai'] = ai_cfg
            else:
                config_dict['ai'] = guardrails_current
            print(f"[BATCOM.PY] Applied guardrails current profile: {guardrails_current}")

        # Update debug file
        try:
            with open('batcom_init_debug.txt', 'a') as f:
                f.write(f"Converted to dict: {config_dict}\n")
                f.write(f"Dict keys: {list(config_dict.keys())}\n")
        except:
            pass

        # Setup logging first
        logging_config = config_dict.get('logging', {})
        print(f"[BATCOM.PY] Setting up logging with config: {logging_config}")
        _logger = setup_logging(logging_config)

        _logger.info('='*60)
        _logger.info('Initializing BATCOM (Root\'s Battlefield Commander)')
        _logger.info('='*60)

        # Store configuration
        _config = config_dict
        _logger.debug('Configuration loaded: %s', config_dict.keys())

        # Initialize state manager
        _state_manager = StateManager()
        _logger.info('State manager initialized')

        # Apply guardrails to runtime overrides
        if guardrails:
            try:
                _state_manager.update_ai_config(guardrails)
            except Exception as e:
                _logger.warning("Failed to apply guardrails to runtime config: %s", e)

        # Initialize admin handler
        _admin_handler = AdminCommandHandler(_state_manager, guardrails_path=GUARDRAILS_PATH)
        _logger.info('Admin handler initialized')

        # Initialize world scanner
        _world_scanner = WorldScanner()
        _logger.info('World scanner initialized')

        # Initialize command queue
        runtime_config = config_dict.get('runtime', {})
        max_commands = runtime_config.get('max_commands_per_tick', 30)
        _command_queue = CommandQueue(max_commands_per_batch=max_commands)
        _logger.info('Command queue initialized (max batch: %d)', max_commands)

        # Initialize commander (decision loop)
        from .runtime.commander import batcom
        _commander = batcom(_state_manager, _command_queue, config_dict)
        _logger.info('Battlefield commander initialized')

        # Link commander to admin handler (for token stats access)
        _admin_handler.commander = _commander

        # Log key configuration
        scan_config = config_dict.get('scan', {})
        _logger.info('Scan intervals - tick: %.1fs, groups: %.1fs, players: %.1fs',
                    scan_config.get('tick', 2.0),
                    scan_config.get('ai_groups', 5.0),
                    scan_config.get('players', 3.0))

        runtime_config = config_dict.get('runtime', {})
        _logger.info('Runtime limits - msgs/tick: %d, cmds/tick: %d, max_groups: %d',
                    runtime_config.get('max_messages_per_tick', 50),
                    runtime_config.get('max_commands_per_tick', 30),
                    runtime_config.get('max_controlled_groups', 500))

        ai_config = config_dict.get('ai', {})
        if ai_config.get('enabled', True):
            _logger.info('AI integration - provider: %s, model: %s',
                        ai_config.get('provider', 'openai'),
                        ai_config.get('model', 'gpt-4'))
        else:
            _logger.info('AI integration disabled - rule-based decisions only')

        # Test LLM connection if enabled
        if ai_config.get('enabled', True):
            _logger.info('Testing LLM connection...')
            try:
                if _commander.llm_enabled:
                    # Use the client's built-in test_connection() method
                    # This works with all provider types (native SDK and OpenAI-compat)
                    success, message = _commander.llm_client.test_connection()

                    if success:
                        _logger.info(f'LLM connected to {_commander.llm_client.model}')
                        _logger.info(f'LLM says: {message}')
                    else:
                        _logger.warning(f'LLM test failed: {message}')
                else:
                    _logger.warning('LLM not enabled - skipping connection test')
            except Exception as llm_test_error:
                _logger.warning(f'LLM connection test failed: {llm_test_error}')
                _logger.warning('BATCOM will continue with rule-based decisions only')

        # Mark as initialized
        _initialized = True

        _logger.info('BATCOM initialization complete')
        print("[BATCOM.PY] Init successful!")

        # Convert dict to array for Pythia (it doesn't support dict->hashmap)
        result_dict = {
            "status": "ok",
            "version": "1.0.0"
        }
        print(f"[BATCOM.PY] Converting result dict to array: {result_dict}")
        result_array = _dict_to_array(result_dict)
        print(f"[BATCOM.PY] Result array: {result_array}")
        print(f"[BATCOM.PY] Result array type: {type(result_array)}")
        print(f"[BATCOM.PY] Returning result...")

        # Write final status to debug file
        try:
            with open('batcom_init_debug.txt', 'a') as f:
                f.write("="*60 + "\n")
                f.write("SUCCESS - Returning result\n")
                f.write(f"Result dict: {result_dict}\n")
                f.write(f"Result array: {result_array}\n")
                f.write("="*60 + "\n")
        except:
            pass

        return result_array

    except Exception as e:
        error_msg = str(e)
        print(f"[BATCOM.PY] ✗✗✗ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()

        # Write error to debug file
        try:
            with open('batcom_init_debug.txt', 'a') as f:
                f.write("="*60 + "\n")
                f.write("ERROR occurred\n")
                f.write(f"Error: {error_msg}\n")
                f.write(f"Traceback:\n{traceback.format_exc()}\n")
                f.write("="*60 + "\n")
        except:
            pass

        if _logger:
            _logger.exception('Failed to initialize BATCOM')

        # Convert dict to array for Pythia (it doesn't support dict->hashmap)
        error_dict = {
            "status": "error",
            "error": error_msg
        }
        error_array = _dict_to_array(error_dict)
        print(f"[BATCOM.PY] Returning error array: {error_array}")
        return error_array


def shutdown():
    """
    Shutdown BATCOM and cleanup resources

    Returns:
        Array with status (converted from dictionary for Pythia)

    Example from SQF:
        ["batcom.shutdown", []] call py3_fnc_callExtension
    """
    global _logger, _config, _initialized, _commander, _world_scanner, _command_queue, _state_manager, _admin_handler

    try:
        if not _initialized:
            return _dict_to_array({"status": "ok", "message": "BATCOM was not initialized"})

        _logger.info('Shutting down BATCOM...')

        # Cleanup subsystems
        if _commander is not None:
            _commander.reset()
            _commander = None

        if _world_scanner is not None:
            _world_scanner = None

        if _command_queue is not None:
            _command_queue.clear()
            _command_queue = None

        if _state_manager is not None:
            _state_manager = None

        if _admin_handler is not None:
            _admin_handler = None

        _initialized = False
        _config = None

        _logger.info('BATCOM shutdown complete')

        return _dict_to_array({"status": "ok"})

    except Exception as e:
        if _logger:
            _logger.exception('Error during BATCOM shutdown')
        return _dict_to_array({
            "status": "error",
            "error": str(e)
        })


def is_initialized():
    """
    Check if BATCOM is initialized

    Returns:
        Boolean

    Example from SQF:
        ["batcom.is_initialized", []] call py3_fnc_callExtension
    """
    return _initialized


def get_version():
    """
    Get BATCOM version

    Returns:
        Version string

    Example from SQF:
        ["batcom.get_version", []] call py3_fnc_callExtension
    """
    return "1.0.0"


def world_snapshot(snapshot_data):
    """
    Process a world state snapshot from SQF

    Args:
        snapshot_data: Dictionary with world state data from worldScan

    Returns:
        Array with status (converted from dictionary for Pythia)

    Example from SQF:
        ["batcom.world_snapshot", [_snapshot]] call py3_fnc_callExtension
    """
    global _world_scanner, _logger

    try:
        # Convert from nested array to dict if needed
        if isinstance(snapshot_data, (list, tuple)):
            snapshot_data = _array_to_dict(snapshot_data)

        if not _initialized:
            return _dict_to_array({
                "status": "error",
                "error": "BATCOM not initialized"
            })

        if _world_scanner is None:
            return _dict_to_array({
                "status": "error",
                "error": "World scanner not initialized"
            })

        # Process the snapshot
        world_state = _world_scanner.ingest_snapshot(snapshot_data)

        # Trigger decision loop
        if _commander is not None:
            _commander.process_world_state(world_state)

        return _dict_to_array({"status": "ok"})

    except Exception as e:
        if _logger:
            _logger.exception('Failed to process world snapshot')
        return _dict_to_array({
            "status": "error",
            "error": str(e)
        })


def get_pending_commands():
    """
    Get pending commands from the command queue

    Returns:
        Array with status and commands (converted from dictionary for Pythia)

    Example from SQF:
        ["batcom.get_pending_commands", []] call py3_fnc_callExtension
    """
    global _command_queue, _logger

    try:
        if not _initialized:
            return _dict_to_array({
                "status": "error",
                "error": "BATCOM not initialized"
            })

        if _command_queue is None:
            return _dict_to_array({
                "status": "error",
                "error": "Command queue not initialized"
            })

        # Get batch of commands
        commands = _command_queue.get_batch()

        return _dict_to_array({
            "status": "ok",
            "commands": commands
        })

    except Exception as e:
        if _logger:
            _logger.exception('Failed to get pending commands')
        return _dict_to_array({
            "status": "error",
            "error": str(e),
            "commands": []
        })


def batcom_init(command, params, flag=False):
    """
    Handle admin commands from debug console

    Args:
        command: Command identifier string
        params: Command parameters (varies by command)
        flag: Additional boolean flag (varies by command)

    Returns:
        Array with status and message (converted from dictionary for Pythia)

    Example from SQF:
        ["batcom.batcom_init", ["commanderBrief", "Protect HVT", true]] call py3_fnc_callExtension
    """
    global _admin_handler, _logger, _commander

    try:
        if not _initialized:
            return _dict_to_array({
                "status": "error",
                "error": "BATCOM not initialized"
            })

        if _admin_handler is None:
            return _dict_to_array({
                "status": "error",
                "error": "Admin handler not initialized"
            })

        # Convert params from nested array to dict if needed (Pythia converts hashmaps to arrays)
        if isinstance(params, (list, tuple)):
            # Check if this looks like a dict structure (array of [key, value] pairs)
            if all(isinstance(item, (list, tuple)) and len(item) == 2 for item in params):
                params = _array_to_dict(params)

        # Route to admin handler
        result = _admin_handler.handle_command(command, params, flag)

        # If an API key was injected and we have a commander, re-initialize LLM components
        if command == "setGeminiApiKey" and result.get("status") == "ok" and _commander is not None:
            _commander._init_llm()

        # Convert result dict to array for Pythia
        return _dict_to_array(result)

    except Exception as e:
        if _logger:
            _logger.exception('Failed to handle admin command: %s', command)
        return _dict_to_array({
            "status": "error",
            "error": str(e)
        })


def test_gemini_connection():
    """
    Test Gemini LLM connection and get a greeting response

    Returns:
        Array with status and LLM response (converted from dictionary for Pythia)

    Example from SQF:
        ["batcom.test_gemini_connection", []] call py3_fnc_callExtension
    """
    global _commander, _logger, _config

    try:
        if not _initialized:
            return _dict_to_array({
                "status": "error",
                "error": "BATCOM not initialized. Call init first."
            })

        if _commander is None:
            return _dict_to_array({
                "status": "error",
                "error": "Commander not initialized"
            })

        # Ensure LLM is initialized (supports runtime API key injection)
        if not _commander.llm_enabled:
            ai_config = _config.get('ai', {}) if _config else {}
            if not ai_config.get('enabled', False):
                return _dict_to_array({
                    "status": "error",
                    "error": "LLM is disabled in CfgBATCOM (ai.enabled = 0)"
                })

            # Try to (re)initialize with current state/api key
            try:
                _commander._init_llm()
            except Exception as reinit_err:
                if _logger:
                    _logger.exception("LLM reinit failed during test: %s", reinit_err)

            if not _commander.llm_enabled:
                import os
                key_cfg = _state_manager.api_keys.get('gemini') if _state_manager else {}
                api_key_present = bool((key_cfg or {}).get('key') or os.getenv('GEMINI_API_KEY'))
                hint = "LLM failed to initialize (check logs for details)"
                if not api_key_present:
                    hint = "GEMINI_API_KEY not set (env or runtime)"
                return _dict_to_array({
                    "status": "error",
                    "error": hint
                })

        # Test the connection with a simple prompt
        _logger.info("Testing Gemini LLM connection...")

        try:
            test_prompt = """You are a tactical AI commander for Arma 3.

Respond with a brief greeting confirming you are ready to command forces.
Keep it under 50 words and professional/military style.

Output ONLY the greeting text, no JSON or other formatting."""

            response = _commander.llm_client.client.models.generate_content(
                model=_commander.llm_client.model,
                contents=test_prompt
            )

            if response.text:
                greeting = response.text.strip()
                _logger.info("Gemini test successful: %s", greeting)

                return _dict_to_array({
                    "status": "ok",
                    "model": _commander.llm_client.model,
                    "greeting": greeting,
                    "llm_enabled": True
                })
            else:
                return _dict_to_array({
                    "status": "error",
                    "error": "Gemini returned empty response"
                })

        except Exception as api_error:
            _logger.error("Gemini API error: %s", api_error, exc_info=True)
            return _dict_to_array({
                "status": "error",
                "error": f"Gemini API call failed: {str(api_error)}"
            })

    except Exception as e:
        if _logger:
            _logger.exception('Failed to test Gemini connection')
        return _dict_to_array({
            "status": "error",
            "error": str(e)
        })


def set_ao_defense_phase(active):
    """
    Activate or deactivate AO Defense Phase

    When active, all defense_only assets become available for deployment regardless
    of objective type. This should be called when the entire AO transitions to a
    defense scenario (e.g., enemy counterattack).

    Args:
        active: Boolean - True to activate defense phase, False to deactivate

    Returns:
        Array with status (converted from dictionary for Pythia)

    Example from SQF:
        // Activate defense phase when counterattack begins
        ["batcom.set_ao_defense_phase", [true]] call py3_fnc_callExtension;

        // Deactivate when threat is neutralized
        ["batcom.set_ao_defense_phase", [false]] call py3_fnc_callExtension;
    """
    global _state_manager, _logger

    try:
        if not _initialized:
            return _dict_to_array({
                "status": "error",
                "error": "BATCOM not initialized"
            })

        if _state_manager is None:
            return _dict_to_array({
                "status": "error",
                "error": "State manager not initialized"
            })

        # Convert to boolean
        active_bool = bool(active)

        # Set the defense phase
        _state_manager.set_ao_defense_phase(active_bool)

        if _logger:
            _logger.info(f"AO Defense Phase {'ACTIVATED' if active_bool else 'DEACTIVATED'} via API")

        return _dict_to_array({
            "status": "ok",
            "ao_defense_phase": active_bool,
            "message": f"Defense phase {'activated' if active_bool else 'deactivated'} - defense_only assets are now {'available' if active_bool else 'restricted'}"
        })

    except Exception as e:
        if _logger:
            _logger.exception('Failed to set AO defense phase')
        return _dict_to_array({
            "status": "error",
            "error": str(e)
        })


def load_resource_template(template_name):
    """
    Load a resource template by name and apply it to the resource pool

    Args:
        template_name: String - Name of template (e.g., "minimal", "low", "medium", "high", "ultra_high")

    Returns:
        Array with status and loaded assets (converted from dictionary for Pythia)

    Example from SQF:
        ["batcom.load_resource_template", ["medium"]] call py3_fnc_callExtension;
    """
    global _state_manager, _logger

    try:
        if not _initialized:
            return _dict_to_array({
                "status": "error",
                "error": "BATCOM not initialized"
            })

        if _state_manager is None:
            return _dict_to_array({
                "status": "error",
                "error": "State manager not initialized"
            })

        # Import resource loader
        from .config.resource_loader import load_template

        # Load the template
        resource_pool = load_template(template_name)
        if not resource_pool:
            return _dict_to_array({
                "status": "error",
                "error": f"Template '{template_name}' not found"
            })

        # Apply to state manager
        _state_manager.set_resource_pool(resource_pool)

        if _logger:
            _logger.info(f"Loaded resource template '{template_name}'")

        # Get summary of what was loaded
        sides = list(resource_pool.keys())
        total_asset_types = sum(len(assets) for assets in resource_pool.values())

        return _dict_to_array({
            "status": "ok",
            "template": template_name,
            "sides": sides,
            "total_asset_types": total_asset_types,
            "message": f"Template '{template_name}' loaded successfully"
        })

    except Exception as e:
        if _logger:
            _logger.exception(f'Failed to load resource template {template_name}')
        return _dict_to_array({
            "status": "error",
            "error": str(e)
        })


def get_state():
    """
    Get the global state manager instance (for direct Python access)

    Returns:
        StateManager instance

    Note: This is for Python API use, not SQF
    """
    global _state_manager
    return _state_manager


def resource_pool_add_asset(side, asset_type, max_count, unit_classes=None, defense_only=False, description=""):
    """
    Add or update an asset in the resource pool

    Args:
        side: Side name ("EAST", "WEST", "RESISTANCE")
        asset_type: Asset type identifier (e.g., "infantry_squad", "heavy_armor")
        max_count: Maximum number that can be deployed
        unit_classes: List of Arma 3 class names (optional, will use template defaults if None)
        defense_only: Boolean - if True, only available during AO Defense Phase
        description: Human-readable description

    Returns:
        Array with status (converted from dictionary for Pythia)

    Example from SQF:
        ["batcom.resource_pool_add_asset", ["EAST", "infantry_squad", 5, ["O_Soldier_F"], false, "Basic infantry"]] call py3_fnc_callExtension;
    """
    global _state_manager, _logger

    try:
        if not _initialized:
            return _dict_to_array({"status": "error", "error": "BATCOM not initialized"})

        if _state_manager is None:
            return _dict_to_array({"status": "error", "error": "State manager not initialized"})

        # Normalize side
        side = side.upper()
        if side not in ["EAST", "WEST", "RESISTANCE", "INDEPENDENT"]:
            return _dict_to_array({"status": "error", "error": f"Invalid side: {side}"})

        # Get current resource pool or create new one
        current_pool = _state_manager.resource_pool
        if not current_pool:
            current_pool = {}

        # Get side assets or create new
        if side not in current_pool:
            current_pool[side] = {}

        # Create asset configuration
        asset_config = {
            "max": max_count,
            "defense_only": defense_only
        }

        if unit_classes and len(unit_classes) > 0:
            asset_config["unit_classes"] = unit_classes

        if description:
            asset_config["description"] = description

        # Add/update asset
        current_pool[side][asset_type] = asset_config

        # Apply to state
        _state_manager.set_resource_pool(current_pool)

        if _logger:
            _logger.info(f"Added/updated asset {side}:{asset_type} (max={max_count}, defense_only={defense_only})")

        return _dict_to_array({
            "status": "ok",
            "message": f"Asset {asset_type} added to {side}",
            "side": side,
            "asset_type": asset_type,
            "max": max_count,
            "defense_only": defense_only
        })

    except Exception as e:
        if _logger:
            _logger.exception('Failed to add asset to resource pool')
        return _dict_to_array({"status": "error", "error": str(e)})


def resource_pool_remove_asset(side, asset_type):
    """
    Remove an asset from the resource pool

    Args:
        side: Side name
        asset_type: Asset type to remove

    Returns:
        Array with status

    Example from SQF:
        ["batcom.resource_pool_remove_asset", ["EAST", "infantry_squad"]] call py3_fnc_callExtension;
    """
    global _state_manager, _logger

    try:
        if not _initialized:
            return _dict_to_array({"status": "error", "error": "BATCOM not initialized"})

        side = side.upper()
        current_pool = _state_manager.resource_pool

        if side not in current_pool or asset_type not in current_pool[side]:
            return _dict_to_array({
                "status": "error",
                "error": f"Asset {asset_type} not found for {side}"
            })

        del current_pool[side][asset_type]
        _state_manager.set_resource_pool(current_pool)

        if _logger:
            _logger.info(f"Removed asset {side}:{asset_type}")

        return _dict_to_array({
            "status": "ok",
            "message": f"Removed {asset_type} from {side}"
        })

    except Exception as e:
        if _logger:
            _logger.exception('Failed to remove asset')
        return _dict_to_array({"status": "error", "error": str(e)})


def resource_pool_clear_side(side):
    """
    Clear all assets for a specific side

    Args:
        side: Side name

    Returns:
        Array with status

    Example from SQF:
        ["batcom.resource_pool_clear_side", ["EAST"]] call py3_fnc_callExtension;
    """
    global _state_manager, _logger

    try:
        if not _initialized:
            return _dict_to_array({"status": "error", "error": "BATCOM not initialized"})

        side = side.upper()
        current_pool = _state_manager.resource_pool

        if side in current_pool:
            del current_pool[side]
            _state_manager.set_resource_pool(current_pool)

            if _logger:
                _logger.info(f"Cleared all assets for {side}")

            return _dict_to_array({
                "status": "ok",
                "message": f"Cleared all resources for {side}"
            })
        else:
            return _dict_to_array({
                "status": "ok",
                "message": f"No resources found for {side}"
            })

    except Exception as e:
        if _logger:
            _logger.exception('Failed to clear side resources')
        return _dict_to_array({"status": "error", "error": str(e)})


def resource_pool_get_status():
    """
    Get current resource pool status with usage information

    Returns:
        Array with resource pool data (converted from dictionary for Pythia)

    Example from SQF:
        private _status = ["batcom.resource_pool_get_status", []] call py3_fnc_callExtension;
    """
    global _state_manager, _logger

    try:
        if not _initialized:
            return _dict_to_array({"status": "error", "error": "BATCOM not initialized"})

        if _state_manager is None:
            return _dict_to_array({"status": "error", "error": "State manager not initialized"})

        # Get full resource status
        status = _state_manager.get_resource_status()

        # Get AO defense phase status
        ao_defense_active = _state_manager.is_ao_defense_phase()

        return _dict_to_array({
            "status": "ok",
            "resource_pool": status,
            "ao_defense_phase": ao_defense_active
        })

    except Exception as e:
        if _logger:
            _logger.exception('Failed to get resource pool status')
        return _dict_to_array({"status": "error", "error": str(e)})


def resource_pool_list_templates():
    """
    List all available resource templates

    Returns:
        Array with template names and descriptions

    Example from SQF:
        private _templates = ["batcom.resource_pool_list_templates", []] call py3_fnc_callExtension;
    """
    global _logger

    try:
        from .config.resource_loader import get_loader

        loader = get_loader()
        template_names = loader.list_templates()

        templates_info = []
        for name in template_names:
            template = loader.get_template(name)
            if template:
                templates_info.append({
                    "name": name,
                    "description": template.get("description", "No description")
                })

        return _dict_to_array({
            "status": "ok",
            "templates": templates_info
        })

    except Exception as e:
        if _logger:
            _logger.exception('Failed to list templates')
        return _dict_to_array({"status": "error", "error": str(e)})


# Future API functions will be added here in later phases:
# - push_event(event_data)
