#include "..\script_component.hpp"
/*
 * Apply a fire_support command for vehicle/armor/air groups.
 *
 * Arguments:
 * 0: Group <GROUP>
 * 1: Command params <HASHMAP>
 *    - position: target area center [x,y,z]
 *    - radius: engagement radius (default 250)
 *
 * Returns:
 * Success <BOOL>
 */

params [
    ["_group", grpNull, [grpNull]],
    ["_params", createHashMap, [createHashMap]]
];

if (isNull _group) exitWith {
    ["BATCOM", "ERROR", "applyFireSupportCommand: Invalid group"] call FUNC(logMessage);
    false
};

private _position = _params getOrDefault ["position", []];
private _radius = _params getOrDefault ["radius", 250];
_group setBehaviour "AWARE";
_group setCombatMode "YELLOW";

if (count _position < 2) exitWith {
    ["BATCOM", "ERROR", "applyFireSupportCommand: Invalid position"] call FUNC(logMessage);
    false
};

// Clear waypoints and create aggressive search/attack pattern
while {waypoints _group isNotEqualTo []} do { deleteWaypoint ((waypoints _group) select 0); };

private _points = 5;
for "_i" from 0 to (_points - 1) do {
    private _angle = (_i / _points) * 360;
    private _dist = _radius * (0.4 + (random 0.6));
    private _wpPos = [
        (_position select 0) + (_dist * cos _angle),
        (_position select 1) + (_dist * sin _angle),
        0
    ];
    private _wp = _group addWaypoint [_wpPos, 0];
    _wp setWaypointType "SAD";
    _wp setWaypointBehaviour "AWARE";
    _wp setWaypointCombatMode "RED";
    _wp setWaypointSpeed "FULL";
};

// No cycle waypoint - units will hold position at final waypoint

private _groupId = [_group] call FUNC(getGroupId);
["BATCOM", "INFO", format ["applyFireSupportCommand: %1 providing fire support at %2 (r:%3)", _groupId, _position, _radius]] call FUNC(logMessage);

true
