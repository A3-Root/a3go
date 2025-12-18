#include "..\script_component.hpp"
/*
 * Author: Root
 * Determines appropriate spawn altitude for a vehicle based on its type
 *
 * Arguments:
 * 0: Vehicle classname <STRING>
 *
 * Return Value:
 * Altitude in meters (ATL) <NUMBER>
 *
 * Example:
 * _altitude = ["O_Heli_Light_02_F"] call BATCOM_fnc_getSpawnAltitude;
 */

params [
    ["_classname", "", [""]]
];

if (_classname isEqualTo "") exitWith {0};

// Get vehicle config
private _config = configFile >> "CfgVehicles" >> _classname;
if (!isClass _config) exitWith {0};

// Determine vehicle type from simulation/parent classes
private _simulation = getText (_config >> "simulation");
private _vehicleClass = toLower (getText (_config >> "vehicleClass"));

// Check parent classes for type identification
private _isHelicopter = false;
private _isPlane = false;
private _isDrone = false;
private _isDroneHeli = false;
private _isDronePlane = false;

// Check inheritance chain
private _checkParent = _config;
while {!isNull _checkParent} do {
    private _parentClass = toLower (configName _checkParent);

    // Helicopter detection
    if (_parentClass in ["helicopter", "helicopter_base_f", "helicopter_base_h"]) exitWith {
        _isHelicopter = true;
    };

    // Plane detection
    if (_parentClass in ["plane", "plane_base_f", "air"]) exitWith {
        _isPlane = true;
    };

    // UAV detection
    if (_parentClass in ["uav", "uav_01_base_f", "uav_02_base_f", "uav_03_base_f", "uav_04_base_f", "uav_05_base_f", "uav_06_base_f"]) exitWith {
        _isDrone = true;
    };

    _checkParent = inheritsFrom _checkParent;
};

// Additional simulation-based checks
if (_simulation in ["helicopterx", "helicopterrtd"]) then {_isHelicopter = true};
if (_simulation in ["airplanex", "airplane"]) then {_isPlane = true};

// Classify drones more specifically
if (_isDrone) then {
    // Check if drone is rotary or fixed-wing
    if (_isHelicopter || {_simulation in ["helicopterx", "helicopterrtd"]}) then {
        _isDroneHeli = true;
    };
    if (_isPlane || {_simulation in ["airplanex", "airplane"]}) then {
        _isDronePlane = true;
    };

    // If still unclassified, check size/mass as heuristic
    if (!_isDroneHeli && !_isDronePlane) then {
        private _mass = getNumber (_config >> "mass");
        if (_mass < 100) then {
            _isDroneHeli = true;  // Small drones are typically quadcopters
        } else {
            _isDronePlane = true;  // Larger drones are typically fixed-wing
        };
    };
};

// Determine altitude based on type
private _altitude = 0;

if (_isPlane && !_isDrone) then {
    // Manned planes: 300m minimum
    _altitude = 300;
} else {
    if (_isHelicopter && !_isDrone) then {
        // Manned helicopters: 100m minimum
        _altitude = 100;
    } else {
        if (_isDronePlane) then {
            // Fixed-wing drones: 300m (same as planes)
            _altitude = 300;
        } else {
            if (_isDroneHeli) then {
                // Rotary drones: 25-50m depending on size
                private _mass = getNumber (_config >> "mass");
                if (_mass > 150) then {
                    _altitude = 100;  // Large combat drones (Greyhawk, etc.)
                } else {
                    _altitude = 50;   // Small quad/surveillance drones
                };
            } else {
                // Ground vehicles, boats, etc: 0m
                _altitude = 0;
            };
        };
    };
};

["BATCOM", "DEBUG", format ["getSpawnAltitude: %1 -> %2m (heli:%3, plane:%4, drone:%5, sim:%6)",
    _classname, _altitude, _isHelicopter, _isPlane, _isDrone, _simulation
]] call FUNC(logMessage);

_altitude
