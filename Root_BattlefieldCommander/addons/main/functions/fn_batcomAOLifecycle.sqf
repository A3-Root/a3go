#include "..\script_component.hpp"
/*
 * Author: Root
 * BATCOM AO Lifecycle Manager - Automatic AO tracking and commander management
 *
 * This script automatically:
 * 1. Monitors for AO start/end events
 * 2. Sets up BATCOM commander when AO starts
 * 3. Tracks objectives and reports to BATCOM
 * 4. Triggers analysis when AO ends
 * 5. Prepares for next AO
 *
 * Arguments:
 * None (runs automatically on server start)
 *
 * Return Value:
 * None
 *
 * Example:
 * call Root_fnc_batcomAOLifecycle; // Start lifecycle manager
 */

if (!isServer) exitWith {};
if (!isNil "BATCOM_lifecycleRunning") exitWith {
    ["BATCOM", "WARN", "AO Lifecycle manager already running"] call FUNC(logMessage);
};

["BATCOM", "INFO", "Starting AO Lifecycle Manager"] call FUNC(logMessage);

BATCOM_lifecycleRunning = true;
BATCOM_currentAOActive = false;
BATCOM_currentAOId = "";
BATCOM_objectivesTracked = createHashMap;

// Main lifecycle loop
[] spawn {
    private _lastAOState = false;
    private _aoFailCheckTime = 0;

    while {BATCOM_lifecycleRunning} do {
        try {
            // Check if AO is active (QS_classic_AI_active)
            private _aoActive = missionNamespace getVariable ["QS_classic_AI_active", false];
            if (!(_aoActive isEqualType true)) then {
                throw format ["QS_classic_AI_active has invalid type %1", typeName _aoActive];
            };

            // AO State Change Detection
            if (_aoActive && !_lastAOState) then {
                // AO STARTED
                ["BATCOM", "INFO", "=== AO STARTED - Initializing Commander ==="] call FUNC(logMessage);

                // Wait a moment for AO to fully initialize
                sleep 2;

                // Generate AO ID
                private _aoId = format ["AO_%1_%2", date select 3, date select 4]; // Hour_Minute
                BATCOM_currentAOId = _aoId;
                BATCOM_currentAOActive = true;

                // Get AO position and size
                private _aoPos = missionNamespace getVariable ["QS_AOpos", [0,0,0]];
                private _aoSize = missionNamespace getVariable ["QS_aoSize", 1000];

                ["BATCOM", "INFO", format ["AO Position: %1, Size: %2", _aoPos, _aoSize]] call FUNC(logMessage);

                // Set AO boundary
                ["QS_marker_aoCircle"] call Root_fnc_batcomSetAOBoundary;

                // Start AO tracking
                [_aoId] call Root_fnc_commanderStartAO;

                // Initialize objectives tracking
                call FUNC(trackAOObjectives);

                // Start objective monitoring loop
                [] spawn {
                    while {BATCOM_currentAOActive} do {
                        call FUNC(trackAOObjectives);
                        sleep 15; // Update objectives every 15 seconds
                    };
                };

                ["BATCOM", "INFO", "=== Commander Initialized for AO ==="] call FUNC(logMessage);

            } else {
                if (!_aoActive && _lastAOState) then {
                    // AO ENDED
                    ["BATCOM", "INFO", "=== AO ENDED - Starting Analysis ==="] call FUNC(logMessage);

                    BATCOM_currentAOActive = false;

                    // Determine success/failure
                    private _aoFailed = missionNamespace getVariable ["QS_aoFailVar", false];
                    private _aoSuccess = !_aoFailed;

                    ["BATCOM", "INFO", format ["AO Result: %1", ["FAILURE", "SUCCESS"] select (_aoSuccess)]] call FUNC(logMessage);

                    // End AO tracking and get HVT designations
                    call Root_fnc_commanderEndAO;

                    // Trigger learning/analysis
                    [] spawn {
                        sleep 5; // Brief delay before analysis
                        ["BATCOM", "INFO", "Triggering post-AO analysis..."] call FUNC(logMessage);

                        // Python analysis will run automatically via commanderEndAO
                        // HVT designations are applied in fn_commanderEndAO

                        ["BATCOM", "INFO", "Post-AO analysis complete - Ready for next AO"] call FUNC(logMessage);
                    };

                    // Clear tracked objectives
                    BATCOM_objectivesTracked = createHashMap;

                    ["BATCOM", "INFO", "=== Ready for Next AO ==="] call FUNC(logMessage);
                };
            };

            _lastAOState = _aoActive;

        } catch {
            ["BATCOM", "ERROR", format ["Lifecycle manager error: %1", _exception]] call FUNC(logMessage);
        };

        sleep 5; // Check every 5 seconds
    };
};

["BATCOM", "INFO", "AO Lifecycle Manager started successfully"] call FUNC(logMessage);
true
