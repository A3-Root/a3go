#include "..\script_component.hpp"
/*
 * Author: Root
 * Main admin API entry point for Root_fnc_batcomInit
 *
 * This is the primary interface for server admins to configure and control BATCOM.
 *
 * Arguments:
 * 0: Command <STRING> - Command identifier
 * 1: Parameters <ANY> - Command-specific parameters
 * 2: Additional flag <BOOL> (optional) - Command-specific flag
 *
 * Return Value:
 * Result message <STRING> or nil
 *
 * Examples:
 * [commanderBrief, "Protect HVT from capture", true] call Root_fnc_batcomInit;
 * [commanderAllies, [east, guer, civilian], true] call Root_fnc_batcomInit;
 * [commanderSides, [east], true] call Root_fnc_batcomInit;
 * [deployCommander, true] call Root_fnc_batcomInit;
 * [commanderTask, "Deploy AAF squad", ["B_soldier_F"], 8] call Root_fnc_batcomInit;
 */

params [
    ["_command", "", [""]],
    ["_params", nil],
    ["_flag", false, [false]]
];

if (!isServer) exitWith {
    ["BATCOM", "ERROR", "batcomInit: Must be executed on server"] call FUNC(logMessage);
    nil
};

if (!(call FUNC(isEnabled))) exitWith {
    ["BATCOM", "ERROR", "batcomInit: BATCOM is not initialized"] call FUNC(logMessage);
    nil
};

if (_command isEqualTo "") exitWith {
    ["BATCOM", "ERROR", "batcomInit: Empty command"] call FUNC(logMessage);
    nil
};

// Log command
["BATCOM", "INFO", format ["Admin command: %1", _command]] call FUNC(logMessage);

// Normalize legacy deployCommander signature to Python's flag param
if (_command isEqualTo "deployCommander") then {
    if (_params isEqualType true) then {
        _flag = _params;
        _params = nil;
    };
};

private _normalizeSidesToString = {
    params ["_rawSides"];

    // Accept a single string/side by wrapping it
    if !(_rawSides isEqualType []) then {
        _rawSides = [_rawSides];
    };

    private _sidesAsStrings = [];

    {
        private _value = _x;
        private _sideString = "";

        // Convert Side objects to their string representation
        if (_value isEqualType east) then {
            _sideString = str _value;  // "EAST", "WEST", "GUER", "CIV"
        } else {
            // Accept common string variants and normalize them
            private _inputStr = if (_value isEqualType "") then {_value} else {str _value};
            _sideString = switch (toUpper _inputStr) do {
                case "EAST": {"EAST"};
                case "OPFOR": {"EAST"};
                case "OP": {"EAST"};
                case "RED": {"EAST"};
                case "WEST": {"WEST"};
                case "BLUFOR": {"WEST"};
                case "BLU": {"WEST"};
                case "BLUE": {"WEST"};
                case "GUER": {"GUER"};
                case "GUERRILLA": {"GUER"};
                case "RESISTANCE": {"GUER"};
                case "INDEPENDENT": {"GUER"};
                case "INDFOR": {"GUER"};
                case "IND": {"GUER"};
                case "GREEN": {"GUER"};
                case "GRN": {"GUER"};
                case "CIV": {"CIV"};
                case "CIVILIAN": {"CIV"};
                case "CIVI": {"CIV"};
                default {""};
            };
        };

        if (_sideString != "") then {
            _sidesAsStrings pushBackUnique _sideString;
        } else {
            ["BATCOM", "WARN", format ["batcomInit: Ignoring invalid side '%1' for %2", _value, _command]] call FUNC(logMessage);
        };
    } forEach _rawSides;

    _sidesAsStrings
};

// Helper: convert string sides to Side objects for SQF variables
private _normalizeSidesToObjects = {
    params ["_rawSides"];

    // Accept a single string/side by wrapping it
    if !(_rawSides isEqualType []) then {
        _rawSides = [_rawSides];
    };

    private _sides = [];

    {
        private _value = _x;
        private _side = if (_value isEqualType east) then {
            _value
        } else {
            switch (toUpper (str _value)) do {
                case "EAST": {east};
                case "WEST": {west};
                case "GUER";
                case "GUERRILLA";
                case "RESISTANCE";
                case "INDEPENDENT": {resistance};
                case "CIV";
                case "CIVILIAN": {civilian};
                default {sideUnknown};
            }
        };

        if (_side isEqualType east && {_side != sideUnknown}) then {
            _sides pushBackUnique _side;
        };
    } forEach _rawSides;

    _sides
};

