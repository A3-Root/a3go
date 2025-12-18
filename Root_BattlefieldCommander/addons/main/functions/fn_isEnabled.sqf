#include "..\script_component.hpp"
/*
 * Author: Root
 * Check if BATCOM is enabled and initialized
 *
 * Arguments:
 * None
 *
 * Return Value:
 * True if enabled <BOOL>
 *
 * Example:
 * if (call BATCOM_fnc_isEnabled) then { hint "BATCOM is running"; };
 */

if (!isServer) exitWith {false};

!isNil QGVAR(enabled) && GVAR(enabled)
