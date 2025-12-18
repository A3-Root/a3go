#include "..\script_component.hpp"
/*
 * Author: Root
 * Get default unit/vehicle classes for an asset type and side
 *
 * Arguments:
 * 0: Side <STRING> - "EAST", "WEST", "GUER", "CIV"
 * 1: Asset Type <STRING> - "infantry_squad", "ifv", "tank", "attack_heli", etc.
 *
 * Return Value:
 * Array of class names <ARRAY>
 *
 * Example:
 * private _classes = ["EAST", "infantry_squad"] call Root_fnc_getDefaultAssetClasses;
 */

params [
    ["_side", "EAST", [""]],
    ["_assetType", "", [""]]
];

private _sideUpper = toUpper _side;
private _assetLower = toLower _assetType;

// Side-specific class mappings
private _classMap = createHashMap;

// EAST (CSAT)
if (_sideUpper == "EAST") then {
    _classMap = createHashMapFromArray [
        ["infantry_squad", ["O_Soldier_TL_F", "O_Soldier_AR_F", "O_Soldier_GL_F", "O_Soldier_F", "O_Soldier_LAT_F", "O_medic_F", "O_Soldier_F", "O_Soldier_F"]],
        ["ifv", ["O_APC_Tracked_02_cannon_F", "O_APC_Wheeled_02_rcws_F"]],
        ["tank", ["O_MBT_02_cannon_F", "O_MBT_04_cannon_F"]],
        ["attack_heli", ["O_Heli_Attack_02_dynamicLoadout_F", "O_Heli_Light_02_dynamicLoadout_F"]],
        ["transport_heli", ["O_Heli_Transport_04_covered_F", "O_Heli_Light_02_F"]],
        ["jet", ["O_Plane_CAS_02_dynamicLoadout_F", "O_Plane_Fighter_02_F"]],
        ["drone", ["O_UAV_02_dynamicLoadout_F", "O_UGV_01_rcws_F"]],
        ["mortar", ["O_Mortar_01_F"]],
        ["aa_vehicle", ["O_APC_Tracked_02_AA_F"]],
        ["artillery", ["O_MBT_02_arty_F"]]
    ];
};

// WEST (NATO)
if (_sideUpper == "WEST") then {
    _classMap = createHashMapFromArray [
        ["infantry_squad", ["B_Soldier_TL_F", "B_Soldier_AR_F", "B_Soldier_GL_F", "B_Soldier_F", "B_Soldier_LAT_F", "B_medic_F", "B_Soldier_F", "B_Soldier_F"]],
        ["ifv", ["B_APC_Tracked_01_rcws_F", "B_APC_Wheeled_01_cannon_F"]],
        ["tank", ["B_MBT_01_cannon_F", "B_MBT_01_TUSK_F"]],
        ["attack_heli", ["B_Heli_Attack_01_dynamicLoadout_F", "B_Heli_Light_01_dynamicLoadout_F"]],
        ["transport_heli", ["B_Heli_Transport_01_F", "B_Heli_Transport_03_F"]],
        ["jet", ["B_Plane_CAS_01_dynamicLoadout_F", "B_Plane_Fighter_01_F"]],
        ["drone", ["B_UAV_02_dynamicLoadout_F", "B_UGV_01_rcws_F"]],
        ["mortar", ["B_Mortar_01_F"]],
        ["aa_vehicle", ["B_APC_Tracked_01_AA_F"]],
        ["artillery", ["B_MBT_01_arty_F"]]
    ];
};

// GUER (AAF/Independent)
if (_sideUpper == "GUER") then {
    _classMap = createHashMapFromArray [
        ["infantry_squad", ["I_Soldier_TL_F", "I_Soldier_AR_F", "I_Soldier_GL_F", "I_Soldier_F", "I_Soldier_LAT_F", "I_medic_F", "I_Soldier_F", "I_Soldier_F"]],
        ["ifv", ["I_APC_tracked_03_cannon_F", "I_APC_Wheeled_03_cannon_F"]],
        ["tank", ["I_MBT_03_cannon_F"]],
        ["attack_heli", ["I_Heli_light_03_dynamicLoadout_F"]],
        ["transport_heli", ["I_Heli_Transport_02_F", "I_Heli_light_03_F"]],
        ["jet", ["I_Plane_Fighter_03_dynamicLoadout_F", "I_Plane_Fighter_04_F"]],
        ["drone", ["I_UAV_02_dynamicLoadout_F", "I_UGV_01_rcws_F"]],
        ["mortar", ["I_Mortar_01_F"]],
        ["aa_vehicle", ["I_LT_01_AA_F"]],
        ["artillery", ["I_Truck_02_MRL_F"]]
    ];
};

// CIV (Civilian - limited military options)
if (_sideUpper == "CIV") then {
    _classMap = createHashMapFromArray [
        ["infantry_squad", ["C_Man_1", "C_Man_1", "C_Man_1", "C_Man_1"]],
        ["ifv", ["I_MRAP_03_hmg_F"]],
        ["transport_heli", ["C_Heli_Light_01_civil_F"]],
        ["drone", ["C_UAV_01_F"]]
    ];
};

// Return classes for requested asset type
private _classes = _classMap getOrDefault [_assetLower, []];

if (count _classes == 0) then {
    ["BATCOM", "WARN", format ["No default classes for %1 / %2", _sideUpper, _assetType]] call FUNC(logMessage);
};

_classes
