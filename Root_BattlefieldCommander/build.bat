@echo off
setlocal enabledelayedexpansion

:: BATCOM Build Script

echo ============================================
echo            BATCOM Build Script
echo ============================================

:: Clean up existing build output
echo.
echo --------------------------------------------
echo  Step 1: Cleanup
echo --------------------------------------------
if exist ".hemttout" (
    echo Cleaning up existing .hemttout folder...
    rmdir /S /Q ".hemttout"
    echo Cleanup complete!
) else (
    echo No existing build to clean.
)

:: Run HEMTT
echo.
echo --------------------------------------------
echo  Step 2: HEMTT Build
echo --------------------------------------------
echo Running HEMTT build...
hemtt build

if %ERRORLEVEL% neq 0 (
    echo HEMTT build failed!
    exit /b %ERRORLEVEL%
)

:: Copy Pythia folder contents to output root
echo.
echo --------------------------------------------
echo  Step 3: Copy Pythia
echo --------------------------------------------
if exist "pythia" (
    echo Copying Pythia built files to the build directory...
    xcopy /E /I /Y "pythia\*" ".hemttout\build\" >nul
    echo Pythia copied successfully!
) else (
    echo Warning: Pythia folder not found, skipping copy!
)

:: Rename build folder to @batcom
echo.
echo --------------------------------------------
echo  Step 4: Rename Output
echo --------------------------------------------
if exist ".hemttout\build" (
    echo Renaming build folder to @batcom...
    ren ".hemttout\build" "@batcom"
    echo Rename complete!
)


:: Remove any __pycache__ folders if present
echo.
echo --------------------------------------------
echo  Step 5: Remove __pycache__
echo --------------------------------------------
for /d /r ".hemttout" %%D in (__pycache__) do (
    echo Deleting %%D
    rmdir /S /Q "%%D"
)


echo.
echo ============================================
echo            Build complete!
echo ============================================
