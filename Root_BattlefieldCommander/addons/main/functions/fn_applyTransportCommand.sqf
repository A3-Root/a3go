#include "..\script_component.hpp"
/*
 * Apply a transport_group command.
 *
 * Arguments:
 * 0: Vehicle group <GROUP> (also command group)
 * 1: Command params <HASHMAP>
 *    - vehicle_group_id: vehicle group id (redundant, for logging)
 *    - passenger_group_id: group to transport
 *    - pickup: [x,y,z]
 *    - dropoff: [x,y,z]
 *
 * Returns:
 * Success <BOOL>
 */

params [
    ["_vehGroup", grpNull, [grpNull]],
    ["_params", createHashMap, [createHashMap]]
];

if (isNull _vehGroup) exitWith {
    ["BATCOM", "ERROR", "applyTransportCommand: Invalid vehicle group"] call FUNC(logMessage);
    false
};

private _pickup = _params getOrDefault ["pickup", []];
private _dropoff = _params getOrDefault ["dropoff", []];
private _passengerGroupId = _params getOrDefault ["passenger_group_id", ""];

if (count _pickup < 2 || {count _dropoff < 2}) exitWith {
    ["BATCOM", "ERROR", "applyTransportCommand: Invalid pickup/dropoff"] call FUNC(logMessage);
    false
};

private _passengerGroup = [_passengerGroupId] call FUNC(resolveGroup);
if (isNull _passengerGroup) exitWith {
    ["BATCOM", "ERROR", format ["applyTransportCommand: Passenger group not found: %1", _passengerGroupId]] call FUNC(logMessage);
    false
};

// Vehicle reference
private _veh = vehicle (leader _vehGroup);

// Prep passenger movement to pickup
while {waypoints _passengerGroup isNotEqualTo []} do { deleteWaypoint ((waypoints _passengerGroup) select 0); };
private _wpPickupPax = _passengerGroup addWaypoint [_pickup, 0];
_wpPickupPax setWaypointType "MOVE";
_wpPickupPax setWaypointSpeed "FULL";
_wpPickupPax setWaypointBehaviour "AWARE";

// Order passengers to board the transport
{
    _x assignAsCargo _veh;
    _x orderGetIn true;
} forEach units _passengerGroup;

// Vehicle path: to pickup, then transport unload at dropoff
while {waypoints _vehGroup isNotEqualTo []} do { deleteWaypoint ((waypoints _vehGroup) select 0); };
private _wpPickupVeh = _vehGroup addWaypoint [_pickup, 0];
_wpPickupVeh setWaypointType "MOVE";
_wpPickupVeh setWaypointSpeed "FULL";
_wpPickupVeh setWaypointBehaviour "AWARE";
_wpPickupVeh setWaypointCompletionRadius 30;

private _wpUnload = _vehGroup addWaypoint [_dropoff, 0];
_wpUnload setWaypointType "TR UNLOAD";
_wpUnload setWaypointSpeed "FULL";
_wpUnload setWaypointBehaviour "AWARE";
_wpUnload setWaypointCompletionRadius 30;

// After unload, disembark passengers and set them to move off the LZ a bit
[_vehGroup, _passengerGroup, _dropoff] spawn {
    params ["_vg", "_pg", "_lz"];
    waitUntil {
        sleep 1;
        isNull _vg || {currentWaypoint _vg >= 2}
    };
    if (isNull _pg) exitWith {};
    {
        unassignVehicle _x;
        doGetOut _x;
    } forEach units _pg;
    private _offset = [(_lz select 0) + 15 - (random 30), (_lz select 1) + 15 - (random 30), 0];
    _pg addWaypoint [_offset, 0];
};

private _vehGroupId = [_vehGroup] call FUNC(getGroupId);
["BATCOM", "INFO", format ["applyTransportCommand: %1 moving %2 from %3 to %4", _vehGroupId, _passengerGroupId, _pickup, _dropoff]] call FUNC(logMessage);

true
