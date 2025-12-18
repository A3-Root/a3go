#include "..\script_component.hpp"
/*
 * Author: Root
 * Start AO tracking
 *
 * Arguments:
 * 0: AO Identifier <STRING>
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * ["AO_Mission_1"] call Root_fnc_commanderStartAO
 */

params [["_aoId", "", [""]]];

if (_aoId == "") exitWith {
    ["BATCOM", "ERROR", "commanderStartAO requires AO ID"] call FUNC(logMessage);
    false
};

// Initialize casualty tracking if not already done
call Root_fnc_initCasualtyTracking;

// Start contribution tracking loop
if (isNil "BATCOM_contribution_loop_running") then {
    BATCOM_contribution_loop_running = true;
    [] spawn {
        while {BATCOM_contribution_loop_running} do {
            call Root_fnc_trackObjectiveContributions;
            sleep 10;  // Track every 10 seconds
        };
    };
};

// Get world and mission name
private _worldName = worldName;
private _missionName = missionName;

// Call Python API with world and mission name
private _params = createHashMapFromArray [
    ["ao_id", _aoId],
    ["world_name", _worldName],
    ["mission_name", _missionName]
];
private _result = ["batcom.batcom_init", ["commanderStartAO", _params, true]] call py3_fnc_callExtension;

["BATCOM", "INFO", format ["Started AO tracking: %1", _aoId]] call FUNC(logMessage);

true
