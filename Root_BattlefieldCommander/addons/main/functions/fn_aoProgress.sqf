#include "..\script_component.hpp"
/*
 * Author: Root
 * Report objective completion progress to BATCOM effectiveness tracker
 *
 * Arguments:
 * 0: Event Type <STRING> - Type of completion event
 * 1: Player UID <STRING> - UID of player who completed the objective
 * 2: Objective ID <STRING> (Optional) - ID of the objective, defaults to event type
 * 3: Objective Type <STRING> (Optional) - task_type, auto-inferred if not provided
 * 4: Completion Method <STRING> (Optional) - How it was completed, auto-inferred if not provided
 * 5: Nearby Players <ARRAY> (Optional) - Array of nearby player objects for proximity bonuses
 * 6: Proximity Radius <NUMBER> (Optional) - Radius in meters to search for nearby players, default 50m
 *
 * Event Types:
 * - "commanderKilled" - HQ commander killed (+30 pts)
 * - "commanderCaptured" - HQ commander captured alive (+40 pts, higher than kill!)
 * - "hvtEliminated" - HVT killed (+25 pts)
 * - "hvtCaptured" - HVT captured alive (+35 pts, higher than kill!)
 * - "radioTowerDestroyed" - Radio tower destroyed (+20 pts)
 * - "radioTowerNeutralized" - Radio tower disabled (+20 pts)
 * - "gpsJammerDestroyed" - GPS jammer destroyed (+20 pts)
 * - "gpsJammerDisabled" - GPS jammer disabled by engineer (+20 pts)
 * - "supplyDepotCaptured" - Supply depot captured (+15 pts)
 * - "mortarPitNeutralized" - Mortar pit neutralized (+5 pts proximity only)
 * - "aaSiteDestroyed" - AA site destroyed (+5 pts proximity only)
 * - "hmgTowerNeutralized" - HMG tower neutralized (+5 pts proximity only)
 *
 * Proximity Bonuses:
 * - For HQ commander and HVT captures/kills, nearby players (within radius) get +10 pts each
 * - Nearby players are automatically detected if position is available
 *
 * Return Value:
 * Success <BOOL>
 *
 * Examples:
 * ["commanderKilled", getPlayerUID _killer] call BATCOM_fnc_aoProgress;
 * ["commanderCaptured", getPlayerUID _capturer, "hq_main"] call BATCOM_fnc_aoProgress;
 * ["hvtCaptured", getPlayerUID _capturer, "hvt_alpha_1"] call BATCOM_fnc_aoProgress;
 * ["radioTowerDestroyed", getPlayerUID _player, "obj_radiotower_1", "defend_radiotower", "destroyed"] call BATCOM_fnc_aoProgress;
 * ["supplyDepotCaptured", getPlayerUID (leader _capturingGroup)] call BATCOM_fnc_aoProgress;
 *
 * // With custom proximity radius
 * ["commanderCaptured", getPlayerUID _capturer, "hq_main", "", "", [], 100] call BATCOM_fnc_aoProgress;
 */

params [
    ["_eventType", "", [""]],
    ["_playerUID", "", [""]],
    ["_objectiveID", "", [""]],
    ["_objectiveType", "", [""]],
    ["_completionMethod", "", [""]],
    ["_nearbyPlayers", [], [[]]],
    ["_proximityRadius", 50, [0]]
];

if (!isServer) exitWith {
    ["BATCOM", "ERROR", "aoProgress: Must be executed on server"] call FUNC(logMessage);
    false
};

if (!(call FUNC(isEnabled))) exitWith {
    ["BATCOM", "WARN", "aoProgress: BATCOM is not enabled"] call FUNC(logMessage);
    false
};

if (_eventType isEqualTo "" || _playerUID isEqualTo "") exitWith {
    ["BATCOM", "ERROR", "aoProgress: eventType and playerUID are required"] call FUNC(logMessage);
    false
};

// Find the player who completed it to get position for proximity search
private _completingPlayer = objNull;
{
    if (getPlayerUID _x == _playerUID) exitWith {
        _completingPlayer = _x;
    };
} forEach allPlayers;

// Auto-detect nearby players if not provided and this is a high-value event
private _isHighValueEvent = (_eventType in ["commanderKilled", "commanderCaptured", "hvtEliminated", "hvtCaptured"]);
if (_isHighValueEvent && {_nearbyPlayers isEqualTo []} && {!isNull _completingPlayer}) then {
    private _eventPos = getPosATL _completingPlayer;
    {
        if (alive _x && {_x != _completingPlayer} && {_x distance2D _eventPos < _proximityRadius}) then {
            _nearbyPlayers pushBack _x;
        };
    } forEach allPlayers;
};

// Format nearby players as [[uid, name, group_id], ...]
private _nearbyPlayersData = [];
{
    if (isPlayer _x && alive _x) then {
        private _uid = getPlayerUID _x;
        private _name = name _x;
        private _groupId = [group _x] call FUNC(getGroupId);
        _nearbyPlayersData pushBack [_uid, _name, _groupId];
    };
} forEach _nearbyPlayers;

// Build params array based on what was provided
private _params = [_eventType, _playerUID];
if (_objectiveID != "") then {
    _params pushBack _objectiveID;
    if (_objectiveType != "") then {
        _params pushBack _objectiveType;
        if (_completionMethod != "") then {
            _params pushBack _completionMethod;
        };
    };
};

// Add nearby players data if any
if (_nearbyPlayersData isNotEqualTo []) then {
    // Ensure we have at least 5 elements before adding 6th
    while {count _params < 5} do {
        _params pushBack "";
    };
    _params pushBack _nearbyPlayersData;
};

// Call Python API
private _result = ["batcom.batcom_init", ["aoProgress", _params, false]] call FUNC(pythiaCall);

if (isNil "_result") exitWith {
    ["BATCOM", "ERROR", format ["aoProgress: Failed to record event: %1", _eventType]] call FUNC(logMessage);
    false
};

// Parse result
private _resultHash = if (_result isEqualType []) then {
    [_result] call FUNC(arrayToHashmap)
} else {
    createHashMap
};

private _status = _resultHash getOrDefault ["status", "error"];
if (_status isEqualTo "ok") then {
    private _message = _resultHash getOrDefault ["message", "Progress recorded"];
    ["BATCOM", "INFO", format ["aoProgress: %1", _message]] call FUNC(logMessage);
    true
} else {
    private _error = _resultHash getOrDefault ["error", "Unknown error"];
    ["BATCOM", "ERROR", format ["aoProgress: %1", _error]] call FUNC(logMessage);
    false
};
