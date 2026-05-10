@echo off
netsh interface ip set address name="以太网" dhcp
netsh interface ip set dns name="以太网" dhcp
echo.
echo Adapter "以太网" restored to DHCP.
pause
