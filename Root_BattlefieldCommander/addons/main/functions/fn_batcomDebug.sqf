#include "..\script_component.hpp"
/*
 * Author: Root
 * Toggle BATCOM debug logging to RPT file
 *
 * Arguments:
 * 0: Enable debug mode <BOOL> - true to enable, false to disable
 *
 * Return Value:
 * None
 *
 * Examples:
 * [true] call Root_fnc_batcomDebug;  // Enable debug logs
 * [false] call Root_fnc_batcomDebug; // Disable debug logs
 */

params [
    ["_enable", true, [true]]
];

if (!isServer) exitWith {
    systemChat "BATCOM: Debug mode can only be toggled on server";
};

// Set global debug flag
GVAR(debugMode) = _enable;

// Log the change
if (_enable) then {
    diag_log "[BATCOM] Debug mode ENABLED - RPT logging active";
    systemChat "BATCOM: Debug mode ENABLED - check RPT logs";
} else {
    diag_log "[BATCOM] Debug mode DISABLED - RPT logging inactive";
    systemChat "BATCOM: Debug mode DISABLED";
};
