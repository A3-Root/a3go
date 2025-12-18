#include "..\script_component.hpp"
/*
 * Author: Root
 * Set AO boundary from a marker or trigger and send to BATCOM/Python.
 *
 * Arguments:
 * 0: Area reference <STRING|OBJECT> - marker name or trigger object
 *
 * Example:
 * ["AO_Area"] call Root_fnc_batcomSetAOBoundary;
 * [AO_Area] call Root_fnc_batcomSetAOBoundary; // if AO_Area is a trigger
 */

params [
    ["_areaRef", objNull, [objNull, ""]]
];

if (!isServer) exitWith {
    ["BATCOM", "ERROR", "batcomSetAOBoundary: Must be run on server"] call FUNC(logMessage);
    false
};

private _isMarker = _areaRef isEqualType "";
private _isTrigger = _areaRef isEqualType objNull && {!isNull _areaRef};

if (!_isMarker && !_isTrigger) exitWith {
    ["BATCOM", "ERROR", "batcomSetAOBoundary: Invalid area reference (expect marker name or trigger)"] call FUNC(logMessage);
    false
};

// Extract center, half-axes, angle, shape
private _center = [0,0,0];
private _halfX = 0;
private _halfY = 0;
private _angle = 0;

if (_isMarker) then {
    if (!(_areaRef in allMapMarkers)) exitWith {
        ["BATCOM", "ERROR", format ["batcomSetAOBoundary: Marker '%1' not found", _areaRef]] call FUNC(logMessage);
        false
    };
    _center = getMarkerPos _areaRef;
    private _size = getMarkerSize _areaRef;
    _halfX = _size select 0;
    _halfY = _size select 1;
    _angle = markerDir _areaRef;
} else {
    // Trigger
    _center = getPosATL _areaRef;
    private _ta = triggerArea _areaRef; // [a,b,angle,isRect]
    _halfX = _ta select 0;
    _halfY = _ta select 1;
    _angle = _ta select 2;
};

// Compute rotated corners to get an axis-aligned bounding box
private _corners = [
    [_halfX, _halfY],
    [-_halfX, _halfY],
    [-_halfX, -_halfY],
    [_halfX, -_halfY]
];
private _rad = _angle * (pi / 180);
private _cosA = cos _rad;
private _sinA = sin _rad;

private _worldCorners = _corners apply {
    _x params ["_cx", "_cy"];
    private _rx = _cx * _cosA - _cy * _sinA;
    private _ry = _cx * _sinA + _cy * _cosA;
    [
        (_center select 0) + _rx,
        (_center select 1) + _ry
    ]
};

private _xs = _worldCorners apply {_x select 0};
private _ys = _worldCorners apply {_x select 1};

private _minX = _xs param [0, 0];
private _maxX = _xs param [0, 0];
{
    if (_x < _minX) then {_minX = _x;};
    if (_x > _maxX) then {_maxX = _x;};
} forEach _xs;

private _minY = _ys param [0, 0];
private _maxY = _ys param [0, 0];
{
    if (_x < _minY) then {_minY = _x;};
    if (_x > _maxY) then {_maxY = _x;};
} forEach _ys;

private _aoBounds = createHashMapFromArray [
    ["min_x", _minX],
    ["max_x", _maxX],
    ["min_y", _minY],
    ["max_y", _maxY]
];

private _guardrails = createHashMapFromArray [
    ["ao_bounds", _aoBounds]
];

["BATCOM", "INFO", format ["batcomSetAOBoundary: AO bounds set (min_x=%1 max_x=%2 min_y=%3 max_y=%4)", _minX, _maxX, _minY, _maxY]] call FUNC(logMessage);

// Send to Python via admin handler
["commanderGuardrails", _guardrails, true] call FUNC(batcomInit);

true
