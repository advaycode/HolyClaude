CADCopilot - GPU host (the PC with the RTX 4070)
================================================

You're lending your GPU so Advay's Inventor copilot runs fast.
You and Advay are on DIFFERENT networks, so you BOTH need Tailscale
(it's a free, secure VPN that lets the two PCs talk to each other).

ONE-TIME SETUP:
  1. Install Ollama:     https://ollama.com/download   (open it once)
  2. Install Tailscale:  https://tailscale.com/download
  3. Sign in to Tailscale with the SAME account Advay uses
     (he'll tell you the login, or invite you). Both PCs must be on
     the same Tailscale account so they can see each other.

EVERY TIME YOU WANT TO HELP HIM BUILD:
  1. Make sure Tailscale is running (icon in the system tray).
  2. Double-click  start.bat
  3. Click "Yes" on the admin prompt (only needed for the firewall).
  4. When it says READY, send Advay the "Tailscale" address it prints
     (looks like  http://100.x.x.x:11434 ).
  5. Leave the minimized "Ollama Server" window OPEN while he works.
     Closing it stops the server.

NOTES:
  - First run downloads the model (~9 GB) once; after that it's instant.
  - If start.bat says "Tailscale NOT connected", open Tailscale / run
    "tailscale up", sign in, then run start.bat again.
  - The "Same-Wi-Fi only" address it also prints won't work for Advay
    since you're on different networks - use the Tailscale one.
