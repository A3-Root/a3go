#include "..\script_component.hpp"
/*
 * Author: Root
 * Resolve a group object from a group ID
 *
 * Arguments:
 * 0: Group ID <STRING>
 *
 * Return Value:
 * Group object or grpNull if not found <GROUP>
 *
 * Example:
 * _group = ["GRP_EAST_1234"] call BATCOM_fnc_resolveGroup;
 */

params [
    ["_groupId", "", [""]]
];

if (_groupId isEqualTo "") exitWith {
    ["BATCOM", "ERROR", "resolveGroup: Empty group ID"] call FUNC(logMessage);
    grpNull
};

// Search through all groups
{
    private _storedId = _x getVariable [QGVAR(groupId), ""];
    if (_storedId isEqualTo _groupId) exitWith {_x};
    grpNull
} forEach allGroups
