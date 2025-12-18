#include "..\script_component.hpp"
/*
 * Author: Root
 * BATCOM Resource Pool Management UI
 *
 * Easy in-game interface to manage resource pools with template support.
 *
 * Arguments:
 * 0: Action <STRING> - "view", "add", "edit", "remove", "clear", "load_template", "list_templates", "set_defense_phase"
 * 1: Parameters <ANY> (optional) - Action-specific parameters
 *
 * Return Value:
 * Success <BOOL>
 *
 * Examples:
 * // View current resource pool
 * ["view"] call Root_fnc_batcomResourcePoolUI;
 *
 * // List available templates
 * ["list_templates"] call Root_fnc_batcomResourcePoolUI;
 *
 * // Load a template
 * ["load_template", ["EAST", "medium"]] call Root_fnc_batcomResourcePoolUI;
 *
 * // Add asset with defense_only flag
 * ["add", ["EAST", "heavy_armor", 2, ["O_MBT_02_cannon_F"], true, "Main battle tank"]] call Root_fnc_batcomResourcePoolUI;
 *
 * // Activate AO Defense Phase
 * ["set_defense_phase", true] call Root_fnc_batcomResourcePoolUI;
 *
 * // Edit existing asset
 * ["edit", ["EAST", "infantry_squad", 10]] call Root_fnc_batcomResourcePoolUI;
 *
 * // Remove asset
 * ["remove", ["EAST", "infantry_squad"]] call Root_fnc_batcomResourcePoolUI;
 *
 * // Clear all resources for a side
 * ["clear", "EAST"] call Root_fnc_batcomResourcePoolUI;
 */

params [
    ["_action", "view", [""]],
    ["_params", [], [[], "", true]]
];

// ========== VIEW ACTION ==========
if (_action == "view") exitWith {
    hint "BATCOM: Getting resource pool status...";

    private _result = ["batcom.resource_pool_get_status", []] call py3_fnc_callExtension;
    private _resultHash = createHashMapFromArray _result;

    if ((_resultHash get "status") != "ok") exitWith {
        private _error = _resultHash getOrDefault ["error", "Unknown error"];
        systemChat format ["BATCOM ERROR: %1", _error];
        hint format ["BATCOM ERROR\n%1", _error];
        false
    };

    private _resourcePool = createHashMapFromArray (_resultHash get "resource_pool");
    private _aoDefensePhase = _resultHash getOrDefault ["ao_defense_phase", false];

    systemChat "========================================";
    systemChat "BATCOM RESOURCE POOL STATUS";
    systemChat "========================================";
    systemChat format ["AO Defense Phase: %1", ["INACTIVE", "ACTIVE"] select _aoDefensePhase];
    systemChat "";

    if (count _resourcePool == 0) then {
        systemChat "STATUS: Resource pool is EMPTY";
        systemChat "";
        systemChat "To load a template:";
        systemChat "  ['load_template', ['EAST', 'medium']] call Root_fnc_batcomResourcePoolUI;";
        systemChat "";
        systemChat "To list templates:";
        systemChat "  ['list_templates'] call Root_fnc_batcomResourcePoolUI;";
        systemChat "========================================";
        hint "BATCOM: Resource pool is empty\nUse 'load_template' to populate";
    } else {
        private _totalAssets = 0;

        {
            private _side = _x;
            private _sideData = createHashMapFromArray _y;

            systemChat format ["Side: %1", _side];
            systemChat "----------------------------------------";

            {
                private _assetType = _x;
                private _assetData = createHashMapFromArray _y;

                private _max = _assetData getOrDefault ["max", 0];
                private _used = _assetData getOrDefault ["used", 0];
                private _remaining = _assetData getOrDefault ["remaining", 0];
                private _defenseOnly = _assetData getOrDefault ["defense_only", false];
                private _description = _assetData getOrDefault ["description", ""];

                _totalAssets = _totalAssets + 1;

                systemChat format ["  Type: %1", _assetType];
                systemChat format ["  Max: %1 | Used: %2 | Remaining: %3", _max, _used, _remaining];

                if (_defenseOnly) then {
                    systemChat "  DEFENSE ONLY - Requires AO Defense Phase";
                };

                if (_description != "") then {
                    systemChat format ["  Info: %1", _description];
                };

                systemChat "";
            } forEach _sideData;
        } forEach _resourcePool;

        systemChat "========================================";
        systemChat format ["Total: %1 asset types configured", _totalAssets];
        if (_aoDefensePhase) then {
            systemChat "AO DEFENSE ACTIVE - All defense_only assets available";
        };
        systemChat "========================================";

        hint format ["BATCOM: Resource pool active\n%1 asset types\nAO Defense: %2", _totalAssets, ["OFF", "ON"] select _aoDefensePhase];
    };

    true
};

