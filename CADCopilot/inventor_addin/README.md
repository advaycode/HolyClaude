# CADCopilot — dockable panel inside Inventor (.NET add-in)

This add-in puts the CADCopilot chat **inside Inventor** as a dockable pane. It
hosts a **WebView2** browser pointed at the local panel server
(`http://127.0.0.1:8750`), so it reuses the same Claude + CAD agent — you just get
it docked in Inventor instead of a separate browser window. The add-in also starts
the panel server for you (`launch_panel_embedded.bat`).

## What you need (one-time)
1. **.NET SDK** (8 or 9) — `winget install Microsoft.DotNet.SDK.9`. (This lets
   `dotnet build` target .NET Framework 4.8 via the reference-assemblies NuGet
   already listed in the csproj. Visual Studio Community works too — just open the
   `.csproj` and Build.)
2. **WebView2 Runtime** — preinstalled on Windows 11. If missing:
   `winget install Microsoft.EdgeWebView2Runtime`.
3. **Inventor interop** — the csproj points at
   `C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll`.
   Change `2027` → `2026` in `CadCopilotAddin.csproj` and `build.bat` if you target 2026.
4. **`ANTHROPIC_API_KEY`** set in your environment (the panel uses the Claude API).

## Build + install
Open an **Administrator** terminal (regasm registers the COM class in HKCR) and run:
```bat
cd C:\Users\advay\Obsidian\CADCopilot\inventor_addin
build.bat
```
That builds the DLL, copies it + `CadCopilot.addin` + WebView2 wrappers to
`%APPDATA%\Autodesk\Inventor 2027\Addins\CadCopilot\`, and registers it.

Then start Inventor. A **CADCopilot** pane docks on the right. If not:
- Tools ▸ **Add-Ins** → tick **CADCopilot** (Load on Startup).
- View ▸ User Interface ▸ **CADCopilot** to toggle the pane.

## Prefer not to compile? 
You don't have to — `launch_panel.bat` gives you the exact same agent in a normal
browser window. The add-in is only for the docked-inside-Inventor experience.

## How it works
`StandardAddInServer.cs` implements Inventor's `ApplicationAddInServer`. On
`Activate` it creates a `DockableWindow`, hosts a WinForms `WebView2` via
`AddChild(handle)`, starts the panel server, and navigates to the panel URL
(retrying while the server boots). The chat → Claude → CAD-tools → screenshots loop
all runs in the Python panel; the add-in is just the embedded window.

## Troubleshooting
- **Pane blank / "can't reach site":** the server didn't start — run
  `launch_panel_embedded.bat` manually and check for errors (usually a missing
  `ANTHROPIC_API_KEY` or Inventor not open).
- **`regasm` failed:** you weren't elevated — re-run `build.bat` as Administrator.
- **`dotnet build` can't find Autodesk.Inventor.Interop:** fix the HintPath/version
  in the csproj to match your installed Inventor.
- **Add-in not listed:** confirm `CadCopilot.addin` is in the Inventor `Addins`
  folder and the `ClassId` matches the `[Guid]` in the C#.
