#include "..\script_component.hpp"
/*
 * Apply an escort_group command.
 *
 * Arguments:
 * 0: Escort group <GROUP>
 * 1: Command params <HASHMAP>
 *    - escort_group_id: escort group id (redundant)
 *    - target_group_id: group to escort
 *    - radius: desired follow radius
 *
 * Returns:
 * Success <BOOL>
 */

params [
    ["_escortGroup", grpNull, [grpNull]],
    ["_params", createHashMap, [createHashMap]]
];

if (isNull _escortGroup) exitWith {
    ["BATCOM", "ERROR", "applyEscortCommand: Invalid escort group"] call FUNC(logMessage);
    false
};

private _targetId = _params getOrDefault ["target_group_id", ""];
private _radius = _params getOrDefault ["radius", 75];
private _targetGroup = [_targetId] call FUNC(resolveGroup);

if (isNull _targetGroup) exitWith {
    ["BATCOM", "ERROR", format ["applyEscortCommand: Target group not found: %1", _targetId]] call FUNC(logMessage);
    false
};

// Basic follow behaviour: move near the target and follow the leader
while {waypoints _escortGroup isNotEqualTo []} do { deleteWaypoint ((waypoints _escortGroup) select 0); };

private _targetPos = getPosATL (leader _targetGroup);
private _wp = _escortGroup addWaypoint [_targetPos, 0];
_wp setWaypointType "MOVE";
_wp setWaypointSpeed "NORMAL";
_wp setWaypointBehaviour "AWARE";
_wp setWaypointCombatMode "YELLOW";
_wp setWaypointCompletionRadius _radius max 20;
_escortGroup setBehaviour "AWARE";
_escortGroup setCombatMode "YELLOW";

// Periodically update to keep station with target
[_escortGroup, _targetGroup, _radius] spawn {
    params ["_eg", "_tg", "_rad"];
    while {!(isNull _eg) && !(isNull _tg)} do {
        private _pos = getPosATL (leader _tg);
        private _wps = waypoints _eg;
        if (_wps isNotEqualTo []) then {
            private _w = _wps select 0;
            _w setWaypointPosition [_pos, 0];
        };
        (leader _eg) doFollow (leader _tg);
        sleep 5;
    };
};

private _escortId = [_escortGroup] call FUNC(getGroupId);
["BATCOM", "INFO", format ["applyEscortCommand: %1 escorting %2 (r:%3)", _escortId, _targetId, _radius]] call FUNC(logMessage);

true
