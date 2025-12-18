// Core functions
PREP(init);
PREP(shutdown);
PREP(isEnabled);

// Pythia interface
PREP(pythiaCall);
PREP(logMessage);
PREP(hashmapToArray);
PREP(arrayToHashmap);

// Scanning functions
PREP(getGroupId);
PREP(getGroupType);
PREP(hasFlashlight);
PREP(scanGroups);
PREP(scanPlayers);
PREP(scanObjectives);
PREP(worldScan);

// Command execution functions
PREP(resolveGroup);
PREP(applyCommands);
PREP(applyMoveCommand);
PREP(applyDefendCommand);
PREP(applyPatrolCommand);
PREP(applySeekCommand);
PREP(applySpawnCommand);
PREP(applyTransportCommand);
PREP(applyEscortCommand);
PREP(applyFireSupportCommand);
PREP(applyDeployAssetCommand);
PREP(batcomSetAOBoundary);

// Admin interface functions
PREP(batcomInit);
PREP(setMissionIntent);
PREP(deployCommander);
PREP(addObjective);

// Utility functions
PREP(getSpawnAltitude);
PREP(testPythia);
PREP(testGeminiConnection);
PREP(debugInit);
PREP(testInitConfig);
PREP(batcomDebug);
PREP(debugLog);
PREP(getTokenStats);

// AO Lifecycle & Tracking
PREP(aoProgress);
PREP(taskComplete);
PREP(batcomAOLifecycle);
PREP(trackAOObjectives);
PREP(trackObjectiveContributions);
PREP(initCasualtyTracking);

// Resource Pool & UI
PREP(batcomResourcePoolUI);
PREP(getResourcePoolTemplate);
PREP(getDefaultAssetClasses);

// Commander AO Functions
PREP(commanderStartAO);
PREP(commanderEndAO);
PREP(batcomAutoInit);
