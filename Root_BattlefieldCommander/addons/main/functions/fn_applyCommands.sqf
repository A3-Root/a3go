#include "..\script_component.hpp"
/*
 * Author: Root
 * Process and apply a batch of commands from Python
 *
 * Arguments:
 * 0: Commands array <ARRAY> of hashmaps with:
 *    - group_id: Group ID string
 *    - type: Command type ("move_to", "defend_area", "patrol_route", "seek_and_destroy")
 *    - params: Command parameters hashmap
 *
 * Return Value:
 * Execution summary hashmap <HASHMAP>
 *
 * Example:
 * [_commands] call BATCOM_fnc_applyCommands;
 */

params [
    ["_commands", [], [[]]]
];

if (!isServer) exitWith {createHashMap};

if (_commands isEqualTo []) exitWith {
    createHashMapFromArray [
        ["executed", 0],
        ["failed", 0],
        ["errors", []]
    ]
};

// Check max commands per tick
private _maxCommands = 15;  // From CfgBATCOM
if (count _commands > _maxCommands) then {
    ["BATCOM", "WARN", format ["applyCommands: Command batch size (%1) exceeds limit (%2), truncating",
        count _commands, _maxCommands]] call FUNC(logMessage);
    _commands resize _maxCommands;
};

private _executed = 0;
private _failed = 0;
private _errors = [];

["BATCOM", "DEBUG", format ["applyCommands: Processing %1 commands", count _commands]] call FUNC(logMessage);

{
    private _command = _x;
    private _groupId = _command getOrDefault ["group_id", ""];
    private _cmdType = _command getOrDefault ["type", ""];
    private _params = _command getOrDefault ["params", createHashMap];

    // Handle spawn_squad/deploy_asset specially (don't require existing group resolution)
    private _success = false;
    if (_cmdType in ["spawn_squad", "deploy_asset"]) then {
        // Pass through the desired group_id so spawns can tag the group for follow-on orders
        _params set ["group_id", _groupId];
        switch (_cmdType) do {
            case "spawn_squad": {
                _success = [_params] call FUNC(applySpawnCommand);
                if (!_success) then {_errors pushBack format ["Spawn command failed: %1", _params];};
            };
            case "deploy_asset": {
                _success = [_params] call FUNC(applyDeployAssetCommand);
                if (!_success) then {_errors pushBack format ["Deploy asset failed: %1", _params];};
            };
        };

        if (_success) then {_executed = _executed + 1;} else {_failed = _failed + 1;};
        continue;
    };

    // For other commands, resolve group
    private _group = [_groupId] call FUNC(resolveGroup);

    if (isNull _group) then {
        _failed = _failed + 1;
        _errors pushBack format ["Group not found: %1", _groupId];
        ["BATCOM", "ERROR", format ["applyCommands: Group not found: %1", _groupId]] call FUNC(logMessage);
        continue;
    };

    // Check if group is controlled
    private _groupSide = side _group;
    private _controlledSides = GVAR(controlledSides);
    if !(_groupSide in _controlledSides) then {
        _failed = _failed + 1;
        _errors pushBack format ["Group %1 is not controlled (side: %2)", _groupId, _groupSide];
        ["BATCOM", "ERROR", format ["applyCommands: Group %1 is not controlled", _groupId]] call FUNC(logMessage);
        continue;
    };

    // Execute command by type
    switch (_cmdType) do {
        case "move_to": {
            _success = [_group, _params] call FUNC(applyMoveCommand);
        };
        case "defend_area": {
            _success = [_group, _params] call FUNC(applyDefendCommand);
        };
        case "patrol_route": {
            _success = [_group, _params] call FUNC(applyPatrolCommand);
        };
        case "seek_and_destroy": {
            _success = [_group, _params] call FUNC(applySeekCommand);
        };
        case "transport_group": {
            _success = [_group, _params] call FUNC(applyTransportCommand);
        };
        case "escort_group": {
            _success = [_group, _params] call FUNC(applyEscortCommand);
        };
        case "fire_support": {
            _success = [_group, _params] call FUNC(applyFireSupportCommand);
        };
        case "deploy_asset": {
            _success = [_params] call FUNC(applyDeployAssetCommand);
            // deploy_asset does not target existing group; treat like spawn
            if (_success) then {_executed = _executed + 1;} else {
                _failed = _failed + 1;
                _errors pushBack format ["Deploy asset failed: %1", _params];
            };
            continue;
        };
        default {
            _failed = _failed + 1;
            _errors pushBack format ["Unknown command type: %1", _cmdType];
            ["BATCOM", "ERROR", format ["applyCommands: Unknown command type: %1", _cmdType]] call FUNC(logMessage);
        };
    };

    if (_success) then {
        _executed = _executed + 1;
    } else {
        _failed = _failed + 1;
        _errors pushBack format ["Command failed: %1 for %2", _cmdType, _groupId];
    };
} forEach _commands;

["BATCOM", "INFO", format ["applyCommands: Executed %1/%2 commands (%3 failed)",
    _executed, count _commands, _failed]] call FUNC(logMessage);

createHashMapFromArray [
    ["executed", _executed],
    ["failed", _failed],
    ["errors", _errors]
]
