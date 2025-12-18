#include "..\script_component.hpp"
/*
 * Author: Root
 * Wrapper for py3_fnc_callExtension with error handling
 *
 * Arguments:
 * 0: Function name <STRING>
 * 1: Arguments array <ARRAY>
 *
 * Return Value:
 * Result from Python or nil on error <ANY>
 *
 * Example:
 * ["batcom.init", [_config]] call BATCOM_fnc_pythiaCall;
 */

params [
    ["_functionName", "", [""]],
    ["_arguments", [], [[]]]
];

private _debug = missionNamespace getVariable [QGVAR(debugMode), false];
private _dlog = {
    params ["_msg", "_debugFlag"];
    if (_debugFlag) then {diag_log _msg;};
};

["BATCOM: ========================================", _debug] call _dlog;
[format ["BATCOM: [PYTHIA CALL] Function: %1", _functionName], _debug] call _dlog;
[format ["BATCOM: [PYTHIA CALL] Arguments count: %1", count _arguments], _debug] call _dlog;
[format ["BATCOM: [PYTHIA CALL] Arguments types: %1", _arguments apply {typeName _x}], _debug] call _dlog;

if (_functionName isEqualTo "") exitWith {
    ["BATCOM", "ERROR", "pythiaCall: Function name cannot be empty"] call FUNC(logMessage);
    ["BATCOM: [PYTHIA CALL] ✗ ERROR - Empty function name", _debug] call _dlog;
    ["BATCOM: ========================================", _debug] call _dlog;
    nil
};

// Check if Pythia is available
if (isNil "py3_fnc_callExtension") exitWith {
    ["BATCOM", "ERROR", "pythiaCall: Pythia extension not available"] call FUNC(logMessage);
    ["BATCOM: [PYTHIA CALL] ✗ ERROR - Pythia not available", _debug] call _dlog;
    ["BATCOM: ========================================", _debug] call _dlog;
    nil
};

["BATCOM: [PYTHIA CALL] Calling py3_fnc_callExtension...", _debug] call _dlog;

// Call Pythia extension
toFixed 6;
private _startTime = diag_tickTime;
private _result = try {
    private _response = [_functionName, _arguments] call py3_fnc_callExtension;
    if (isNil "_response") then {
        throw format ["py3_fnc_callExtension returned nil for %1", _functionName];
    };
    _response
} catch {
    ["BATCOM", "ERROR", format ["pythiaCall: Exception calling %1: %2", _functionName, _exception]] call FUNC(logMessage);
    [format ["BATCOM: [PYTHIA CALL] ✗ EXCEPTION: %1", _exception], _debug] call _dlog;
    nil
};
private _endTime = diag_tickTime;
private _duration = (_endTime - _startTime) * 1000; // Convert to ms
toFixed -1;

[format ["BATCOM: [PYTHIA CALL] Call completed in %1 ms", _duration], _debug] call _dlog;

// Check if call succeeded
if (isNil "_result") then {
    ["BATCOM", "ERROR", format ["pythiaCall: Failed to call %1", _functionName]] call FUNC(logMessage);
    [format ["BATCOM: [PYTHIA CALL] ✗ Result is nil for %1", _functionName], _debug] call _dlog;
    ["BATCOM: ========================================", _debug] call _dlog;
} else {
    [format ["BATCOM: [PYTHIA CALL] ✓ Result type: %1", typeName _result], _debug] call _dlog;
    if (_result isEqualType []) then {
        [format ["BATCOM: [PYTHIA CALL] ✓ Result is ARRAY with %1 elements", count _result], _debug] call _dlog;
    } else {
        if (_result isEqualType "") then {
            private _preview = if (count _result > 100) then {
                ((_result select [0, 97]) + "...")
            } else {
                _result
            };
            [format ["BATCOM: [PYTHIA CALL] ✓ Result is STRING: %1", _preview], _debug] call _dlog;
        } else {
            [format ["BATCOM: [PYTHIA CALL] ✓ Result value: %1", _result], _debug] call _dlog;
        };
    };
    ["BATCOM: ========================================", _debug] call _dlog;
};

_result
