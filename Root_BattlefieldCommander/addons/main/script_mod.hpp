#ifndef BATCOM_SCRIPT_MOD_HPP
#define BATCOM_SCRIPT_MOD_HPP

#define MAINPREFIX z
#define PREFIX root_batcom

#define MAJOR 1
#define MINOR 0
#define PATCH 0
#define BUILD 0

#define VERSION MAJOR.MINOR.PATCH.BUILD
#define VERSION_AR MAJOR,MINOR,PATCH,BUILD

#define REQUIRED_VERSION 2.20

#ifdef COMPONENT_BEAUTIFIED
    #define COMPONENT_NAME QUOTE(Root's Battlefield Commander - COMPONENT_BEAUTIFIED)
#else
    #define COMPONENT_NAME QUOTE(Root's Battlefield Commander - COMPONENT)
#endif

#endif // BATCOM_SCRIPT_MOD_HPP
