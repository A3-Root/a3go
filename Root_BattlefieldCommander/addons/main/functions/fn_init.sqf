#include "..\script_component.hpp"
/*
 * Author: Root
 * Initialize Root's Battlefield Commander (BATCOM)
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * call BATCOM_fnc_init;
 */

if (GVAR(debugMode)) then {
    diag_log "========================================";
    diag_log "BATCOM: INIT STARTING";
    diag_log "========================================";
};

// Only run on server
if (!isServer) exitWith {
    if (GVAR(debugMode)) then {diag_log "BATCOM: Not server, exiting init";};
};

if (GVAR(debugMode)) then {diag_log "BATCOM: Server confirmed, checking Pythia...";};

// Check if Pythia is available
if (isNil "py3_fnc_callExtension") exitWith {
    ["BATCOM", "ERROR", "Pythia extension not found! BATCOM requires Pythia-next to function."] call FUNC(logMessage);
    if (GVAR(debugMode)) then {diag_log "BATCOM: ✗ Pythia not found!";};
};

if (GVAR(debugMode)) then {diag_log "BATCOM: ✓ Pythia found";};
["BATCOM", "INFO", "Initializing Root's Battlefield Commander..."] call FUNC(logMessage);

// Initialize global state variables
if (GVAR(debugMode)) then {diag_log "BATCOM: Initializing global state variables...";};
GVAR(enabled) = false;
GVAR(deployed) = false;
GVAR(groupRegistry) = createHashMap;
GVAR(asyncThreads) = createHashMap;
GVAR(missionIntent) = "";
GVAR(friendlySides) = [];
GVAR(controlledSides) = [];
GVAR(controlledGroupOverrides) = [];
GVAR(aoBounds) = createHashMap;
GVAR(debugMode) = false;
private _dlog = {
    params ["_msg"];
    if (GVAR(debugMode)) then {diag_log _msg;};
};
["BATCOM: ✓ Global state initialized"] call _dlog;

// Load configuration from CfgBATCOM
["BATCOM: Loading configuration from CfgBATCOM..."] call _dlog;
private _config = configFile >> "CfgBATCOM";
private _configDict = createHashMap;

// Parse logging config
["BATCOM: Parsing logging config..."] call _dlog;
private _loggingConfig = _config >> "logging";
_configDict set ["logging", createHashMapFromArray [
    ["level", getText (_loggingConfig >> "level")],
    ["arma_console", getNumber (_loggingConfig >> "arma_console")]
]];
[(format ["BATCOM: ✓ logging: level=%1, arma_console=%2", getText (_loggingConfig >> "level"), getNumber (_loggingConfig >> "arma_console")])] call _dlog;

// Parse scan config
["BATCOM: Parsing scan config..."] call _dlog;
private _scanConfig = _config >> "scan";
_configDict set ["scan", createHashMapFromArray [
    ["tick", getNumber (_scanConfig >> "tick")],
    ["ai_groups", getNumber (_scanConfig >> "ai_groups")],
    ["players", getNumber (_scanConfig >> "players")],
    ["objectives", getNumber (_scanConfig >> "objectives")]
]];
[format ["BATCOM: ✓ scan: tick=%1, ai_groups=%2, players=%3, objectives=%4",
    getNumber (_scanConfig >> "tick"), getNumber (_scanConfig >> "ai_groups"),
    getNumber (_scanConfig >> "players"), getNumber (_scanConfig >> "objectives")]] call _dlog;

// Parse runtime config
["BATCOM: Parsing runtime config..."] call _dlog;
private _runtimeConfig = _config >> "runtime";
_configDict set ["runtime", createHashMapFromArray [
    ["max_messages_per_tick", getNumber (_runtimeConfig >> "max_messages_per_tick")],
    ["max_commands_per_tick", getNumber (_runtimeConfig >> "max_commands_per_tick")],
    ["max_controlled_groups", getNumber (_runtimeConfig >> "max_controlled_groups")]
]];
[(format ["BATCOM: ✓ runtime: max_messages=%1, max_commands=%2, max_groups=%3",
    getNumber (_runtimeConfig >> "max_messages_per_tick"), getNumber (_runtimeConfig >> "max_commands_per_tick"),
    getNumber (_runtimeConfig >> "max_controlled_groups")])] call _dlog;

// Parse AI config
["BATCOM: Parsing AI config..."] call _dlog;
private _aiConfig = _config >> "ai";
_configDict set ["ai", createHashMapFromArray [
    ["enabled", getNumber (_aiConfig >> "enabled") == 1],
    ["provider", getText (_aiConfig >> "provider")],
    ["model", getText (_aiConfig >> "model")],
    ["timeout", getNumber (_aiConfig >> "timeout")],
    ["min_interval", getNumber (_aiConfig >> "min_interval")]
]];
[(format ["BATCOM: ✓ ai: enabled=%1, provider=%2, model=%3",
    getNumber (_aiConfig >> "enabled") == 1, getText (_aiConfig >> "provider"), getText (_aiConfig >> "model")])] call _dlog;

// Parse safety config
["BATCOM: Parsing safety config..."] call _dlog;
private _safetyConfig = _config >> "safety";

