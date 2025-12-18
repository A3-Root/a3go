# BATCOM Task Examples

Comprehensive examples of different task types you can assign to the AI commander using `commanderTask`.

---

## Task Format Overview

**Simple Format** (legacy):
```sqf
["commanderTask", [DESCRIPTION, UNIT_CLASSES, PRIORITY], nil] call Root_fnc_batcomInit;
```

**Advanced Format** (recommended):
```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Task description"],
    ["priority", 0-10],
    ["position", [x, y, z]],
    ["radius", meters],
    ["task_type", "hint"],
    ["metadata", createHashMapFromArray [...]]
], nil] call Root_fnc_batcomInit;
```

---

## Defensive Tasks

### 1. Defend Fixed Position
Establish defensive perimeter around a location.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Defend the control tower at all costs. Prevent enemy from entering the compound."],
    ["priority", 10],
    ["position", [5234, 5678, 0]],
    ["radius", 150],
    ["task_type", "defend_area"]
], nil] call Root_fnc_batcomInit;
```

### 2. Protect Specific Unit/HVT
Guard a high-value target that may move.

```sqf
private _hvtPos = getPos hvt_bravo6;
["commanderTask", createHashMapFromArray [
    ["description", "Protect HVT 'Bravo-6' from enemy capture or elimination. Stay within 200m of HVT."],
    ["priority", 10],
    ["target_unit", "hvt_bravo6"],
    ["position", _hvtPos],
    ["radius", 200],
    ["task_type", "protect_hvt"],
    ["metadata", createHashMapFromArray [
        ["hvt_name", "Bravo-6"],
        ["hvt_importance", "critical"],
        ["can_relocate", true]  // Hint: AI can move HVT if threatened
    ]]
], nil] call Root_fnc_batcomInit;
```

### 3. Layered Defense
Multiple defensive lines.

```sqf
// Outer perimeter
["commanderTask", createHashMapFromArray [
    ["description", "Establish outer defensive perimeter to intercept enemy approaches"],
    ["priority", 7],
    ["position", [5000, 5000, 0]],
    ["radius", 400],
    ["task_type", "defend_area"]
], nil] call Root_fnc_batcomInit;

// Inner strongpoint
["commanderTask", createHashMapFromArray [
    ["description", "Defend inner strongpoint - last line of defense"],
    ["priority", 9],
    ["position", [5000, 5000, 0]],
    ["radius", 100],
    ["task_type", "defend_area"]
], nil] call Root_fnc_batcomInit;
```

---

## Patrol Tasks

### 4. Area Patrol
Continuous patrols in a zone.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Maintain continuous patrols around the airfield perimeter. Detect and report enemy movement."],
    ["priority", 7],
    ["patrol_waypoints", [[5000, 5000, 0], [5200, 5000, 0], [5200, 5200, 0], [5000, 5200, 0]]],
    ["task_type", "patrol"],
    ["area_center", [5100, 5100, 0]],
    ["area_radius", 300]
], nil] call Root_fnc_batcomInit;
```

### 5. Route Patrol
Patrol specific path between points.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Patrol supply route between main base and forward outpost. Ensure route remains clear."],
    ["priority", 6],
    ["patrol_waypoints", [[3000, 3000, 0], [3500, 4000, 0], [4000, 4500, 0], [4500, 5000, 0], [5000, 6000, 0]]],
    ["task_type", "route_patrol"],
    ["metadata", createHashMapFromArray [
        ["patrol_frequency", "continuous"],
        ["threat_level", "moderate"]
    ]]
], nil] call Root_fnc_batcomInit;
```

### 6. Reconnaissance Patrol
Scout enemy positions.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Conduct reconnaissance of enemy positions in sector 7-8. Gather intelligence without engaging unless necessary."],
    ["priority", 8],
    ["area_center", [7500, 8200, 0]],
    ["area_radius", 600],
    ["task_type", "reconnaissance"],
    ["metadata", createHashMapFromArray [
        ["stealth_priority", "high"],
        ["engagement_rules", "defensive_only"]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

## Offensive Tasks

### 7. Eliminate Specific Threat
Hunt down priority target.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Locate and eliminate enemy mortar team operating in sector 5-7. They are shelling our positions."],
    ["priority", 9],
    ["area_center", [5500, 7200, 0]],
    ["area_radius", 500],
    ["task_type", "hunt_enemy"],
    ["metadata", createHashMapFromArray [
        ["target_type", "mortar_team"],
        ["threat_level", "critical"],
        ["time_sensitive", true]
    ]]
], nil] call Root_fnc_batcomInit;
```

