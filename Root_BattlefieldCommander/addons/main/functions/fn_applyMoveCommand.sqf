#include "..\script_component.hpp"
/*
 * Author: Root
 * Apply a move_to command to a group
 *
 * Arguments:
 * 0: Group <GROUP>
 * 1: Command parameters <HASHMAP>
 *    - position: Target position [x, y, z]
 *    - speed: Speed mode (optional, default: "NORMAL")
 *    - formation: Formation (optional, default: current)
 *    - behaviour: Behaviour (optional, default: "AWARE")
 *    - combat_mode: Combat mode (optional, default: "YELLOW")
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * [_group, createHashMapFromArray [["position", [1234, 5678, 0]]]] call BATCOM_fnc_applyMoveCommand;
 */

params [
    ["_group", grpNull, [grpNull]],
    ["_params", createHashMap, [createHashMap]]
];

if (isNull _group) exitWith {
    ["BATCOM", "ERROR", "applyMoveCommand: Invalid group"] call FUNC(logMessage);
    false
};

private _position = _params getOrDefault ["position", []];
if (count _position < 2) exitWith {
    ["BATCOM", "ERROR", "applyMoveCommand: Invalid position"] call FUNC(logMessage);
    false
};

// Clear existing waypoints
while {waypoints _group isNotEqualTo []} do {
    deleteWaypoint ((waypoints _group) select 0);
};

private _behaviour = _params getOrDefault ["behaviour", "AWARE"];
private _combatMode = _params getOrDefault ["combat_mode", "YELLOW"];

// Add move waypoint
private _wp = _group addWaypoint [_position, 0];
_wp setWaypointType "MOVE";
_group setBehaviour _behaviour;
_group setCombatMode _combatMode;

// Apply optional parameters
private _speed = _params getOrDefault ["speed", "NORMAL"];
_group setSpeedMode _speed;

private _formation = _params getOrDefault ["formation", ""];
if (_formation != "") then {
    _group setFormation _formation;
};

_wp setWaypointBehaviour _behaviour;

_wp setWaypointCombatMode _combatMode;

private _groupId = [_group] call FUNC(getGroupId);
["BATCOM", "INFO", format ["applyMoveCommand: %1 -> %2", _groupId, _position]] call FUNC(logMessage);

true
