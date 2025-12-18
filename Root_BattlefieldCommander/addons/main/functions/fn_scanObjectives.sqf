#include "..\script_component.hpp"
/*
 * Author: Root
 * Scan objective markers and zones
 *
 * Objectives are identified by markers starting with "obj_" or "batcom_obj_"
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Array of objective data hashmaps <ARRAY>
 *
 * Example:
 * _objectives = call BATCOM_fnc_scanObjectives;
 */

if (!isServer) exitWith {[]};

private _objectivesData = [];
private _allMarkers = allMapMarkers;

{
    private _marker = _x;

    // Only process objective markers
    if !(_marker select [0, 4] == "obj_" || {_marker select [0, 11] == "batcom_obj_"}) then {continue};

    // Get marker info
    private _markerPos = getMarkerPos _marker;
    private _markerSize = getMarkerSize _marker;
    private _markerShape = markerShape _marker;
    private _markerType = markerType _marker;
    private _markerText = markerText _marker;
    private _markerColor = markerColor _marker;

    // Calculate radius (use max of x/y for ellipse)
    private _radius = (_markerSize select 0) max (_markerSize select 1);
    if (_radius < 50) then {_radius = 50};  // Minimum radius

    // Count units in area
    private _nearUnits = _markerPos nearEntities [["Man", "LandVehicle", "Air", "Ship"], _radius];
    private _friendlyCount = 0;
    private _enemyCount = 0;
    private _controlledSides = GVAR(controlledSides);

    {
        private _unit = _x;
        private _unitSide = side _unit;

        if (_unitSide in _controlledSides) then {
            _friendlyCount = _friendlyCount + 1;
        } else {
            _enemyCount = _enemyCount + 1;
        };
    } forEach _nearUnits;

    private _objectiveData = createHashMapFromArray [
        ["id", _marker],
        ["position", _markerPos],
        ["radius", _radius],
        ["shape", _markerShape],
        ["type", _markerType],
        ["text", _markerText],
        ["color", _markerColor],
        ["friendly_count", _friendlyCount],
        ["enemy_count", _enemyCount]
    ];

    _objectivesData pushBack _objectiveData;
} forEach _allMarkers;

["BATCOM", "DEBUG", format ["scanObjectives: Scanned %1 objectives", count _objectivesData]] call FUNC(logMessage);

_objectivesData
