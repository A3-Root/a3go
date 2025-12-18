#include "..\script_component.hpp"
/*
 * Author: Root
 * Track and report AO objectives to BATCOM
 *
 * This function:
 * 1. Scans all AO objectives (HQ, Radio Tower, GPS Jammer, Supply Depot, AA, HVT, etc.)
 * 2. Reports objective status to BATCOM
 * 3. Tracks objective state changes
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * call Root_fnc_trackAOObjectives;
 */

if (!isServer) exitWith {};
if (!BATCOM_currentAOActive) exitWith {};

private _aoPos = missionNamespace getVariable ["QS_AOpos", [0,0,0]];
private _objectives = [];

// ========== HQ / Commander Objective ==========
private _hqPos = missionNamespace getVariable ["QS_HQpos", []];
if (count _hqPos >= 2) then {
    private _commanderAlive = missionNamespace getVariable ["QS_commanderAlive", false];
    private _commander = missionNamespace getVariable ["QS_csatCommander", objNull];
    private _commanderSurrendered = if (isNull _commander) then {
        false
    } else {
        _commander getVariable ["QS_isSurrendered", false]
    };

    private _objId = "OBJ_HQ";
    private _state = if (_commanderSurrendered) then {"captured"} else {
        ["destroyed", "active"] select (_commanderAlive)
    };

    // Check if state changed
    private _lastState = BATCOM_objectivesTracked getOrDefault [_objId, ""];
    if (_lastState != _state) then {
        BATCOM_objectivesTracked set [_objId, _state];

        // Report to BATCOM
        private _params = createHashMapFromArray [
            ["description", format ["Defend HQ and Commander at %1", _hqPos]],
            ["priority", 100], // HQ is highest priority
            ["position", _hqPos + [0]], // Add Z coordinate
            ["radius", 150],
            ["metadata", createHashMapFromArray [
                ["task_type", "defend_hq"],
                ["objective_name", "HQ"],
                ["ao_linked", true],
                ["state", _state]
            ]]
        ];

        ["commanderTask", _params, false] call Root_fnc_batcomInit;
    };
};

// ========== Radio Tower Objective ==========
private _radioTower = missionNamespace getVariable ["QS_radioTower", objNull];
if (!isNull _radioTower) then {
    private _radioTowerPos = missionNamespace getVariable ["QS_radioTower_pos", []];
    private _radioTowerAlive = missionNamespace getVariable ["radioTowerAlive", true];

    private _objId = "OBJ_RADIOTOWER";
    private _state = ["destroyed", "active"] select (_radioTowerAlive);

    private _lastState = BATCOM_objectivesTracked getOrDefault [_objId, ""];
    if (_lastState != _state) then {
        BATCOM_objectivesTracked set [_objId, _state];

        private _params = createHashMapFromArray [
            ["description", format ["Defend Radio Tower at %1", _radioTowerPos]],
            ["priority", 80], // High priority - force multiplier
            ["position", _radioTowerPos + [0]],
            ["radius", 100],
            ["metadata", createHashMapFromArray [
                ["task_type", "defend_radiotower"],
                ["objective_name", "Radio Tower"],
                ["ao_linked", true],
                ["state", _state]
            ]]
        ];

        ["commanderTask", _params, false] call Root_fnc_batcomInit;
    };
};

// ========== GPS Jammer Objectives ==========
private _jammers = missionNamespace getVariable ["QS_mission_gpsJammers", []];
{
    _x params ["_id", "_spawnPos", "_effectPos", "_radius", "_jammer", "_assocObjects"];

    if (!isNull _jammer && {alive _jammer}) then {
        private _objId = format ["OBJ_JAMMER_%1", _forEachIndex];
        private _state = "active";

        private _lastState = BATCOM_objectivesTracked getOrDefault [_objId, ""];
        if (_lastState != _state) then {
            BATCOM_objectivesTracked set [_objId, _state];

            private _params = createHashMapFromArray [
                ["description", format ["Defend GPS Jammer at %1", _effectPos]],
                ["priority", 70], // High priority
                ["position", _effectPos + [0]],
                ["radius", 75],
                ["metadata", createHashMapFromArray [
                    ["task_type", "defend_gps_jammer"],
                    ["objective_name", format ["GPS Jammer %1", _forEachIndex + 1]],
                    ["ao_linked", true],
                    ["state", _state],
                    ["jammerObject", netId _jammer]
                ]]
            ];

            ["commanderTask", _params, false] call Root_fnc_batcomInit;
        };
    };
} forEach _jammers;