// ========== LIST TEMPLATES ACTION ==========
if (_action == "list_templates") exitWith {
    private _result = ["batcom.resource_pool_list_templates", []] call py3_fnc_callExtension;
    private _resultHash = createHashMapFromArray _result;

    if ((_resultHash get "status") != "ok") exitWith {
        private _error = _resultHash getOrDefault ["error", "Unknown error"];
        systemChat format ["BATCOM ERROR: %1", _error];
        false
    };

    private _templates = _resultHash get "templates";

    systemChat "========================================";
    systemChat "AVAILABLE RESOURCE TEMPLATES";
    systemChat "========================================";

    {
        private _templateData = createHashMapFromArray _x;
        private _name = _templateData get "name";
        private _desc = _templateData get "description";

        systemChat format ["%1: %2", _name, _desc];
    } forEach _templates;

    systemChat "";
    systemChat "To load a template:";
    systemChat "  ['load_template', ['EAST', 'medium']] call Root_fnc_batcomResourcePoolUI;";
    systemChat "========================================";

    hint format ["BATCOM: %1 templates available\nCheck chat for list", count _templates];
    true
};

// ========== LOAD TEMPLATE ACTION ==========
if (_action == "load_template") exitWith {
    if (!(_params isEqualType []) || {count _params < 2}) exitWith {
        systemChat "BATCOM ERROR: Usage: ['load_template', ['SIDE', 'template_name']]";
        systemChat "Example: ['load_template', ['EAST', 'medium']]";
        hint "BATCOM ERROR: Invalid parameters";
        false
    };

    _params params ["_side", "_templateName"];

    private _loadResult = ["batcom.load_resource_template", [_templateName]] call py3_fnc_callExtension;
    private _loadHash = createHashMapFromArray _loadResult;

    if ((_loadHash get "status") != "ok") exitWith {
        private _error = _loadHash getOrDefault ["error", "Unknown error"];
        systemChat format ["BATCOM ERROR: %1", _error];
        hint format ["BATCOM ERROR\n%1", _error];
        false
    };

    private _sides = _loadHash getOrDefault ["sides", []];
    private _totalTypes = _loadHash getOrDefault ["total_asset_types", 0];

    systemChat format ["BATCOM: Loaded template '%1'", _templateName];
    systemChat format ["Sides configured: %1", _sides joinString ", "];
    systemChat format ["Total asset types: %1", _totalTypes];

    hint format ["BATCOM: Template loaded\n%1\n%2 asset types", _templateName, _totalTypes];
    true
};

// ========== SET DEFENSE PHASE ACTION ==========
if (_action == "set_defense_phase") exitWith {
    private _active = [false, _params] select (_params isEqualType true);

    private _result = ["batcom.set_ao_defense_phase", [_active]] call py3_fnc_callExtension;
    private _resultHash = createHashMapFromArray _result;

    if ((_resultHash get "status") != "ok") exitWith {
        private _error = _resultHash getOrDefault ["error", "Unknown error"];
        systemChat format ["BATCOM ERROR: %1", _error];
        false
    };

    private _message = _resultHash getOrDefault ["message", ""];
    systemChat format ["BATCOM: %1", _message];

    if (_active) then {
        hint "AO DEFENSE PHASE ACTIVATED\nAll defense_only assets available";
    } else {
        hint "AO Defense Phase deactivated";
    };

    true
};