### 8. Clear Area of Enemies
Offensive sweep operation.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Clear the village of enemy forces. Sweep all buildings and neutralize any threats."],
    ["priority", 8],
    ["position", [6234, 7890, 0]],
    ["radius", 250],
    ["task_type", "clear_area"],
    ["metadata", createHashMapFromArray [
        ["area_name", "Village Chernarus"],
        ["civilian_presence", true],
        ["rules_of_engagement", "positive_id_required"]
    ]]
], nil] call Root_fnc_batcomInit;
```

### 9. Assault Position
Attack and capture specific objective.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Assault and capture the enemy-held communications relay station. Neutralize defenders and secure the facility."],
    ["priority", 9],
    ["position", [8000, 9000, 0]],
    ["radius", 100],
    ["task_type", "assault_objective"],
    ["spawn_assets", ["infantry_squad", "mech_infantry"]],
    ["metadata", createHashMapFromArray [
        ["defender_strength", "platoon_sized"],
        ["objective_value", "strategic"]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

## Support & Logistics Tasks

### 10. Escort Mission
Protect moving convoy or unit.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Escort supply convoy from main base to forward operating base. Protect convoy from ambush."],
    ["priority", 7],
    ["target_group", "convoy_alpha"],
    ["task_type", "escort"],
    ["patrol_waypoints", [[3000, 3000, 0], [4000, 4500, 0], [5000, 6000, 0]]],
    ["metadata", createHashMapFromArray [
        ["convoy_size", 3],
        ["cargo_importance", "high"],
        ["threat_level", "high"],
        ["alternate_route", [[3000, 3000, 0], [3200, 4200, 0], [4800, 6200, 0]]]
    ]]
], nil] call Root_fnc_batcomInit;
```

### 11. Provide Fire Support
Standby for fire missions.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Position mortar/artillery assets to provide fire support for friendly forces. Maintain readiness for fire missions."],
    ["priority", 6],
    ["position", [4500, 4500, 0]],
    ["task_type", "fire_support_standby"],
    ["metadata", createHashMapFromArray [
        ["coverage_area", [[5000, 5000], 2000]],  // Center and radius
        ["response_time", "5min"],
        ["ammo_type", ["HE", "smoke", "illumination"]]
    ]]
], nil] call Root_fnc_batcomInit;
```

### 12. Deploy Quick Reaction Force (QRF)
Maintain ready reserve for emergencies.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Deploy and maintain Quick Reaction Force ready to respond to enemy breakthroughs or emergencies."],
    ["priority", 8],
    ["position", [5000, 5000, 0]],  // Central staging area
    ["task_type", "qrf_standby"],
    ["spawn_assets", ["mech_infantry", "attack_heli"]],
    ["unit_classes", ["I_Soldier_F", "I_MRAP_03_F"]],
    ["metadata", createHashMapFromArray [
        ["response_time_requirement", "5min"],
        ["deployment_radius", 3000]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

## Deployment Tasks

### 13. Deploy Units to Position
Spawn and position reinforcements.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Deploy rifle squad to northern ridge and establish overwatch position covering the valley approach."],
    ["priority", 7],
    ["position", [6000, 7000, 0]],
    ["unit_classes", ["I_Soldier_F", "I_Soldier_AR_F", "I_Soldier_GL_F", "I_medic_F"]],
    ["spawn_assets", ["infantry_squad"]],
    ["task_type", "deploy_and_defend"]
], nil] call Root_fnc_batcomInit;
```

