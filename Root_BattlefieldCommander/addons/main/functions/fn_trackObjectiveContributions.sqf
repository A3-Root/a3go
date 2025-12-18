#include "..\script_component.hpp"
/*
 * Author: Root
 * Track player contributions to objective capture/defense
 * Called periodically to update who is contributing to objectives
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * call Root_fnc_trackObjectiveContributions
 */

if (!isServer) exitWith {};

// Initialize contribution tracking
if (isNil "BATCOM_contributions") then {
    BATCOM_contributions = createHashMap;
};

private _allMarkers = allMapMarkers;
private _allPlayers = allPlayers;

{
    private _marker = _x;

    // Only process objective markers
    if !(_marker select [0, 4] == "obj_" || {_marker select [0, 11] == "batcom_obj_"}) then {continue};

    private _markerPos = getMarkerPos _marker;
    private _markerSize = getMarkerSize _marker;
    private _radius = (_markerSize select 0) max (_markerSize select 1);
    if (_radius < 50) then {_radius = 50};

    // Check all players in radius
    {
        private _player = _x;
        if (alive _player && {_player distance2D _markerPos < _radius}) then {
            private _uid = getPlayerUID _player;

            // Get or create player contribution record
            private _playerData = BATCOM_contributions getOrDefault [_uid, createHashMap];
            private _objContributions = _playerData getOrDefault ["objectives", []];

            // Track time in objective area
            if !(_marker in _objContributions) then {
                _objContributions pushBack _marker;
                _playerData set ["objectives", _objContributions];
                BATCOM_contributions set [_uid, _playerData];
            };

            // Update proximity timestamp
            private _proximityData = _playerData getOrDefault ["proximity", createHashMap];
            _proximityData set [_marker, time];
            _playerData set ["proximity", _proximityData];
        };
    } forEach _allPlayers;

} forEach _allMarkers;
