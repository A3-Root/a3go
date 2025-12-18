#include "..\script_component.hpp"
/*
 * Author: Root
 * Add a runtime objective to the mission
 *
 * Arguments:
 * 0: Description <STRING> - Objective description
 * 1: Unit class names <ARRAY> - Array of unit class names for spawning
 * 2: Priority <NUMBER> - Objective priority (higher = more important)
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * ["Deploy AAF squad to hunt players", ["I_Soldier_F", "I_Soldier_AR_F"], 8] call BATCOM_fnc_addObjective;
 */

params [
    ["_description", "", [""]],
    ["_unitClasses", [], [[]]],
    ["_priority", 5, [0]]
];

if (!isServer) exitWith {false};

if (_description isEqualTo "") exitWith {
    ["BATCOM", "ERROR", "addObjective: Empty description"] call FUNC(logMessage);
    false
};

["BATCOM", "INFO", format ["Runtime objective added: %1 (priority: %2, units: %3)",
    _description, _priority, count _unitClasses]] call FUNC(logMessage);

// This will be handled by Python in the future
// For now, just log it

true