### 14. Deploy Specialized Asset
Use specific resource pool assets.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Deploy attack helicopter to provide close air support for ground forces engaged in sector 5-6."],
    ["priority", 8],
    ["position", [5500, 6200, 0]],
    ["spawn_assets", ["attack_heli"]],
    ["task_type", "deploy_air_support"],
    ["metadata", createHashMapFromArray [
        ["target_area", [5500, 6200, 0]],
        ["support_duration", "ongoing"],
        ["priority_targets", ["armor", "vehicles"]]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

## Complex Multi-Phase Tasks

### 15. Ambush Setup
Prepare and execute ambush.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Set up ambush along enemy supply route. Wait for convoy, engage and destroy, then withdraw."],
    ["priority", 7],
    ["position", [7000, 8000, 0]],  // Ambush site
    ["radius", 150],
    ["task_type", "ambush"],
    ["metadata", createHashMapFromArray [
        ["ambush_type", "near"],
        ["kill_zone", [[7000, 8000], 50]],
        ["withdrawal_route", [[6800, 8200, 0], [6500, 8500, 0]]],
        ["target", "enemy_supply_convoy"]
    ]]
], nil] call Root_fnc_batcomInit;
```

### 16. Search and Rescue
Locate and extract friendly forces.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Downed pilot 'Eagle-2' is in enemy territory at approximate grid 8234-9012. Locate, secure, and extract."],
    ["priority", 10],
    ["position", [8234, 9012, 0]],
    ["radius", 300],  // Search area
    ["task_type", "search_and_rescue"],
    ["metadata", createHashMapFromArray [
        ["pilot_callsign", "Eagle-2"],
        ["last_known_position", [8234, 9012, 0]],
        ["enemy_presence", "confirmed"],
        ["extraction_method", "ground_or_air"],
        ["time_critical", true]
    ]]
], nil] call Root_fnc_batcomInit;
```

### 17. Holding Action
Delay enemy advance.

```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Conduct delaying action against enemy advance from the north. Slow enemy, inflict casualties, withdraw when necessary. Buy time for main force to reposition."],
    ["priority", 9],
    ["position", [5000, 7000, 0]],
    ["radius", 400],
    ["task_type", "delaying_action"],
    ["metadata", createHashMapFromArray [
        ["delay_duration_min", 30],  // Minutes
        ["withdrawal_triggers", ["50_percent_casualties", "enemy_flanking", "time_elapsed"]],
        ["fallback_position", [4800, 6500, 0]],
        ["acceptable_loss_rate", "moderate"]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

## Tips for Task Creation

### Priority Guidelines
- **10**: Survival-critical (HVT protection, last-stand defense)
- **9**: Mission-critical (primary objectives)
- **8**: High importance (eliminate key threats)
- **7**: Important (patrols, escorts)
- **5-6**: Moderate importance (secondary objectives)
- **1-4**: Low priority (optional tasks)

### Best Practices

1. **Be Descriptive**: LLM uses your description to understand intent
   ```sqf
   // Good
   ["description", "Defend the ammunition depot at grid 1234-5678. Enemy is approaching from the north. Priority is preventing depot destruction."]

   // Less effective
   ["description", "Defend position"]
   ```

2. **Include Geographic Context**: Position, radius, waypoints help AI plan
   ```sqf
   ["position", getPos objective_marker],
   ["radius", 200]
   ```

3. **Use Metadata for Details**: Any additional context the LLM might need
   ```sqf
   ["metadata", createHashMapFromArray [
       ["time_limit", 1800],
       ["acceptable_losses", "minimal"],
       ["civilian_presence", true]
   ]]
   ```

4. **Set Appropriate Task Types**: Helps AI categorize and prioritize
   - Use consistent naming: "defend_area", "patrol", "escort", "attack", etc.

5. **Combine Tasks**: Multiple tasks create layered operations
   ```sqf
   // Defense + Patrol + QRF = comprehensive defense plan
   ```

6. **Update Tasks Dynamically**: Tasks can be added mid-mission as situation changes
   ```sqf
   // Enemy breakthrough detected - add emergency response task
   ["commanderTask", createHashMapFromArray [
       ["description", "URGENT: Enemy breakthrough at sector 5-6. Deploy QRF immediately."],
       ["priority", 10],
       ["position", _breachLocation],
       ["task_type", "emergency_response"]
   ], nil] call Root_fnc_batcomInit;
   ```

---

## Testing Your Tasks

After adding tasks, verify they're working:

```sqf
// Check world scan sees objectives
private _snapshot = call BATCOM_fnc_worldScan;
systemChat format ["Objectives: %1", count (_snapshot get "objectives")];

// Monitor LLM decisions
call Root_fnc_getTokenStats;  // Should show increasing calls

// Check logs
// See @BATCOM/logs/ for LLM's interpretation of your tasks
```