// ========== Supply Depot Objective ==========
private _supplyDepotActive = missionNamespace getVariable ["QS_subObjective_supplyDepot_active", false];
if (_supplyDepotActive) then {
    private _supplyDepotObj = missionNamespace getVariable ["QS_subObjective_supplyDepot_obj", objNull];

    if (!isNull _supplyDepotObj) then {
        private _depotPos = getPosATL _supplyDepotObj;
        private _objId = "OBJ_SUPPLY_DEPOT";
        private _state = "active";

        private _lastState = BATCOM_objectivesTracked getOrDefault [_objId, ""];
        if (_lastState != _state) then {
            BATCOM_objectivesTracked set [_objId, _state];

            private _params = createHashMapFromArray [
                ["description", format ["Defend Supply Depot at %1", _depotPos]],
                ["priority", 60], // Medium priority
                ["position", _depotPos],
                ["radius", 100],
                ["metadata", createHashMapFromArray [
                    ["task_type", "defend_supply_depot"],
                    ["objective_name", "Supply Depot"],
                    ["ao_linked", true],
                    ["state", _state]
                ]]
            ];

            ["commanderTask", _params, false] call Root_fnc_batcomInit;
        };
    };
};

// ========== AA Site Objectives ==========
private _aaVehicles = vehicles select {(alive _x) && (_x getVariable ["McD_AO_AA", false])};
if (_aaVehicles isNotEqualTo []) then {
    {
        private _aaVehicle = _x;
        private _aaPos = getPosATL _aaVehicle;
        private _objId = format ["OBJ_AA_%1", netId _aaVehicle];
        private _state = "active";

        private _lastState = BATCOM_objectivesTracked getOrDefault [_objId, ""];
        if (_lastState != _state) then {
            BATCOM_objectivesTracked set [_objId, _state];

            private _params = createHashMapFromArray [
                ["description", format ["Defend AA Site at %1", _aaPos]],
                ["priority", 50], // Lower priority
                ["position", _aaPos],
                ["radius", 75],
                ["metadata", createHashMapFromArray [
                    ["task_type", "defend_aa_site"],
                    ["objective_name", format ["AA Site %1", _forEachIndex + 1]],
                    ["ao_linked", true],
                    ["state", _state],
                    ["vehicleNetId", netId _aaVehicle]
                ]]
            ];

            ["commanderTask", _params, false] call Root_fnc_batcomInit;
        };
    } forEach _aaVehicles;
};

// ========== HVT (Arrest Target) Objective ==========
private _arrestTarget = missionNamespace getVariable ["QS_arrest_target", objNull];
if (!isNull _arrestTarget && {alive _arrestTarget}) then {
    private _hvtPos = getPosATL _arrestTarget;
    private _hvtArrested = missionNamespace getVariable ["QS_aoSmallTask_Arrested", false];

    private _objId = "OBJ_HVT";
    private _state = ["active", "captured"] select (_hvtArrested);

    private _lastState = BATCOM_objectivesTracked getOrDefault [_objId, ""];
    if (_lastState != _state) then {
        BATCOM_objectivesTracked set [_objId, _state];

        private _params = createHashMapFromArray [
            ["description", format ["Defend/Eliminate HVT at %1", _hvtPos]],
            ["priority", 75], // High priority
            ["position", _hvtPos],
            ["radius", 50],
            ["metadata", createHashMapFromArray [
                ["task_type", "defend_hvt"],
                ["objective_name", "HVT"],
                ["ao_linked", true],
                ["state", _state],
                ["hvtNetId", netId _arrestTarget]
            ]]
        ];

        ["commanderTask", _params, false] call Root_fnc_batcomInit;
    };
};

