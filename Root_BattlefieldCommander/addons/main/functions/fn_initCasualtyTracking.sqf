#include "..\script_component.hpp"
/*
 * Author: Root
 * Initialize casualty tracking system
 * Attaches event handlers to all units to track kills and attribute them
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * call Root_fnc_initCasualtyTracking
 */

if (!isServer) exitWith {};

// Initialize global casualty tracking namespace
if (isNil "BATCOM_casualties") then {
    BATCOM_casualties = createHashMap;
    BATCOM_casualties set ["events", []];
    BATCOM_casualties set ["player_kills", createHashMap];  // uid -> kill count
    BATCOM_casualties set ["group_kills", createHashMap];  // group_id -> kill count
};

// Function to record a casualty
BATCOM_fnc_recordCasualty = {
    params ["_victim", "_killer"];

    private _victimSide = side _victim;
    private _victimGroup = group _victim;
    private _victimGroupId = groupId _victimGroup;
    private _timestamp = time;
    private _position = getPosATL _victim;

    // Determine killer info
    private _killerId = "";
    private _killerSide = sideUnknown;
    private _weapon = "";

    if (!isNull _killer && {_killer != _victim}) then {
        _killerSide = side _killer;
        _weapon = currentWeapon _killer;

        if (isPlayer _killer) then {
            _killerId = getPlayerUID _killer;

            // Track player kills
            private _playerKills = BATCOM_casualties get "player_kills";
            private _currentKills = _playerKills getOrDefault [_killerId, 0];
            _playerKills set [_killerId, _currentKills + 1];
        } else {
            private _killerGroup = group _killer;
            _killerId = groupId _killerGroup;

            // Track group kills
            private _groupKills = BATCOM_casualties get "group_kills";
            private _currentKills = _groupKills getOrDefault [_killerId, 0];
            _groupKills set [_killerId, _currentKills + 1];
        };
    };

    // Find nearest objective if in AO
    private _nearestObj = "";
    private _minDist = 999999;
    {
        private _marker = _x;
        if (_marker select [0, 4] == "obj_" || {_marker select [0, 11] == "batcom_obj_"}) then {
            private _dist = _position distance2D (getMarkerPos _marker);
            if (_dist < _minDist) then {
                _minDist = _dist;
                _nearestObj = _marker;
            };
        };
    } forEach allMapMarkers;

    // Only record if within 300m of an objective
    if (_minDist < 300) then {
        // Record casualty event
        private _event = createHashMapFromArray [
            ["victim_id", _victimGroupId],
            ["victim_side", str _victimSide],
            ["killer_id", _killerId],
            ["killer_side", str _killerSide],
            ["timestamp", _timestamp],
            ["position", _position],
            ["weapon", _weapon],
            ["objective_id", _nearestObj]
        ];

        private _events = BATCOM_casualties get "events";
        _events pushBack _event;
    };
};

// Add event handler to all existing units
{
    {
        private _unit = _x;
        if (!(_unit getVariable ["batcom_casualty_tracking", false])) then {
            _unit addEventHandler ["Killed", {
                params ["_victim", "_killer"];
                [_victim, _killer] call BATCOM_fnc_recordCasualty;
            }];
            _unit setVariable ["batcom_casualty_tracking", true];
        };
    } forEach (units _x);
} forEach allGroups;

// Add event handler to future spawned units
if (isNil "BATCOM_casualty_init_eh") then {
    BATCOM_casualty_init_eh = addMissionEventHandler ["EntityCreated", {
        params ["_entity"];

        if (_entity isKindOf "CAManBase") then {
            [{
                params ["_unit"];
                if (!isNull _unit && {alive _unit} && {!(_unit getVariable ["batcom_casualty_tracking", false])}) then {
                    _unit addEventHandler ["Killed", {
                        params ["_victim", "_killer"];
                        [_victim, _killer] call BATCOM_fnc_recordCasualty;
                    }];
                    _unit setVariable ["batcom_casualty_tracking", true];
                };
            }, [_entity], 1] call CBA_fnc_waitAndExecute;
        };
    }];
};

["BATCOM", "INFO", "Casualty tracking system initialized"] call FUNC(logMessage);
