#include "..\script_component.hpp"
/*
 * Author: Root
 * Apply a defend_area command to a group (creates circular patrol around position)
 *
 * Arguments:
 * 0: Group <GROUP>
 * 1: Command parameters <HASHMAP>
 *    - position: Center position [x, y, z]
 *    - radius: Defense radius (optional, default: 100)
 *    - garrison: Whether to garrison buildings (optional, default: false)
 *    - behaviour: Behaviour (optional, default: "AWARE")
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * [_group, createHashMapFromArray [["position", [1234, 5678, 0]], ["radius", 150]]] call BATCOM_fnc_applyDefendCommand;
 */

params [
    ["_group", grpNull, [grpNull]],
    ["_params", createHashMap, [createHashMap]]
];

if (isNull _group) exitWith {
    ["BATCOM", "ERROR", "applyDefendCommand: Invalid group"] call FUNC(logMessage);
    false
};

private _position = _params getOrDefault ["position", []];
if (count _position < 2) exitWith {
    ["BATCOM", "ERROR", "applyDefendCommand: Invalid position"] call FUNC(logMessage);
    false
};

private _radius = _params getOrDefault ["radius", 100];
private _garrison = _params getOrDefault ["garrison", false];
private _behaviour = _params getOrDefault ["behaviour", "AWARE"];
_group setBehaviour _behaviour;
_group setCombatMode "YELLOW";

// Clear existing waypoints
while {waypoints _group isNotEqualTo []} do {
    deleteWaypoint ((waypoints _group) select 0);
};

// Create 4-point circular patrol around position
private _angles = [0, 90, 180, 270];
{
    private _angle = _x;
    private _wpPos = [
        (_position select 0) + (_radius * cos _angle),
        (_position select 1) + (_radius * sin _angle),
        0
    ];

    private _wp = _group addWaypoint [_wpPos, 0];
    _wp setWaypointType "MOVE";
    _wp setWaypointBehaviour _behaviour;
    _wp setWaypointCombatMode "YELLOW";
    _wp setWaypointSpeed "LIMITED";
    _wp setWaypointFormation "WEDGE";
} forEach _angles;

// No cycle waypoint - units will hold position at final waypoint

// If garrison requested, add garrison script (simplified)
if (_garrison) then {
    {
        private _leader = leader _group;
        _leader setVariable [QGVAR(garrison), true];
    };
};

private _groupId = [_group] call FUNC(getGroupId);
["BATCOM", "INFO", format ["applyDefendCommand: %1 defending %2 (r:%3m)", _groupId, _position, _radius]] call FUNC(logMessage);

true
