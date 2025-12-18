#include "..\script_component.hpp"
/*
 * Author: Root
 * Execute a spawn_squad command from Python
 *
 * Arguments:
 * 0: Command parameters <HASHMAP>
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * [_params] call BATCOM_fnc_applySpawnCommand;
 */

params [
    ["_cmdData", createHashMap, [createHashMap]]
];

if (!isServer) exitWith {false};

// Parse parameters
private _side = _cmdData getOrDefault ["side", ""];
private _unitClasses = _cmdData getOrDefault ["unit_classes", []];
private _position = _cmdData getOrDefault ["position", [0,0,0]];
private _objectiveId = _cmdData getOrDefault ["objective_id", ""];
private _forcedGroupId = _cmdData getOrDefault ["group_id", ""];

// Validate side
private _sideType = switch (_side) do {
    case "EAST": {east};
    case "WEST": {west};
    case "RESISTANCE": {resistance};
    case "INDEPENDENT": {resistance};
    default {
        ["BATCOM", "ERROR", format ["applySpawnCommand: Invalid side: %1", _side]] call FUNC(logMessage);
        sideUnknown
    };
};

if (_sideType == sideUnknown) exitWith {
    ["BATCOM", "ERROR", "applySpawnCommand: Failed to resolve side type"] call FUNC(logMessage);
    false
};

// Validate unit classes
if (_unitClasses isEqualTo []) exitWith {
    ["BATCOM", "ERROR", "applySpawnCommand: Empty unit_classes array"] call FUNC(logMessage);
    false
};

// Validate position
if (!(_position isEqualType [])) exitWith {
    ["BATCOM", "ERROR", format ["applySpawnCommand: Invalid position (not array): %1", _position]] call FUNC(logMessage);
    false
};

// Normalize position to [x,y,z] numbers (handle stringy inputs from Python)
_position = (_position + [0,0,0]) select [0,3];
_position = _position apply {
    if (_x isEqualType "") then {parseNumber _x} else {_x}
};

if ((count _position) != 3 || {(_position findIf {!( _x isEqualType 0) || {!finite _x}}) != -1}) exitWith {
    ["BATCOM", "ERROR", format ["applySpawnCommand: Invalid position elements: %1", _position]] call FUNC(logMessage);
    false
};

private _moveTargetPos = +_position;  // Treat requested position as the movement destination

// Classify the first unit so we can choose how to find a safe position
private _firstClass = _unitClasses select 0;
private _firstConfig = configFile >> "CfgVehicles" >> _firstClass;
private _simulation = toLower (getText (_firstConfig >> "simulation"));
private _isUav = getNumber (_firstConfig >> "isUav") == 1;
private _isHelicopterSim = _simulation in ["helicopterx", "helicopterrtd"];
private _isPlaneSim = _simulation in ["airplanex", "airplane"];
private _isGroundVehicle = _simulation in ["car", "carx", "tank", "tankx"];
private _isVehicle = _isUav || {_isHelicopterSim || _isPlaneSim || _isGroundVehicle || {_simulation isEqualTo "ship"}};
private _useFlatGroundCheck = (!_isVehicle) || _isGroundVehicle;

// Derive spawn seed position; vehicles start outside the AO (>=2km from center) then move in
private _aoBounds = GVAR(aoBounds);
private _aoCenter = [worldSize / 2, worldSize / 2, 0];
if (!isNil "_aoBounds" && {_aoBounds isEqualType createHashMap}) then {
    private _minX = _aoBounds getOrDefault ["min_x", (_aoCenter select 0)];
    private _maxX = _aoBounds getOrDefault ["max_x", (_aoCenter select 0)];
    private _minY = _aoBounds getOrDefault ["min_y", (_aoCenter select 1)];
    private _maxY = _aoBounds getOrDefault ["max_y", (_aoCenter select 1)];
    _aoCenter = [(_minX + _maxX) / 2, (_minY + _maxY) / 2, 0];
};

private _spawnSeedPos = +_position;
if (_isVehicle) then {
    private _dirX = (_moveTargetPos select 0) - (_aoCenter select 0);
    private _dirY = (_moveTargetPos select 1) - (_aoCenter select 1);
    private _dirMag = sqrt ((_dirX * _dirX) + (_dirY * _dirY));
    if (_dirMag < 1) then {
        private _randDir = random 360;
        _dirX = cos _randDir;
        _dirY = sin _randDir;
        _dirMag = 1;
    };
    private _spawnRadius = 2000 max _dirMag;
    _spawnSeedPos = [
        (_aoCenter select 0) + (_dirX / _dirMag * _spawnRadius),
        (_aoCenter select 1) + (_dirY / _dirMag * _spawnRadius),
        _position select 2
    ];

    private _mapSize = worldSize;
    if (!finite _mapSize || _mapSize <= 0) then {_mapSize = 51200;};
    _spawnSeedPos set [0, (_spawnSeedPos select 0) max 0 min _mapSize];
    _spawnSeedPos set [1, (_spawnSeedPos select 1) max 0 min _mapSize];
};

