#include "..\script_component.hpp"
/*
 * Author: Root
 * Set the mission intent/description for the AI commander
 *
 * Arguments:
 * 0: Mission intent <STRING> - Description of mission objectives
 * 1: Clear memory <BOOL> (optional, default: false) - Whether to clear previous context
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * ["Protect HVT and defend bases", true] call BATCOM_fnc_setMissionIntent;
 */

params [
    ["_intent", "", [""]],
    ["_clearMemory", false, [false]]
];

if (!isServer) exitWith {false};

if (_intent isEqualTo "") exitWith {
    ["BATCOM", "ERROR", "setMissionIntent: Empty intent"] call FUNC(logMessage);
    false
};

// Store locally
GVAR(missionIntent) = _intent;

["BATCOM", "INFO", format ["Mission intent set: %1 (clear: %2)", _intent, _clearMemory]] call FUNC(logMessage);

true
