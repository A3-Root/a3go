#include "..\script_component.hpp"
/*
 * Author: Root
 * Shutdown BATCOM and cleanup resources
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * call BATCOM_fnc_shutdown;
 */

if (!isServer) exitWith {};

if (!(call FUNC(isEnabled))) exitWith {
    ["BATCOM", "WARN", "shutdown: BATCOM is not initialized"] call FUNC(logMessage);
};

["BATCOM", "INFO", "Shutting down BATCOM..."] call FUNC(logMessage);

// Call Python shutdown
["batcom.shutdown", []] call FUNC(pythiaCall);

// Clear global state
GVAR(enabled) = false;
GVAR(deployed) = false;
GVAR(groupRegistry) = nil;
GVAR(asyncThreads) = nil;
GVAR(missionIntent) = nil;
GVAR(friendlySides) = nil;
GVAR(controlledSides) = nil;

["BATCOM", "INFO", "BATCOM shutdown complete"] call FUNC(logMessage);
