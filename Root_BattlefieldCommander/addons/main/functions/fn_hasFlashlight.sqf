#include "..\script_component.hpp"
/*
 * Author: Root
 * Check if unit has flashlight or IR laser active
 *
 * Arguments:
 * 0: Unit <OBJECT>
 *
 * Return Value:
 * True if unit has flashlight or IR laser active <BOOL>
 *
 * Example:
 * _hasLight = [_unit] call BATCOM_fnc_hasFlashlight;
 */

params [
    ["_unit", objNull, [objNull]]
];

if (isNull _unit) exitWith {false};

private _hasLight = isLightOn _unit;
private _weapon = currentWeapon _unit;
private _hasIRLaser = false;

if (_weapon != "") then {
    private _items = _unit weaponAccessories _weapon;
    {
        private _item = _x;
        if (_item != "") then {
            // Check if item is an IR laser (contains "laser" or "pointer")
            private _itemLower = toLower _item;
            if (_itemLower find "laser" >= 0 || _itemLower find "pointer" >= 0) then {
                _hasIRLaser = true;
            };
        };
    } forEach _items;
};

(_hasLight || _hasIRLaser)
