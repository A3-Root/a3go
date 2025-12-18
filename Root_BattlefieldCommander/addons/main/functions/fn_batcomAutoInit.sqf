#include "..\script_component.hpp"
/*
 * Author: Root
 * BATCOM Auto-Initialization for Server Start
 *
 * This script automatically initializes BATCOM when the server starts.
 * Place this in your server init (init.sqf or initServer.sqf):
 *
 *   call Root_fnc_batcomAutoInit;
 *
 * Arguments:
 * 0: Config <HASHMAP> (optional) - Override default configuration
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * // Auto-init with defaults
 * call Root_fnc_batcomAutoInit;
 *
 * // Auto-init with custom config
 * private _config = createHashMapFromArray [
 *     ["controlledSides", [east]],
 *     ["friendlySides", [east, resistance]],
 *     ["missionIntent", "Defend AO objectives against BLUFOR assault"],
 *     ["autoDeployCommander", true],
 *     ["resourceTemplate", "default"] // or "light", "heavy", "mixed", "minimal"
 * ];
 * [_config] call Root_fnc_batcomAutoInit;
 */

params [
    ["_config", createHashMap, [createHashMap]]
];

// Helper: normalize side inputs to string identifiers (EAST/WEST/GUER/CIV)
private _normalizeSidesToStrings = {
    params ["_rawSides"];

    if !(_rawSides isEqualType []) then {
        _rawSides = [_rawSides];
    };

    private _normalized = [];

    {
        private _value = _x;
        private _sideString = "";

        if (_value isEqualType east) then {
            _sideString = str _value;
        } else {
            private _inputStr = if (_value isEqualType "") then {_value} else {str _value};
            _sideString = switch (toUpper _inputStr) do {
                case "EAST": {"EAST"};
                case "OPFOR": {"EAST"};
                case "WEST": {"WEST"};
                case "BLUFOR": {"WEST"};
                case "GUER": {"GUER"};
                case "GUERRILLA": {"GUER"};
                case "RESISTANCE": {"GUER"};
                case "INDEPENDENT": {"GUER"};
                case "INDFOR": {"GUER"};
                case "CIV": {"CIV"};
                case "CIVILIAN": {"CIV"};
                case "CIVI": {"CIV"};
                default {""};
            };
        };

        if (_sideString != "") then {
            _normalized pushBackUnique _sideString;
        } else {
            ["BATCOM", "WARN", format ["batcomAutoInit: Ignoring invalid side '%1' in config", _value]] call FUNC(logMessage);
        };
    } forEach _rawSides;

    _normalized
};

if (!isServer) exitWith {
    ["BATCOM", "ERROR", "batcomAutoInit must run on server"] call FUNC(logMessage);
    false
};

["BATCOM", "INFO", "========================================"] call FUNC(logMessage);
["BATCOM", "INFO", "BATCOM Auto-Initialization Starting..."] call FUNC(logMessage);
["BATCOM", "INFO", "========================================"] call FUNC(logMessage);

// Extract configuration with defaults
private _controlledSides = _config getOrDefault ["controlledSides", [east, resistance]];
private _friendlySides = _config getOrDefault ["friendlySides", [east, resistance]];
private _missionIntent = _config getOrDefault ["missionIntent", "Control the AO and defend objectives against enemy forces"];
private _autoDeployCommander = _config getOrDefault ["autoDeployCommander", true];
private _resourceTemplate = _config getOrDefault ["resourceTemplate", "default"];

// Normalize to strings early so Python sees a clean array (avoids mission configs with mixed types)
_controlledSides = [_controlledSides] call _normalizeSidesToStrings;
_friendlySides = [_friendlySides] call _normalizeSidesToStrings;

// Step 1: Set controlled sides
["BATCOM", "INFO", format ["Step 1: Setting controlled sides (count: %1): %2", count _controlledSides, _controlledSides]] call FUNC(logMessage);
{
    ["BATCOM", "INFO", format ["  - Controlled side %1: %2", _forEachIndex, _x]] call FUNC(logMessage);
} forEach _controlledSides;
["commanderSides", _controlledSides, false] call Root_fnc_batcomInit;

// Step 2: Set friendly sides
["BATCOM", "INFO", format ["Step 2: Setting friendly sides (count: %1): %2", count _friendlySides, _friendlySides]] call FUNC(logMessage);
{
    ["BATCOM", "INFO", format ["  - Friendly side %1: %2", _forEachIndex, _x]] call FUNC(logMessage);
} forEach _friendlySides;
["commanderAllies", _friendlySides, false] call Root_fnc_batcomInit;

// Step 3: Set mission intent
["BATCOM", "INFO", format ["Step 3: Setting mission intent: %1", _missionIntent]] call FUNC(logMessage);
["commanderBrief", _missionIntent, true] call Root_fnc_batcomInit;

// Step 4: Apply resource pool template
["BATCOM", "INFO", format ["Step 4: Applying resource template '%1'", _resourceTemplate]] call FUNC(logMessage);
{
    private _sideStr = _x;  // Already a string after normalization

    ["template", [_sideStr, _resourceTemplate]] call Root_fnc_batcomResourcePoolUI;
} forEach _controlledSides;

// Step 5: Deploy commander if requested
if (_autoDeployCommander) then {
    ["BATCOM", "INFO", "Step 5: Deploying commander"] call FUNC(logMessage);
    ["deployCommander", true] call Root_fnc_batcomInit;
} else {
    ["BATCOM", "INFO", "Step 5: Commander not auto-deployed (set autoDeployCommander = true to enable)"] call FUNC(logMessage);
};

// Step 6: Start AO Lifecycle Manager
["BATCOM", "INFO", "Step 6: Starting AO Lifecycle Manager"] call FUNC(logMessage);
call Root_fnc_batcomAOLifecycle;

// Wait for lifecycle to initialize
sleep 1;

["BATCOM", "INFO", "========================================"] call FUNC(logMessage);
["BATCOM", "INFO", "BATCOM Auto-Initialization Complete!"] call FUNC(logMessage);
["BATCOM", "INFO", "========================================"] call FUNC(logMessage);
["BATCOM", "INFO", ""] call FUNC(logMessage);
["BATCOM", "INFO", "AO Lifecycle Manager is now monitoring for AO start/end events"] call FUNC(logMessage);
["BATCOM", "INFO", "When an AO starts, BATCOM will automatically:"] call FUNC(logMessage);
["BATCOM", "INFO", "  1. Set AO boundaries"] call FUNC(logMessage);
["BATCOM", "INFO", "  2. Track all objectives"] call FUNC(logMessage);
["BATCOM", "INFO", "  3. Generate tactical commands"] call FUNC(logMessage);
["BATCOM", "INFO", "  4. Analyze performance when AO ends"] call FUNC(logMessage);
["BATCOM", "INFO", "  5. Designate HVTs for next AO"] call FUNC(logMessage);
["BATCOM", "INFO", ""] call FUNC(logMessage);
["BATCOM", "INFO", "Manage resource pool: ['view'] call Root_fnc_batcomResourcePoolUI;"] call FUNC(logMessage);
["BATCOM", "INFO", "========================================"] call FUNC(logMessage);

systemChat "BATCOM: Auto-initialization complete - Ready for AO";

true