// Log tracked objectives count
private _activeCount = 0;
{
    if (_y == "active") then {_activeCount = _activeCount + 1;};
} forEach BATCOM_objectivesTracked;

if (_activeCount > 0) then {
    ["BATCOM", "DEBUG", format ["Tracking %1 active objectives", _activeCount]] call FUNC(logMessage);
};

private _sideMissionMarker = "QS_marker_sideMarker";
private _sideMissionActive = (markerAlpha _sideMissionMarker > 0);

if (_sideMissionActive) then {
    private _smPos = markerPos _sideMissionMarker;
    private _smText = markerText _sideMissionMarker;
    private _smSuccess = missionNamespace getVariable ["QS_smSuccess", false];

    // Parse mission type from marker text
    private _taskType = "defend_side_mission";
    private _priority = 85;
    private _radius = 200;

    if ((_smText find "Artillery") >= 0) then {
        _taskType = "defend_priority_artillery";
        _priority = 95;
        _radius = 250;
    } else {
        if ((_smText find "Anti-Air") >= 0 || (_smText find "AA") >= 0) then {
            _taskType = "defend_priority_aa";
            _priority = 90;
            _radius = 200;
        } else {
            if ((_smText find "Regenerator") >= 0) then {
                _taskType = "defend_regenerator";
                _priority = 90;
                _radius = 150;
            } else {
                if ((_smText find "Doomsday") >= 0) then {
                    _taskType = "defend_doomsday";
                    _priority = 95;
                    _radius = 300;
                };
            };
        };
    };

    private _objId = format ["OBJ_SIDEMISSION_%1", _taskType];
    private _state = ["active", "completed"] select _smSuccess;

    private _lastState = BATCOM_objectivesTracked getOrDefault [_objId, ""];
    if (_lastState != _state) then {
        BATCOM_objectivesTracked set [_objId, _state];

        // Check overlap with main AO
        private _aoPos = missionNamespace getVariable ["QS_AOpos", [0,0,0]];
        private _aoRadius = missionNamespace getVariable ["QS_AO_radius", 500];
        private _distToAO = _smPos distance2D _aoPos;
        private _overlaps = (_distToAO < (_aoRadius + _radius));

        private _params = createHashMapFromArray [
            ["description", format ["%1 at %2", _smText, _smPos]],
            ["priority", _priority],
            ["position", _smPos + [0]],
            ["radius", _radius],
            ["metadata", createHashMapFromArray [
                ["task_type", _taskType],
                ["objective_name", _smText],
                ["side_mission", true],
                ["state", _state],
                ["overlaps_main_ao", _overlaps],
                ["distance_to_ao", round _distToAO]
            ]]
        ];

        ["commanderTask", _params, false] call Root_fnc_batcomInit;

        ["BATCOM", "INFO", format ["Side mission %1: %2 (pri %3, overlap=%4)",
            _state, _taskType, _priority, _overlaps]] call FUNC(logMessage);
    };
};

private _defendActive = missionNamespace getVariable ["QS_defendActive", false];

if (_defendActive) then {
    private _hqPos = missionNamespace getVariable ["QS_HQpos", []];

    if (count _hqPos >= 2) then {
        private _objId = "OBJ_COUNTERATTACK";
        private _state = "active";

        private _lastState = BATCOM_objectivesTracked getOrDefault [_objId, ""];
        if (_lastState != _state) then {
            BATCOM_objectivesTracked set [_objId, _state];

            private _params = createHashMapFromArray [
                ["description", format ["ASSAULT AND RETAKE THE LOST HQ at %1", _hqPos]],
                ["priority", 100],
                ["position", _hqPos + [0]],
                ["radius", 300],
                ["metadata", createHashMapFromArray [
                    ["task_type", "defend_counterattack"],
                    ["objective_name", "HQ Defense"],
                    ["state", _state],
                    ["defense_phase", true]
                ]]
            ];

            ["commanderTask", _params, false] call Root_fnc_batcomInit;

            ["BATCOM", "CRITICAL", "AO Defense Phase triggered: Assault and retake HQ!"] call FUNC(logMessage);
        };
    };
};
