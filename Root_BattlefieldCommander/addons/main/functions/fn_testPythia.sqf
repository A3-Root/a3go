#include "..\script_component.hpp"
/*
 * Author: Root
 * Test basic Pythia functionality and module loading
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * [] call BATCOM_fnc_testPythia;
 */

if (!isServer) exitWith {
    diag_log "BATCOM: Test must be run on server";
    false
};

diag_log "========================================";
diag_log "BATCOM: Pythia Diagnostic Test";
diag_log "========================================";

// Test 1: Check if Pythia is loaded
if (isNil "py3_fnc_callExtension") then {
    diag_log "BATCOM: ✗ FAILED - Pythia not loaded!";
    diag_log "BATCOM: SOLUTION - Launch with -mod=@Pythia";
    false
} else {
    diag_log "BATCOM: ✓ Pythia extension is loaded";

    // Test 2: Try a simple Python call
    diag_log "BATCOM: Testing simple Python call...";
    private _simpleTest = try {
        private _result = ["platform.python_version", []] call py3_fnc_callExtension;
        if (isNil "_result") then {
            throw "py3_fnc_callExtension returned nil for platform.python_version";
        };
        _result
    } catch {
        diag_log format ["BATCOM: ✗ Exception: %1", _exception];
        nil
    };

    if (isNil "_simpleTest") then {
        diag_log "BATCOM: ✗ Basic Pythia calls are failing";
        diag_log "BATCOM: Check @Pythia installation";
        false
    } else {
        diag_log format ["BATCOM: ✓ Python version: %1", _simpleTest];

        // Test 3: Check if batcom module is accessible
        diag_log "BATCOM: Checking if batcom module is loaded...";
        private _moduleTest = try {
            private _result = ["batcom.get_version", []] call py3_fnc_callExtension;
            if (isNil "_result") then {
                throw "py3_fnc_callExtension returned nil for batcom.get_version";
            };
            _result
        } catch {
            diag_log format ["BATCOM: ✗ Exception when calling batcom: %1", _exception];
            nil
        };

        if (isNil "_moduleTest") then {
            diag_log "BATCOM: ✗ batcom module not found!";
            diag_log "BATCOM: ISSUE - Pythia can't find the batcom Python module";
            diag_log "BATCOM: ";
            diag_log "BATCOM: SOLUTION 1 - Check mod is loaded:";
            diag_log "BATCOM:   Launch with: -mod=@Pythia;@Rootsbatcom";
            diag_log "BATCOM: ";
            diag_log "BATCOM: SOLUTION 2 - Verify batcom folder exists in mod root:";
            diag_log "BATCOM:   Check: @Rootsbatcom\batcom\__init__.py";
            diag_log "BATCOM: ";
            diag_log "BATCOM: SOLUTION 3 - Try rebuilding the mod:";
            diag_log "BATCOM:   Run: hemtt build";
            false
        } else {
            diag_log format ["BATCOM: ✓ batcom module version: %1", _moduleTest];

            // Test 4: Check BATCOM initialization status
            diag_log "BATCOM: Checking BATCOM initialization...";
            private _isInit = try {
                private _result = ["batcom.is_initialized", []] call py3_fnc_callExtension;
                if (isNil "_result") then {
                    throw "py3_fnc_callExtension returned nil for batcom.is_initialized";
                };
                _result
            } catch {
                false
            };

            // Handle response (could be bool or error)
            if (_isInit isEqualType true && _isInit) then {
                diag_log "BATCOM: ✓ BATCOM is already initialized";
            } else {
                diag_log "BATCOM: ⚠ BATCOM is not initialized";
                diag_log "BATCOM: Run: [] call BATCOM_fnc_init";
            };

            diag_log "========================================";
            diag_log "BATCOM: All basic tests passed!";
            diag_log "BATCOM: Module is accessible and working.";
            diag_log "========================================";
            true
        };
    };
};
