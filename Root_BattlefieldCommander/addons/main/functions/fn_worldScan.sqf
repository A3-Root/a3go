#include "..\script_component.hpp"
/*
 * Author: Root
 * Collect a complete world state snapshot
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Hashmap with world state data <HASHMAP>
 *
 * Example:
 * _snapshot = call BATCOM_fnc_worldScan;
 */

if (!isServer) exitWith {createHashMap};

if (!(call FUNC(isEnabled))) exitWith {
    ["BATCOM", "WARN", "worldScan: BATCOM is not enabled"] call FUNC(logMessage);
    createHashMap
};

["BATCOM", "DEBUG", "worldScan: Starting world scan"] call FUNC(logMessage);

// Collect all data
private _groups = call FUNC(scanGroups);
private _players = call FUNC(scanPlayers);
private _objectives = call FUNC(scanObjectives);

// Environment data
private _missionTime = time;
private _dayTime = dayTime;
private _isNight = sunOrMoon <= 0.5;
private _weather = [
    overcast,
    rain,
    fog,
    wind
];

// Map and mission identification
private _worldName = worldName;  // e.g., "Altis", "Tanoa", "VR"
private _missionName = missionName;  // e.g., "apex_jsoc_mission.Altis"

// Calculate AI deployment by side
private _aiDeployment = createHashMap;
{
    private _group = _x;
    if (units _group isNotEqualTo []) then {
        private _groupSide = str (side _group);
        private _unitCount = count (units _group);
        private _currentCount = _aiDeployment getOrDefault [_groupSide, 0];
        _aiDeployment set [_groupSide, _currentCount + _unitCount];
    };
} forEach allGroups;

// Mission state variables
private _missionVariables = createHashMap;

// Scan for BATCOM-tracked variables (starting with BATCOM_missionIntel_)
{
    private _varName = _x;
    if (_varName select [0, 19] == "BATCOM_missionIntel") then {
        private _value = missionNamespace getVariable [_varName, nil];
        if (!isNil "_value") then {
            _missionVariables set [_varName, _value];
        };
    };
} forEach allVariables missionNamespace;

// Get casualty and contribution data (if tracking is active)
private _casualtyData = createHashMap;
if (!isNil "BATCOM_casualties") then {
    _casualtyData = BATCOM_casualties;
};

private _contributionData = createHashMap;
if (!isNil "BATCOM_contributions") then {
    _contributionData = BATCOM_contributions;
};

// Build snapshot
// Normalize sides to strings for Python
private _friendlySides = GVAR(friendlySides) apply {str _x};
private _controlledSides = GVAR(controlledSides) apply {str _x};

private _snapshot = createHashMapFromArray [
    ["timestamp", _missionTime],
    ["mission_time", _missionTime],
    ["daytime", _dayTime],
    ["is_night", _isNight],
    ["weather", _weather],
    ["world_name", _worldName],
    ["mission_name", _missionName],
    ["ai_deployment", _aiDeployment],
    ["groups", _groups],
    ["players", _players],
    ["objectives", _objectives],
    ["mission_variables", _missionVariables],
    ["mission_intent", GVAR(missionIntent)],
    ["friendly_sides", _friendlySides],
    ["controlled_sides", _controlledSides],
    ["casualty_data", _casualtyData],
    ["contribution_data", _contributionData]
];

["BATCOM", "DEBUG", format ["worldScan: Complete - %1 groups, %2 players, %3 objectives",
    count _groups, count _players, count _objectives]] call FUNC(logMessage);

_snapshot
