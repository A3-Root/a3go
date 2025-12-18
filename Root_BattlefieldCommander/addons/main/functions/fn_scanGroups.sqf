#include "..\script_component.hpp"
/*
 * Author: Root
 * Scan all AI groups with knowledge-based fog-of-war
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Array of group data hashmaps <ARRAY>
 *
 * Example:
 * _groups = call BATCOM_fnc_scanGroups;
 */

if (!isServer) exitWith {[]};

// Get controlled sides
private _controlledSides = GVAR(controlledSides);
if (count _controlledSides == 0) exitWith {
    ["BATCOM", "DEBUG", "scanGroups: No controlled sides configured"] call FUNC(logMessage);
    []
};

// Log controlled sides for debugging
private _controlledSidesDebug = _controlledSides apply {str _x};
["BATCOM", "DEBUG", format ["scanGroups: Controlled sides: %1", _controlledSidesDebug]] call FUNC(logMessage);

private _friendlySides = GVAR(friendlySides);
private _allGroups = allGroups;
private _groupsData = [];

// Collect friendly units for knowledge checks
private _friendlyUnits = [];
{
    private _side = _x;
    {
        if (side _x == _side) then {
            _friendlyUnits append (units _x);
        };
    } forEach _allGroups;
} forEach _controlledSides;

// Scan all groups
{
    private _group = _x;
    private _groupSide = side _group;

    // Skip empty groups
    if (units _group isEqualTo []) then {continue};

    

    // Get group info
    private _groupId = [_group] call FUNC(getGroupId);
    private _groupType = [_group] call FUNC(getGroupType);
    private _leader = leader _group;
    private _units = units _group;
    private _unitCount = count _units;

    // Check if this is a controlled group
    // Normalize sides to strings for comparison to handle resistance/independent
    private _groupSideStr = str _groupSide;
    private _controlledSidesStr = _controlledSides apply {str _x};
    private _isControlled = (_groupSideStr in _controlledSidesStr);
    if (!_isControlled) then {
        if (_groupId in GVAR(controlledGroupOverrides)) then {
            _isControlled = true;
        };
    };

    // Get position
    private _position = getPosATL _leader;

    // Behavior and combat state
    private _behaviour = behaviour _leader;
    private _combatMode = combatMode _group;
    private _speedMode = speedMode _group;
    private _formation = formation _group;

    // Check if any unit in group is a player
    private _isPlayerGroup = false;
    {
        if (isPlayer _x) then {
            _isPlayerGroup = true;
        };
    } forEach _units;

    // Check engagement status - if any unit is in combat
    private _inCombat = false;
    {
        private _unit = _x;
        if (behaviour _unit in ["COMBAT", "STEALTH"]) then {
            private _target = assignedTarget _unit;
            if (!isNull _target && {_unit knowsAbout _target > 0}) then {
                _inCombat = true;
            };
        };
    } forEach _units;

    // Get current waypoint information
    private _currentWPIndex = currentWaypoint _group;
    private _waypoints = waypoints _group;
    private _currentWP = objNull;
    private _currentWPType = "";
    private _currentWPPos = [];
    if (_currentWPIndex < count _waypoints) then {
        _currentWP = _waypoints select _currentWPIndex;
        _currentWPType = waypointType _currentWP;
        _currentWPPos = waypointPosition _currentWP;
    };

    // For controlled groups, gather full intel
    if (_isControlled) then {
        // Calculate casualties from initial strength
        private _initialStrength = _group getVariable ["batcom_initial_strength", _unitCount];
        if (_initialStrength == 0) then {
            _group setVariable ["batcom_initial_strength", _unitCount];
            _initialStrength = _unitCount;
        };
        private _casualties = _initialStrength - _unitCount;

        private _groupData = createHashMapFromArray [
            ["id", _groupId],
            ["side", str _groupSide],
            ["type", _groupType],
            ["position", _position],
            ["unit_count", _unitCount],
            ["casualties", _casualties],
            ["behaviour", _behaviour],
            ["combat_mode", _combatMode],
            ["speed_mode", _speedMode],
            ["formation", _formation],
            ["is_controlled", true],
            ["is_player_group", _isPlayerGroup],
            ["in_combat", _inCombat],
            ["current_waypoint_type", _currentWPType],
            ["current_waypoint_pos", _currentWPPos],
            ["known_enemies", []]
        ];

        // Known enemies omitted for token savings
        _groupsData pushBack _groupData;

    } else {
        // For non-controlled groups, report based on several criteria:
        // 1. Always report player groups
        // 2. Always report allied/friendly groups
        // 3. Report enemy groups if known to our forces (knowledge >= 1.5)

        private _isFriendly = _groupSide in _friendlySides;
        private _shouldReport = _isPlayerGroup || _isFriendly;

        // Check knowledge level for enemy groups
        private _maxKnowledge = 0;
        if (!_shouldReport) then {
            {
                private _knowledge = _x knowsAbout _leader;
                _maxKnowledge = _maxKnowledge max _knowledge;
            } forEach _friendlyUnits;
            _shouldReport = _maxKnowledge >= 1.5;
        };

        if (_shouldReport) then {
            private _groupData = createHashMapFromArray [
                ["id", _groupId],
                ["side", str _groupSide],
                ["type", _groupType],
                ["position", _position],
                ["unit_count", _unitCount],
                ["behaviour", _behaviour],
                ["combat_mode", _combatMode],
                ["formation", _formation],
                ["is_controlled", false],
                ["is_player_group", _isPlayerGroup],
                ["is_friendly", _isFriendly],
                ["in_combat", _inCombat],
                ["current_waypoint_type", _currentWPType],
                ["current_waypoint_pos", _currentWPPos],
                ["knowledge", _maxKnowledge]
            ];

            _groupsData pushBack _groupData;
        };
    };
} forEach _allGroups;

["BATCOM", "DEBUG", format ["scanGroups: Scanned %1 groups", count _groupsData]] call FUNC(logMessage);

_groupsData
