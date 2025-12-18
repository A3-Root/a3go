#include "..\script_component.hpp"
/*
 * Author: Root
 * Debug init - test imports step by step
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call BATCOM_fnc_debugInit;
 */

if (!isServer) exitWith {
    diag_log "BATCOM: Debug must be run on server";
};

diag_log "========================================";
diag_log "BATCOM: Debug Init Test";
diag_log "========================================";

// Call debug init
private _result = try {
    private _response = ["batcom.debug_init", []] call py3_fnc_callExtension;
    if (isNil "_response") then {
        throw "batcom.debug_init returned nil";
    };
    _response
} catch {
    diag_log format ["BATCOM: ✗ Exception: %1", _exception];
    nil
};

if (isNil "_result") exitWith {
    diag_log "BATCOM: ✗ No response from Python";
    diag_log "BATCOM: Pythia may not be working";
    diag_log "========================================";
};

// Result should be a string
if (_result isEqualType "") then {
    // Split long results into multiple lines
    private _maxLen = 100;
    if (count _result > _maxLen) then {
        private _parts = _result splitString "|";
        {
            diag_log format ["BATCOM: %1", _x];
        } forEach _parts;
    } else {
        diag_log format ["BATCOM: %1", _result];
    };
} else {
    diag_log format ["BATCOM: Unexpected result type: %1", typeName _result];
    diag_log format ["BATCOM: Value: %1", _result];
};

diag_log "========================================";