// Find safe spawn position
private _originalPos = _spawnSeedPos;
private _safePos = [-1, -1, -1];
private _foundSafePos = false;

if (_useFlatGroundCheck) then {
    // Try to clear a landing spot for infantry and ground vehicles first
    private _flatParams = [1, -1, 0.5, 1, 0, false, objNull];
    private _emptyPos = [];

    try {
        _emptyPos = _spawnSeedPos findEmptyPosition [0, 150];
        if (!(_emptyPos isEqualType [])) then {
            throw format ["findEmptyPosition returned %1", typeName _emptyPos];
        };
    } catch {
        ["BATCOM", "ERROR", format ["applySpawnCommand: findEmptyPosition failed for %1: %2", _spawnSeedPos, _exception]] call FUNC(logMessage);
    };

    if (_emptyPos isEqualTo []) then {
        ["BATCOM", "WARN", format ["applySpawnCommand: findEmptyPosition returned no result near %1 for %2", _spawnSeedPos, _firstClass]] call FUNC(logMessage);
    } else {
        private _flatCheck = +_flatParams;
        _flatCheck set [0, -1];

        try {
            _safePos = _emptyPos isFlatEmpty _flatCheck;
            if (!(_safePos isEqualType [])) then {
                throw format ["isFlatEmpty returned %1", typeName _safePos];
            };
        } catch {
            ["BATCOM", "ERROR", format ["applySpawnCommand: isFlatEmpty failed at %1: %2", _emptyPos, _exception]] call FUNC(logMessage);
            _safePos = [-1, -1, -1];
        };

        if (_safePos isEqualType [] && {count _safePos >= 2 && {(_safePos select 0) >= 0 && (_safePos select 1) >= 0}}) then {
            _foundSafePos = true;
        } else {
            _safePos = [-1, -1, -1];
        };
    };
};

// Fallback to BIS_fnc_findSafePos for anything still missing a valid position
if (!_foundSafePos) then {
    try {
        _safePos = [_spawnSeedPos, 0, 300, 10, 0, 5, 0, [], [_spawnSeedPos]] call BIS_fnc_findSafePos;
        if (!(_safePos isEqualType [])) then {
            throw format ["BIS_fnc_findSafePos returned %1", typeName _safePos];
        };
        if (_safePos isEqualType [] && {count _safePos >= 2 && {(_safePos select 0) >= 0 && (_safePos select 1) >= 0 && (_safePos isNotEqualTo [0, 0, 0])}}) then {
            _foundSafePos = true;
        };
    } catch {
        ["BATCOM", "ERROR", format ["applySpawnCommand: BIS_fnc_findSafePos failed for %1: %2", _spawnSeedPos, _exception]] call FUNC(logMessage);
    };
};

// No safe position found, use original position but log warning
if (!_foundSafePos) then {
    ["BATCOM", "WARN", format ["applySpawnCommand: Could not find safe position near %1, using original position", _originalPos]] call FUNC(logMessage);
    _safePos = [_spawnSeedPos select 0, _spawnSeedPos select 1, _spawnSeedPos param [2, 0]];
};

// Update position with safe coordinates (preserve Z for now)
// Ensure all position elements are numbers
private _posX = _safePos select 0;
private _posY = _safePos select 1;
private _posZ = if ((count _safePos) > 2) then {_safePos select 2} else {_spawnSeedPos param [2, 0]};

// Convert to numbers if needed
if (_posX isEqualType "") then {_posX = parseNumber _posX};
if (_posY isEqualType "") then {_posY = parseNumber _posY};
if (_posZ isEqualType "") then {_posZ = parseNumber _posZ};

// Validate they are numbers
if (!(_posX isEqualType 0) || !finite _posX) then {_posX = 0};
if (!(_posY isEqualType 0) || !finite _posY) then {_posY = 0};
if (!(_posZ isEqualType 0) || !finite _posZ) then {_posZ = 0};

if (_useFlatGroundCheck) then {
    _posZ = getTerrainHeightASL [_posX, _posY];
};

_position = [_posX, _posY, _posZ];
private _spawnPosATL = _position;
if (_useFlatGroundCheck && {count _safePos >= 3}) then {
    _spawnPosATL = ASLToATL _position;
    _position = _spawnPosATL;
};

["BATCOM", "DEBUG", format ["applySpawnCommand: Position adjusted: %1 -> %2 (types: %3, %4, %5)",
    _originalPos, _position, typeName _posX, typeName _posY, typeName _posZ]] call FUNC(logMessage);

// Create group
private _group = createGroup [_sideType, true];

if (isNull _group) exitWith {
    ["BATCOM", "ERROR", format ["applySpawnCommand: Failed to create group for side %1", _side]] call FUNC(logMessage);
    false
};

