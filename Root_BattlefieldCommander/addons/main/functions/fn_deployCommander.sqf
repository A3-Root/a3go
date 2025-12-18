#include "..\script_component.hpp"
/*
 * Author: Root
 * Deploy or undeploy the AI commander (start/stop decision loops)
 *
 * Arguments:
 * 0: Deploy <BOOL> - true to deploy, false to undeploy
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * [true] call BATCOM_fnc_deployCommander;
 */

params [
    ["_deploy", false, [false]]
];

if (!isServer) exitWith {false};

if (!(call FUNC(isEnabled))) exitWith {
    ["BATCOM", "ERROR", "deployCommander: BATCOM is not initialized"] call FUNC(logMessage);
    false
};

if (_deploy) then {
    // Check if already deployed
    if (GVAR(deployed)) exitWith {
        ["BATCOM", "WARN", "deployCommander: Already deployed"] call FUNC(logMessage);
        true
    };

    // Validate configuration
    if (count (GVAR(controlledSides)) == 0) exitWith {
        ["BATCOM", "ERROR", "deployCommander: No controlled sides configured. Use commanderSides first."] call FUNC(logMessage);
        false
    };

    ["BATCOM", "INFO", "Deploying AI commander..."] call FUNC(logMessage);

    // Set deployed flag
    GVAR(deployed) = true;

    // Get scan interval from config
    private _scanInterval = 2.0;  // Default from CfgBATCOM
    private _commandPollInterval = 1.0;

    // Start world scanning loop
    GVAR(worldScanLoopHandle) = [_scanInterval] spawn compile preprocessFileLineNumbers QPATHTOF(scripts\worldScanLoop.sqf);

    // Start command processing loop
    GVAR(commandProcessLoopHandle) = [_commandPollInterval] spawn compile preprocessFileLineNumbers QPATHTOF(scripts\commandProcessLoop.sqf);

    ["BATCOM", "INFO", "AI commander deployed successfully"] call FUNC(logMessage);
    systemChat "BATCOM: Commander deployed - AI is now active";

    true
} else {
    // Undeploy
    if !(GVAR(deployed)) exitWith {
        ["BATCOM", "WARN", "deployCommander: Not deployed"] call FUNC(logMessage);
        true
    };

    ["BATCOM", "INFO", "Undeploying AI commander..."] call FUNC(logMessage);

    // Set flag to stop loops
    GVAR(deployed) = false;

    // Wait for loops to finish (they check the flag)
    sleep 1;

    // Terminate handles if still running
    if (!isNil QGVAR(worldScanLoopHandle)) then {
        terminate GVAR(worldScanLoopHandle);
        GVAR(worldScanLoopHandle) = nil;
    };

    if (!isNil QGVAR(commandProcessLoopHandle)) then {
        terminate GVAR(commandProcessLoopHandle);
        GVAR(commandProcessLoopHandle) = nil;
    };

    ["BATCOM", "INFO", "AI commander undeployed"] call FUNC(logMessage);
    systemChat "BATCOM: Commander undeployed - AI is now inactive";

    true
};
