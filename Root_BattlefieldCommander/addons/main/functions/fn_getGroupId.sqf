#include "..\script_component.hpp"
/*
 * Author: Root
 * Generate a stable, unique ID for a group
 *
 * Arguments:
 * 0: Group <GROUP>
 *
 * Return Value:
 * Group ID <STRING>
 *
 * Example:
 * _id = [_group] call BATCOM_fnc_getGroupId;
 */

params [
    ["_group", grpNull, [grpNull]]
];

if (isNull _group) exitWith {""};

// Check if group already has an ID assigned
private _existingId = _group getVariable [QGVAR(groupId), ""];
if (_existingId != "") exitWith {_existingId};

// Generate new ID using group's network ID
private _netId = netId (leader _group);
private _side = side _group;
private _groupId = format ["GRP_%1_%2", _side, _netId];

// Store ID on group
_group setVariable [QGVAR(groupId), _groupId];

_groupId