_configDict set ["safety", createHashMapFromArray [
    ["sandbox_enabled", getNumber (_safetyConfig >> "sandbox_enabled") == 1],
    ["max_groups_per_objective", getNumber (_safetyConfig >> "max_groups_per_objective")],
    ["max_units_per_side", getNumber (_safetyConfig >> "max_units_per_side")],
    ["allowed_commands", getArray (_safetyConfig >> "allowed_commands")],
    ["blocked_commands", getArray (_safetyConfig >> "blocked_commands")],
    ["audit_log", getNumber (_safetyConfig >> "audit_log") == 1]
]];
[(format ["BATCOM: ✓ safety: sandbox=%1, max_groups=%2, max_units=%3, allowed_cmds=%4",
    getNumber (_safetyConfig >> "sandbox_enabled") == 1, getNumber (_safetyConfig >> "max_groups_per_objective"),
    getNumber (_safetyConfig >> "max_units_per_side"), count getArray (_safetyConfig >> "allowed_commands")])] call _dlog;

// Convert hashmap to array for Pythia compatibility
// Pythia doesn't support hashmaps, only arrays
[(format ["BATCOM: DEBUG - _configDict type: %1, keys: %2", typeName _configDict, keys _configDict])] call _dlog;

// Check if function exists
[(format ["BATCOM: DEBUG - FUNC(hashmapToArray) = %1", FUNC(hashmapToArray)])] call _dlog;
[(format ["BATCOM: DEBUG - isNil FUNC(hashmapToArray) = %1", isNil {FUNC(hashmapToArray)}])] call _dlog;

private _configArray = try {
    private _result = [_configDict] call FUNC(hashmapToArray);
    if (!(_result isEqualType [])) then {
        throw format ["hashmapToArray returned %1 during init", typeName _result];
    };
    _result
} catch {
    [(format ["BATCOM: ERROR calling hashmapToArray: %1", _exception])] call _dlog;
    []
};
[(format ["BATCOM: DEBUG - _configArray type: %1, isNil: %2", typeName _configArray, isNil "_configArray"])] call _dlog;
if (!isNil "_configArray" && {_configArray isEqualType []}) then {
    [(format ["BATCOM: DEBUG - _configArray count: %1", count _configArray])] call _dlog;
};
[(format ["BATCOM: Config prepared (%1 sections)", count _configArray])] call _dlog;

// Call Python initialization
["BATCOM: ----------------------------------------"] call _dlog;
["BATCOM: Calling Python batcom.init()..."] call _dlog;
[(format ["BATCOM: Sending config array with %1 sections", count _configArray])] call _dlog;
private _resultArray = ["batcom.init", [_configArray]] call FUNC(pythiaCall);
["BATCOM: Python call returned"] call _dlog;

if (isNil "_resultArray") exitWith {
    ["BATCOM", "ERROR", "Failed to initialize Python module - no response!"] call FUNC(logMessage);
    ["BATCOM: ✗ Init failed - _resultArray is nil (no response from Python)"] call _dlog;
    ["BATCOM: Check Pythia logs for errors"] call _dlog;
    ["BATCOM: ========================================"] call _dlog;
};

[(format ["BATCOM: Result type: %1", typeName _resultArray])] call _dlog;

// Convert result array back to hashmap (Pythia doesn't support dict->hashmap directly)
if (!(_resultArray isEqualType [])) exitWith {
    ["BATCOM", "ERROR", format ["Python init returned wrong type: %1 (expected array)", typeName _resultArray]] call FUNC(logMessage);
    [(format ["BATCOM: ✗ Init failed - wrong return type: %1 (expected ARRAY)", typeName _resultArray])] call _dlog;
    [(format ["BATCOM: Raw result value: %1", _resultArray])] call _dlog;
    ["BATCOM: ========================================"] call _dlog;
};

[(format ["BATCOM: Converting result array (count: %1) to hashmap...", count _resultArray])] call _dlog;
private _result = [_resultArray] call FUNC(arrayToHashmap);
[(format ["BATCOM: Converted to hashmap, keys: %1", keys _result])] call _dlog;

private _status = _result getOrDefault ["status", ""];
[(format ["BATCOM: Status from Python: '%1'", _status])] call _dlog;

if (_status isEqualTo "ok") then {
    GVAR(enabled) = true;
    private _version = _result getOrDefault ["version", "unknown"];
    ["BATCOM", "INFO", format ["BATCOM initialized successfully (v%1)", _version]] call FUNC(logMessage);
    ["BATCOM: ========================================"] call _dlog;
    [(format ["BATCOM: ✓✓✓ INIT SUCCESS (v%1) ✓✓✓", _version])] call _dlog;
    ["BATCOM: ========================================"] call _dlog;
} else {
    private _error = _result getOrDefault ["error", "unknown"];
    ["BATCOM", "ERROR", format ["Python initialization failed: %1", _error]] call FUNC(logMessage);
    ["BATCOM: ========================================"] call _dlog;
    [(format ["BATCOM: ✗✗✗ INIT FAILED: %1 ✗✗✗", _error])] call _dlog;
    ["BATCOM: ========================================"] call _dlog;
};
