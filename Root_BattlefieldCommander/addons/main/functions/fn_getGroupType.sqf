#include "..\script_component.hpp"
/*
 * Author: Root
 * Classify a group by its vehicle/unit composition
 *
 * Arguments:
 * 0: Group <GROUP>
 *
 * Return Value:
 * Group type <STRING> - "infantry", "motorized", "mechanized", "armor", "air_rotary", "air_fixed", "naval"
 *
 * Example:
 * _type = [_group] call BATCOM_fnc_getGroupType;
 */

params [
    ["_group", grpNull, [grpNull]]
];

if (isNull _group) exitWith {"unknown"};

private _units = units _group;
if (_units isEqualTo []) exitWith {"unknown"};

// Get vehicles used by the group
private _vehicles = [];
{
    private _veh = vehicle _x;
    if (_veh != _x && {!(_veh in _vehicles)}) then {
        _vehicles pushBack _veh;
    };
} forEach _units;

// If no vehicles, it's infantry
if (_vehicles isEqualTo []) exitWith {"infantry"};

// Classify by most significant vehicle type
private _hasAir = false;
private _hasArmor = false;
private _hasMech = false;
private _hasMotorized = false;
private _hasNaval = false;
private _type = "";

{
    private _veh = _x;

    // Air vehicles
    if (_veh isKindOf "Air") exitWith {
        _hasAir = true;
        if (_veh isKindOf "Helicopter") then {
            _type = "air_rotary";
        } else {
            _type = "air_fixed";
        };
    };

    // Naval vehicles
    if (_veh isKindOf "Ship") exitWith {
        _hasNaval = true;
    };

    // Armor (tanks)
    if (_veh isKindOf "Tank") exitWith {
        _hasArmor = true;
    };

    // Mechanized (APCs, IFVs)
    if (_veh isKindOf "Wheeled_APC_F" || {_veh isKindOf "Tracked_APC_F"}) exitWith {
        _hasMech = true;
    };

    // Motorized (trucks, cars)
    if (_veh isKindOf "Car" || {_veh isKindOf "Truck"}) exitWith {
        _hasMotorized = true;
    };
} forEach _vehicles;

// Return most significant type
if (_hasAir) exitWith {
    if (_type isEqualTo "air_fixed") exitWith {"air_fixed"};
    "air_rotary"
};
if (_hasNaval) exitWith {"naval"};
if (_hasArmor) exitWith {"armor"};
if (_hasMech) exitWith {"mechanized"};
if (_hasMotorized) exitWith {"motorized"};

"infantry"