// Pre-process params for commands that require side normalization
// This ensures Python receives valid string arrays
if (_command in ["commanderAllies", "commanderSides"] && {_params isEqualType []}) then {
    ["BATCOM", "ERROR", format ["batcomInit: Before normalization - command=%1, params count=%2, type=%3, value=%4", _command, count _params, typeName _params, _params]] call FUNC(logMessage);
    private _normalizedStrings = [_params] call _normalizeSidesToString;
    ["BATCOM", "ERROR", format ["batcomInit: After normalization - result count=%1, value=%2", count _normalizedStrings, _normalizedStrings]] call FUNC(logMessage);
    if (_normalizedStrings isEqualTo []) then {
        // Set defaults if normalization failed
        if (_command == "commanderAllies") then {
            _normalizedStrings = ["EAST", "GUER"];
            ["BATCOM", "WARN", "batcomInit: No valid friendly sides provided, defaulting to EAST and GUER"] call FUNC(logMessage);
        } else {
            _normalizedStrings = ["EAST"];
            ["BATCOM", "WARN", "batcomInit: No valid controlled sides provided, defaulting to EAST"] call FUNC(logMessage);
        };
    };
    _params = _normalizedStrings;
};

// Safety: ensure params/flag are valid before passing to Python (Pythia can't serialize nil)
if (isNil "_params" || {isNil {_params}}) then {_params = "";};
if (isNil "_flag" || {isNil {_flag}}) then {_flag = false;};

// Route to Python
private _resultArray = ["batcom.batcom_init", [_command, _params, _flag]] call FUNC(pythiaCall);

if (isNil "_resultArray") exitWith {
    ["BATCOM", "ERROR", format ["batcomInit: Failed to execute command: %1", _command]] call FUNC(logMessage);
    nil
};

// Convert result array to hashmap (Pythia doesn't support dict->hashmap)
private _result = if (_resultArray isEqualType []) then {
    [_resultArray] call FUNC(arrayToHashmap)
} else {
    createHashMap
};

// Check result
private _status = _result getOrDefault ["status", ""];
if (_status isEqualTo "ok") then {
    private _message = _result getOrDefault ["message", "Command executed successfully"];
    ["BATCOM", "INFO", format ["batcomInit: %1", _message]] call FUNC(logMessage);

    // Display to admin
    systemChat format ["BATCOM: %1", _message];

    // Keep local SQF state in sync with the admin commands so scans work
    switch (_command) do {
        case "commanderBrief": {
            // _params = mission intent, _flag = clear memory
            [_params, _flag] call FUNC(setMissionIntent);
        };
        case "commanderAllies": {
            // _params is already normalized to string array by pre-processing above
            // Convert strings to Side objects for SQF variables
            if (_params isEqualType []) then {
                private _sideObjects = _params call _normalizeSidesToObjects;
                if (_sideObjects isEqualTo []) then {
                    _sideObjects = [east, resistance];
                };
                GVAR(friendlySides) = _sideObjects;
            };
        };
        case "commanderSides": {
            // _params is already normalized to string array by pre-processing above
            // Convert strings to Side objects for SQF variables
            if (_params isEqualType []) then {
                private _sideObjects = _params call _normalizeSidesToObjects;
                if (_sideObjects isEqualTo []) then {
                    _sideObjects = [east];
                };
                GVAR(controlledSides) = _sideObjects;
            };
        };
        case "setGeminiApiKey": {
            // Do not log or echo the key; Python handles storage and init
        };
        case "setLLMApiKey": {
            // Runtime multi-provider key injection (Python handles storage/init)
        };
        case "setLLMConfig": {
            // Runtime multi-provider config injection (Python handles storage/init)
        };
        case "deployCommander": {
            // Support both documented signature ["deployCommander", true] and the legacy 3-arg form
            private _deploy = [_flag, _params] select (_params isEqualType true);
            [_deploy] call FUNC(deployCommander);
        };
        case "commanderControlGroups": {
            if (_params isEqualType []) then {
                GVAR(controlledGroupOverrides) = _params;
            };
        };
        case "commanderGuardrails": {
            if (_params isEqualType createHashMap) then {
                if ("ao_bounds" in _params) then {
                    GVAR(aoBounds) = _params get "ao_bounds";
                } else {
                    if ("ao" in _params) then {
                        GVAR(aoBounds) = _params get "ao";
                    };
                };
            };
        };
        case "commanderStartAO": {
            // AO tracking started - Python handles the state
            // SQF already called the initialization via fn_commanderStartAO
        };
        case "commanderEndAO": {
            // AO tracking ended - Python returns HVT data
            // SQF already handled HVT application via fn_commanderEndAO
            private _hvtData = _result getOrDefault ["hvt_data", createHashMap];
            private _hvtPlayers = _hvtData getOrDefault ["players", []];
            private _hvtGroups = _hvtData getOrDefault ["groups", []];

            ["BATCOM", "INFO", format ["AO ended - %1 HVT players, %2 HVT groups designated",
                count _hvtPlayers, count _hvtGroups]] call FUNC(logMessage);
        };
        case "commanderSetHVT": {
            // Manual HVT designation - Python handles the state
        };
    };

    _message
} else {
    private _error = _result getOrDefault ["error", "Unknown error"];
    ["BATCOM", "ERROR", format ["batcomInit: Error: %1", _error]] call FUNC(logMessage);

    // Display error to admin
    systemChat format ["BATCOM ERROR: %1", _error];
    nil
};
