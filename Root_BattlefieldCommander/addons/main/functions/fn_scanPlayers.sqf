#include "..\script_component.hpp"
/*
 * Author: Root
 * Scan all player positions and states
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Array of player data hashmaps <ARRAY>
 *
 * Example:
 * _players = call BATCOM_fnc_scanPlayers;
 */

if (!isServer) exitWith {[]};

private _playersData = [];
private _allPlayers = allPlayers;

{
    private _player = _x;

    // Skip dead players
    if (!alive _player) then {continue};

    // Get player info
    private _name = name _player;
    private _uid = getPlayerUID _player;
    private _side = side _player;
    private _group = group _player;
    private _groupId = [_group] call FUNC(getGroupId);

    // Position and state
    private _position = getPosATL _player;
    private _vehicle = vehicle _player;
    private _isInVehicle = _vehicle != _player;
    private _vehicleType = "";
    if (_isInVehicle) then {
        _vehicleType = typeOf _vehicle;
    };

    // Combat state
    private _behaviour = behaviour _player;

    // Health state (simplified)
    private _damage = damage _player;

    // HVT status
    private _isHVT = _player getVariable ["batcom_hvt", false];
    private _hvtReason = _player getVariable ["batcom_hvt_reason", ""];
    private _threatScore = _player getVariable ["batcom_threat_score", 0.0];

    private _playerData = createHashMapFromArray [
        ["name", _name],
        ["uid", _uid],
        ["side", str _side],
        ["group_id", _groupId],
        ["position", _position],
        ["is_in_vehicle", _isInVehicle],
        ["vehicle_type", _vehicleType],
        ["behaviour", _behaviour],
        ["damage", _damage],
        ["is_hvt", _isHVT],
        ["hvt_reason", _hvtReason],
        ["threat_score", _threatScore]
    ];

    _playersData pushBack _playerData;
} forEach _allPlayers;

["BATCOM", "DEBUG", format ["scanPlayers: Scanned %1 players", count _playersData]] call FUNC(logMessage);

_playersData
