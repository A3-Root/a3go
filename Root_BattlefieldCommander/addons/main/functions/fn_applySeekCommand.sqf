#include "..\script_component.hpp"
/*
 * Author: Root
 * Apply a seek_and_destroy command to a group (hunt enemy in area)
 *
 * Arguments:
 * 0: Group <GROUP>
 * 1: Command parameters <HASHMAP>
 *    - position: Target area center [x, y, z]
 *    - radius: Search radius (optional, default: 200)
 *    - behaviour: Behaviour (optional, default: "COMBAT")
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * [_group, createHashMapFromArray [["position", [1234, 5678, 0]], ["radius", 300]]] call BATCOM_fnc_applySeekCommand;
 */

params [
    ["_group", grpNull, [grpNull]],
    ["_params", createHashMap, [createHashMap]]
];

if (isNull _group) exitWith {
    ["BATCOM", "ERROR", "applySeekCommand: Invalid group"] call FUNC(logMessage);
    false
};

private _position = _params getOrDefault ["position", []];
if (count _position < 2) exitWith {
    ["BATCOM", "ERROR", "applySeekCommand: Invalid position"] call FUNC(logMessage);
    false
};

private _radius = _params getOrDefault ["radius", 200];
private _behaviour = _params getOrDefault ["behaviour", "AWARE"];
_group setBehaviour _behaviour;
_group setCombatMode "YELLOW";

// Clear existing waypoints
while {waypoints _group isNotEqualTo []} do {
    deleteWaypoint ((waypoints _group) select 0);
};

// Create search pattern waypoints
private _searchPoints = 5;
for "_i" from 0 to (_searchPoints - 1) do {
    private _angle = (_i / _searchPoints) * 360;
    private _dist = _radius * (0.5 + (random 0.5));  // Randomize distance
    private _wpPos = [
        (_position select 0) + (_dist * cos _angle),
        (_position select 1) + (_dist * sin _angle),
        0
    ];

    private _wp = _group addWaypoint [_wpPos, 0];
    _wp setWaypointType "SAD";  // Search and Destroy
    _wp setWaypointBehaviour _behaviour;
    _wp setWaypointCombatMode "RED";
    _wp setWaypointSpeed "NORMAL";
};

private _groupId = [_group] call FUNC(getGroupId);
["BATCOM", "INFO", format ["applySeekCommand: %1 hunting in %2 (r:%3m)", _groupId, _position, _radius]] call FUNC(logMessage);

true
