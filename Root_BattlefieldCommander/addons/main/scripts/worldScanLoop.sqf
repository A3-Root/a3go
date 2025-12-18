#include "..\script_component.hpp"
/*
 * Author: Root
 * Main world scanning loop - runs continuously when commander is deployed
 *
 * This script is spawned when the commander is deployed and runs in the background,
 * periodically scanning the world state and sending it to Python.
 *
 * Arguments:
 * 0: Scan interval in seconds <NUMBER> (default: 2.0)
 *
 * Example:
 * [2.0] spawn compile preprocessFileLineNumbers QPATHTOF(scripts\worldScanLoop.sqf);
 */

params [
    ["_scanInterval", 2.0, [0]]
];

if (!isServer) exitWith {};

["BATCOM", "INFO", format ["worldScanLoop: Started (interval: %1s)", _scanInterval]] call FUNC(logMessage);

while {GVAR(deployed)} do {
    try {
        // Check if still enabled
        if (!(call FUNC(isEnabled))) exitWith {
            ["BATCOM", "WARN", "worldScanLoop: BATCOM disabled, stopping loop"] call FUNC(logMessage);
        };

        // Perform world scan
        private _snapshot = call FUNC(worldScan);
        if (!(_snapshot isEqualType createHashMap)) then {
            throw format ["worldScan returned %1 instead of HASHMAP", typeName _snapshot];
        };

        if (count _snapshot > 0) then {
            // Convert hashmap snapshot to array for Python compatibility
            private _snapshotArray = [];
            try {
                _snapshotArray = [_snapshot] call FUNC(hashmapToArray);
                if (!(_snapshotArray isEqualType [])) then {
                    throw format ["hashmapToArray returned %1", typeName _snapshotArray];
                };
            } catch {
                ["BATCOM", "ERROR", format ["worldScanLoop: Failed to convert snapshot to array: %1", _exception]] call FUNC(logMessage);
                _snapshotArray = [];
            };

            if (!(_snapshotArray isEqualType [])) then {
                ["BATCOM", "ERROR", "worldScanLoop: Snapshot conversion failed (not an array)"] call FUNC(logMessage);
                sleep _scanInterval;
                continue;
            };

            // Send snapshot to Python
            // Note: This is currently synchronous, in later phases we'll make it async
            private _resultArray = ["batcom.world_snapshot", [_snapshotArray]] call FUNC(pythiaCall);

            if (isNil "_resultArray") then {
                throw "Failed to send snapshot to Python (nil result)";
            } else {
                // Convert result array to hashmap (Pythia doesn't support dict->hashmap)
                private _result = if (_resultArray isEqualType []) then {
                    [_resultArray] call FUNC(arrayToHashmap)
                } else {
                    throw format ["Unexpected result array type: %1", typeName _resultArray]
                };

                if ((_result getOrDefault ["status", ""]) != "ok") then {
                    throw format ["Python error: %1",
                        _result getOrDefault ["error", "unknown"]];
                };
            };
        };

    } catch {
        ["BATCOM", "ERROR", format ["worldScanLoop: Exception: %1", _exception]] call FUNC(logMessage);
    };

    // Wait for next scan
    sleep _scanInterval;
};

["BATCOM", "INFO", "worldScanLoop: Stopped"] call FUNC(logMessage);
