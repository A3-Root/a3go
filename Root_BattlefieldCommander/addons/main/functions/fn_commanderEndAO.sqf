#include "..\script_component.hpp"
/*
 * Author: Root
 * End AO tracking and apply HVT designations
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * call Root_fnc_commanderEndAO
 */

if (!isServer) exitWith {false};

// Call Python API
private _result = ["batcom.batcom_init", ["commanderEndAO", [], true]] call py3_fnc_callExtension;

if (!isNil "_result" && {count _result > 0}) then {
    // Parse result as hashmap
    private _status = _result getOrDefault ["status", "error"];

    if (_status == "ok") then {
        // Extract HVT data
        private _hvtData = _result getOrDefault ["hvt_data", createHashMap];
        private _hvtPlayers = _hvtData getOrDefault ["players", []];
        private _hvtGroups = _hvtData getOrDefault ["groups", []];

        // Apply HVT status to players
        {
            private _uid = _x;
            private _player = objNull;

            // Find player by UID
            {
                if (getPlayerUID _x == _uid) exitWith {
                    _player = _x;
                };
            } forEach allPlayers;

            if (!isNull _player) then {
                _player setVariable ["batcom_hvt", true, true];
                _player setVariable ["batcom_hvt_reason", "Top performer in previous AO", true];

                ["BATCOM", "INFO", format ["Designated HVT: %1", name _player]] call FUNC(logMessage);
            };
        } forEach _hvtPlayers;

        // Apply HVT status to groups
        {
            private _groupId = _x;
            // Mark group as HVT (groups are recreated, so store in mission namespace)
            missionNamespace setVariable [format ["batcom_hvt_group_%1", _groupId], true, true];
        } forEach _hvtGroups;

        ["BATCOM", "INFO", format ["AO ended - Designated %1 HVT players, %2 HVT groups", count _hvtPlayers, count _hvtGroups]] call FUNC(logMessage);

        // Stop contribution tracking
        BATCOM_contribution_loop_running = false;

        true
    } else {
        ["BATCOM", "ERROR", "Failed to end AO"] call FUNC(logMessage);
        false
    };
} else {
    ["BATCOM", "ERROR", "No response from commanderEndAO"] call FUNC(logMessage);
    false
};
