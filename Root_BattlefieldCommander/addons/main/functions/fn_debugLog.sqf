#include "..\script_component.hpp"
/*
 * Author: Root
 * Conditional debug logging to RPT file
 * Only logs if debug mode is enabled
 *
 * Arguments:
 * 0: Message <STRING> - Message to log
 *
 * Return Value:
 * None
 *
 * Examples:
 * ["Test message"] call BATCOM_fnc_debugLog;
 */

params [
    ["_message", "", [""]]
];

// Only log if debug mode is enabled
if (GVAR(debugMode)) then {
    diag_log format ["[BATCOM DEBUG] %1", _message];
};
