#include "script_component.hpp"

// Initialize BATCOM on server
// CBA has already compiled all functions in preInit via XEH_PREP
if (isServer) then {
    // Initialize debug mode flag (disabled by default)
    GVAR(debugMode) = false;

    if (GVAR(debugMode)) then {
        diag_log "BATCOM: XEH_postInit - Calling init...";
    };
    call FUNC(init);
};