// Get appropriate spawn altitude if spawning vehicles
private _spawnAltitude = 0;
if (_isVehicle) then {
    _spawnAltitude = [_firstClass] call FUNC(getSpawnAltitude);

    // Override Z coordinate with calculated altitude
    if (_spawnAltitude > 0) then {
        _position set [2, _spawnAltitude];
        ["BATCOM", "INFO", format ["applySpawnCommand: Adjusted spawn altitude for %1 to %2m ATL", _firstClass, _spawnAltitude]] call FUNC(logMessage);
    } else {
        // Ground vehicles: ensure Z is on terrain
        _position set [2, 0 max (_position select 2)];
    };
};

// Spawn units
private _spawnedUnits = [];
private _vehicle = objNull;

{
    private _unitClass = _x;

    // First unit might be a vehicle
    if (_forEachIndex == 0 && _isVehicle) then {
        // Create vehicle
        if ((_position isEqualType [] && {count _position == 3})) then {
            private _placement = ["CAN_COLLIDE", "FLY"] select (_spawnAltitude > 0);
            _vehicle = createVehicle [_unitClass, _position, [], 0, _placement];
        } else {
            ["BATCOM", "ERROR", format ["applySpawnCommand: Invalid vehicle spawn position: %1", _position]] call FUNC(logMessage);
        };

        if (isNull _vehicle) then {
            ["BATCOM", "ERROR", format ["applySpawnCommand: Failed to create vehicle: %1", _unitClass]] call FUNC(logMessage);
        } else {
            // Set position with proper altitude
            if (_spawnAltitude > 0) then {
                _vehicle setPosATL _position;
                // Give a slight forward nudge to avoid immediate stall for airframes
                _vehicle setVelocityModelSpace [0, 5, 0];
            } else {
                _vehicle setVehiclePosition [_spawnPosATL, [], 0, "NONE"];
            };

            // Create crew for the vehicle
            createVehicleCrew _vehicle;

            // Add vehicle and crew to group
            private _crew = crew _vehicle;
            {
                [_x] joinSilent _group;
                _spawnedUnits pushBack _x;
            } forEach _crew;

            ["BATCOM", "INFO", format ["applySpawnCommand: Created vehicle %1 with %2 crew", _unitClass, count _crew]] call FUNC(logMessage);
        };
    } else {
        // Regular infantry unit or vehicle passenger
        private _unit = objNull;
        if ((_position isEqualType [] && {count _position == 3})) then {
            ["BATCOM", "DEBUG", format ["applySpawnCommand: Creating unit %1 at position %2 (pos types: %3)",
                _unitClass, _position, _position apply {typeName _x}]] call FUNC(logMessage);
            _unit = _group createUnit [_unitClass, _position, [], 0, "FORM"];
        } else {
            ["BATCOM", "ERROR", format ["applySpawnCommand: Invalid infantry spawn position: %1", _position]] call FUNC(logMessage);
        };

        if (isNull _unit) then {
            ["BATCOM", "WARN", format ["applySpawnCommand: Failed to create unit class: %1", _unitClass]] call FUNC(logMessage);
        } else {
            _spawnedUnits pushBack _unit;

            // If there's a vehicle, put passengers inside
            if (!isNull _vehicle && {_forEachIndex > 0}) then {
                _unit moveInCargo _vehicle;
            };
        };
    };
} forEach _unitClasses;

if (_isVehicle && {_spawnedUnits isNotEqualTo []}) then {
    private _wp = _group addWaypoint [_moveTargetPos, 0];
    _wp setWaypointType "MOVE";
    _wp setWaypointCompletionRadius 25;
    ["BATCOM", "DEBUG", format ["applySpawnCommand: Issued move waypoint for %1 toward %2", _firstClass, _moveTargetPos]] call FUNC(logMessage);
};

// Default posture: keep spawned units aware unless combat is triggered later
_group setBehaviour "AWARE";
_group setCombatMode "YELLOW";
{
    _x setBehaviour "AWARE";
    _x setCombatMode "YELLOW";
} forEach _spawnedUnits;

// Check if any units were spawned
if (_spawnedUnits isEqualTo []) exitWith {
    ["BATCOM", "ERROR", "applySpawnCommand: No units were spawned, deleting group"] call FUNC(logMessage);
    deleteGroup _group;
    false
};

// Tag group for tracking (respect caller-provided ID so follow-on orders can resolve)
private _groupId = _forcedGroupId;
if (_groupId isEqualTo "") then {
    _groupId = [_group] call FUNC(getGroupId);
} else {
    _group setVariable [QGVAR(groupId), _groupId, true];
};
_group setVariable [QGVAR(spawnedByCommander), true, true];
_group setVariable [QGVAR(originalSize), count _spawnedUnits];

// Set objective ID if provided
if (_objectiveId != "") then {
    _group setVariable [QGVAR(objectiveId), _objectiveId, true];
};

["BATCOM", "INFO", format ["applySpawnCommand: Spawned %1 units (%2) at %3 -> Group %4",
    count _spawnedUnits,
    _side,
    _position,
    _groupId
]] call FUNC(logMessage);

true
