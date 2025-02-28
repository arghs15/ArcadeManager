@echo off
REM Get ROM name from first parameter
set ROM_NAME=%1

REM Launch MAME with the ROM
start /b "" "mame64nocfg.exe" %ROM_NAME%

REM Launch preview app with the same ROM and auto-close enabled
start "" pythonw "MAME Controls - New.pyw" --preview-only --game=%ROM_NAME% --screen=2 --auto-close