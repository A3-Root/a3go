#include "..\script_component.hpp"
/*
 * Author: Root
 * Command processing loop - polls Python for pending commands and executes them
 *
 * This script is spawned when the commander is deployed and runs in the background,
 * periodically checking for commands from Python and executing them.
 *
 * Arguments:
 * 0: Poll interval in seconds <NUMBER> (default: 0.1 for near-immediate execution)
 *
 * Example:
 * [1.0] spawn compile preprocessFileLineNumbers QPATHTOF(scripts\commandProcessLoop.sqf);
 */

params [
    ["_pollInterval", 1.0, [0]]
];

if (!isServer) exitWith {};

["BATCOM", "INFO", format ["commandProcessLoop: Started (interval: %1s)", _pollInterval]] call FUNC(logMessage);

while {GVAR(deployed)} do {
    try {
        // Check if still enabled
        if (!(call FUNC(isEnabled))) exitWith {
            ["BATCOM", "WARN", "commandProcessLoop: BATCOM disabled, stopping loop"] call FUNC(logMessage);
        };

        // Poll Python for pending commands
        private _resultArray = ["batcom.get_pending_commands", []] call FUNC(pythiaCall);

        if (isNil "_resultArray") then {
            throw "Pythia returned nil while polling pending commands";
        };

        // Convert result array to hashmap (Pythia doesn't support dict->hashmap)
        private _result = if (_resultArray isEqualType []) then {
            [_resultArray] call FUNC(arrayToHashmap)
        } else {
            throw format ["Unexpected result type from pending commands: %1", typeName _resultArray];
        };

        if (!isNil "_result" && {_result isEqualType createHashMap}) then {
            private _status = _result getOrDefault ["status", ""];

            if (_status isEqualTo "ok") then {
                private _commandsArray = _result getOrDefault ["commands", []];

                if (count _commandsArray > 0) then {
                    ["BATCOM", "DEBUG", format ["commandProcessLoop: Received %1 commands", count _commandsArray]] call FUNC(logMessage);

                    // Convert each command from array to hashmap
                    private _commands = [];
                    {
                        private _cmdHashmap = [_x] call FUNC(arrayToHashmap);
                        _commands pushBack _cmdHashmap;
                    } forEach _commandsArray;

                    // Execute commands
                    private _summary = [_commands] call FUNC(applyCommands);

                    // Log summary
                    private _failed = _summary getOrDefault ["failed", 0];

                    if (_failed > 0) then {
                        private _errors = _summary getOrDefault ["errors", []];
                        ["BATCOM", "WARN", format ["commandProcessLoop: %1 commands failed: %2",
                            _failed, _errors]] call FUNC(logMessage);
                    };
                };
            } else {
                private _error = _result getOrDefault ["error", "unknown"];
                throw format ["Python error: %1", _error];
            };
        };

    } catch {
        ["BATCOM", "ERROR", format ["commandProcessLoop: Exception: %1", _exception]] call FUNC(logMessage);
    };

    // Wait for next poll
    sleep _pollInterval;
};

["BATCOM", "INFO", "commandProcessLoop: Stopped"] call FUNC(logMessage);