// ========== ADD/EDIT ACTIONS (SERVER-ONLY) ==========
if (_action in ["add", "edit"]) exitWith {
    if (!isServer) exitWith {
        systemChat "BATCOM: Sending request to server...";
        [_action, _params] remoteExec ["Root_fnc_batcomResourcePoolUI", 2];
        true
    };

    if (!(_params isEqualType []) || {count _params < 3}) exitWith {
        systemChat format ["BATCOM ERROR: %1 requires [side, assetType, maxCount, (optional)classes, (optional)defenseOnly, (optional)description]", _action];
        systemChat format ["Example: ['%1', ['EAST', 'infantry_squad', 5, [], false, 'Basic infantry']]", _action];
        false
    };

    _params params ["_side", "_assetType", "_maxCount", ["_classes", []], ["_defenseOnly", false], ["_description", ""]];

    private _result = ["batcom.resource_pool_add_asset", [_side, _assetType, _maxCount, _classes, _defenseOnly, _description]] call py3_fnc_callExtension;
    private _resultHash = createHashMapFromArray _result;

    if ((_resultHash get "status") != "ok") exitWith {
        private _error = _resultHash getOrDefault ["error", "Unknown error"];
        systemChat format ["BATCOM ERROR: %1", _error];
        false
    };

    private _message = _resultHash getOrDefault ["message", ""];
    systemChat format ["BATCOM: %1", _message];

    if (_defenseOnly) then {
        systemChat "  (DEFENSE ONLY - requires AO Defense Phase)";
    };

    hint format ["BATCOM: %1 %2", ["Updated", "Added"] select (_action == "add"), _assetType];
    true
};

// ========== REMOVE ACTION (SERVER-ONLY) ==========
if (_action == "remove") exitWith {
    if (!isServer) exitWith {
        systemChat "BATCOM: Sending request to server...";
        [_action, _params] remoteExec ["Root_fnc_batcomResourcePoolUI", 2];
        true
    };

    if (!(_params isEqualType []) || {count _params < 2}) exitWith {
        systemChat "BATCOM ERROR: remove requires [side, assetType]";
        false
    };

    _params params ["_side", "_assetType"];

    private _result = ["batcom.resource_pool_remove_asset", [_side, _assetType]] call py3_fnc_callExtension;
    private _resultHash = createHashMapFromArray _result;

    if ((_resultHash get "status") != "ok") exitWith {
        private _error = _resultHash getOrDefault ["error", "Unknown error"];
        systemChat format ["BATCOM ERROR: %1", _error];
        false
    };

    private _message = _resultHash getOrDefault ["message", ""];
    systemChat format ["BATCOM: %1", _message];
    hint format ["BATCOM: Removed %1", _assetType];
    true
};

// ========== CLEAR ACTION (SERVER-ONLY) ==========
if (_action == "clear") exitWith {
    if (!isServer) exitWith {
        systemChat "BATCOM: Sending request to server...";
        [_action, _params] remoteExec ["Root_fnc_batcomResourcePoolUI", 2];
        true
    };

    private _side = ["", _params] select (_params isEqualType "");

    if (_side == "") exitWith {
        systemChat "BATCOM ERROR: clear requires side name";
        false
    };

    private _result = ["batcom.resource_pool_clear_side", [_side]] call py3_fnc_callExtension;
    private _resultHash = createHashMapFromArray _result;

    if ((_resultHash get "status") != "ok") exitWith {
        private _error = _resultHash getOrDefault ["error", "Unknown error"];
        systemChat format ["BATCOM ERROR: %1", _error];
        false
    };

    private _message = _resultHash getOrDefault ["message", ""];
    systemChat format ["BATCOM: %1", _message];
    hint format ["BATCOM: Cleared %1", _side];
    true
};

systemChat format ["BATCOM ERROR: Unknown action '%1'", _action];
systemChat "Available actions: view, list_templates, load_template, add, edit, remove, clear, set_defense_phase";
false
