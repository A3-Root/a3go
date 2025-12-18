#include "..\script_component.hpp"
/*
 * Author: Root
 * Report task completion to BATCOM effectiveness tracker
 * This is the unified interface for all objective completions
 *
 * Arguments:
 * 0: Task Name <STRING> - Type of task completed
 * 1: Task Info <ARRAY> - Task-specific information (object name, unit ID, etc.)
 * 2: Player UID <STRING> - UID of player who completed the task
 * 3: Group ID <STRING> - Group ID of the completing player
 *
 * Task Names and Expected Task Info:
 * - "commander_killed": [commander_unit] - HQ commander killed (+30 pts)
 * - "commander_captured": [commander_unit] - HQ commander captured alive (+40 pts)
 * - "hvt_killed": [hvt_unit] - HVT killed (+25 pts)
 * - "hvt_captured": [hvt_unit] - HVT captured alive (+35 pts)
 * - "radiotower_destroyed": [tower_object] - Radio tower destroyed (+20 pts)
 * - "radiotower_disabled": [tower_object] - Radio tower disabled (+20 pts)
 * - "gpsjammer_destroyed": [jammer_object] - GPS jammer destroyed (+20 pts)
 * - "gpsjammer_disabled": [jammer_object] - GPS jammer disabled (+20 pts)
 * - "supplydepot_captured": [depot_object] - Supply depot captured (+15 pts)
 * - "mortarpit_neutralized": [mortar_position] - Mortar pit neutralized
 * - "aasite_destroyed": [aa_vehicle] - AA site destroyed
 * - "hmgtower_neutralized": [tower_object] - HMG tower neutralized
 *
 * Proximity Bonuses:
 * - For commander/HVT captures and kills, nearby players (50m) automatically get +10 pts
 *
 * Return Value:
 * Success <BOOL>
 *
 * Examples:
 * // Commander captured via addAction
 * ["commander_captured", [_commander], getPlayerUID _capturer, groupId (group _capturer)] call BATCOM_fnc_taskComplete;
 *
 * // HVT killed
 * ["hvt_killed", [_hvt], getPlayerUID _killer, groupId (group _killer)] call BATCOM_fnc_taskComplete;
 *
 * // Radio tower destroyed
 * ["radiotower_destroyed", [_tower], getPlayerUID _destroyer, groupId (group _destroyer)] call BATCOM_fnc_taskComplete;
 *
 * // Supply depot captured with custom object name
 * ["supplydepot_captured", ["Supply Depot North"], getPlayerUID _capturer, groupId (group _capturer)] call BATCOM_fnc_taskComplete;
 */

params [
    ["_taskName", "", [""]],
    ["_taskInfo", [], [[]]],
    ["_playerUID", "", [""]],
    ["_groupID", "", [""]]
];

if (!isServer) exitWith {
    ["BATCOM", "ERROR", "taskComplete: Must be executed on server"] call FUNC(logMessage);
    false
};

if (!(call FUNC(isEnabled))) exitWith {
    ["BATCOM", "WARN", "taskComplete: BATCOM is not enabled"] call FUNC(logMessage);
    false
};

if (_taskName isEqualTo "" || _playerUID isEqualTo "") exitWith {
    ["BATCOM", "ERROR", "taskComplete: taskName and playerUID are required"] call FUNC(logMessage);
    false
};

// Map task names to aoProgress event types
private _eventTypeMapping = createHashMapFromArray [
    ["commander_killed", "commanderKilled"],
    ["commander_captured", "commanderCaptured"],
    ["hvt_killed", "hvtEliminated"],
    ["hvt_captured", "hvtCaptured"],
    ["radiotower_destroyed", "radioTowerDestroyed"],
    ["radiotower_disabled", "radioTowerNeutralized"],
    ["gpsjammer_destroyed", "gpsJammerDestroyed"],
    ["gpsjammer_disabled", "gpsJammerDisabled"],
    ["supplydepot_captured", "supplyDepotCaptured"],
    ["mortarpit_neutralized", "mortarPitNeutralized"],
    ["aasite_destroyed", "aaSiteDestroyed"],
    ["hmgtower_neutralized", "hmgTowerNeutralized"]
];

private _eventType = _eventTypeMapping getOrDefault [_taskName, ""];
if (_eventType isEqualTo "") exitWith {
    ["BATCOM", "ERROR", format ["taskComplete: Unknown task name: %1", _taskName]] call FUNC(logMessage);
    false
};

// Extract objective ID from task info
private _objectiveID = "";
if (_taskInfo isNotEqualTo []) then {
    private _taskData = _taskInfo select 0;

    // If it's an object, get its variable name or class
    if (_taskData isEqualType objNull) then {
        private _varName = vehicleVarName _taskData;
        if (_varName != "") then {
            _objectiveID = _varName;
        } else {
            _objectiveID = format ["%1_%2", typeOf _taskData, _taskData call BIS_fnc_netId];
        };
    }
    // If it's a string, use it directly
    else {
        if (_taskData isEqualType "") then {
            _objectiveID = _taskData;
        }
        // If it's a position, format it
        else {
            if (_taskData isEqualType []) then {
                _objectiveID = format ["pos_%1_%2", floor (_taskData select 0), floor (_taskData select 1)];
            };
        };
    };
};

// Default to task name if no objective ID found
if (_objectiveID isEqualTo "") then {
    _objectiveID = _taskName;
};

// Log the completion
["BATCOM", "DEBUG", format ["taskComplete: %1 by player %2 on %3", _taskName, _playerUID, _objectiveID]] call FUNC(logMessage);

// Call aoProgress with the mapped event type
// aoProgress will handle proximity detection automatically for high-value events
[_eventType, _playerUID, _objectiveID] call FUNC(aoProgress);
