@echo off
echo Starting Cloudflare Tunnel...
echo.
cloudflared tunnel --url http://localhost:5000
pause
