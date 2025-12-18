#include "..\script_component.hpp"
/*
 * Author: Root
 * Log a message to Arma RPT file
 *
 * Arguments:
 * 0: Component <STRING>
 * 1: Level <STRING> (INFO, WARN, ERROR, DEBUG)
 * 2: Message <STRING>
 *
 * Return Value:
 * None
 *
 * Example:
 * ["BATCOM", "INFO", "System initialized"] call BATCOM_fnc_logMessage;
 */

params [
    ["_component", "BATCOM", [""]],
    ["_level", "INFO", [""]],
    ["_message", "", [""]]
];

private _timestamp = [time, "HH:MM:SS"] call BIS_fnc_timeToString;
private _formattedMessage = format ["[%1] [%2] [%3] %4", _timestamp, _component, _level, _message];

// Only emit INFO/DEBUG when debug mode is enabled; always emit WARN/ERROR
private _debugEnabled = missionNamespace getVariable [QGVAR(debugMode), false];
if (_level in ["ERROR", "WARN"] || _debugEnabled) then {
    diag_log _formattedMessage;
};
