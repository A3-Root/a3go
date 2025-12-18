#include "..\script_component.hpp"
/*
 * Author: Root
 * Apply a patrol_route command to a group
 *
 * Arguments:
 * 0: Group <GROUP>
 * 1: Command parameters <HASHMAP>
 *    - waypoints: Array of positions [[x,y,z], [x,y,z], ...]
 *    - speed: Speed mode (optional, default: "LIMITED")
 *    - behaviour: Behaviour (optional, default: "SAFE")
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * [_group, createHashMapFromArray [["waypoints", [[100,200,0], [300,400,0]]]]] call BATCOM_fnc_applyPatrolCommand;
 */

params [
    ["_group", grpNull, [grpNull]],
    ["_params", createHashMap, [createHashMap]]
];

if (isNull _group) exitWith {
    ["BATCOM", "ERROR", "applyPatrolCommand: Invalid group"] call FUNC(logMessage);
    false
};

private _waypoints = _params getOrDefault ["waypoints", []];
if (count _waypoints < 2) exitWith {
    ["BATCOM", "ERROR", "applyPatrolCommand: Need at least 2 waypoints"] call FUNC(logMessage);
    false
};

private _speed = _params getOrDefault ["speed", "LIMITED"];
private _behaviour = _params getOrDefault ["behaviour", "AWARE"];
_group setBehaviour _behaviour;
_group setCombatMode "YELLOW";

// Clear existing waypoints
while {waypoints _group isNotEqualTo []} do {
    deleteWaypoint ((waypoints _group) select 0);
};

// Add waypoints
{
    private _wpPos = _x;
    private _wp = _group addWaypoint [_wpPos, 0];
    _wp setWaypointType "MOVE";
    _wp setWaypointBehaviour _behaviour;
    _wp setWaypointSpeed _speed;
} forEach _waypoints;

// No cycle waypoint - units will hold position at final waypoint

private _groupId = [_group] call FUNC(getGroupId);
["BATCOM", "INFO", format ["applyPatrolCommand: %1 patrolling %2 waypoints", _groupId, count _waypoints]] call FUNC(logMessage);

true
