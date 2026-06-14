using System;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Inventor;
using Microsoft.Web.WebView2.WinForms;

[assembly: ComVisible(true)]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace CadCopilot
{
    // ClassId/ClientId GUID must match CadCopilot.addin and the HKCU registration.
    [Guid("8F3C9A21-7B4D-4E2A-9C11-2A6E5D3F1B07")]
    [ComVisible(true)]
    [ClassInterface(ClassInterfaceType.None)]
    public class StandardAddInServer : ApplicationAddInServer
    {
        private const string ClientId = "{8F3C9A21-7B4D-4E2A-9C11-2A6E5D3F1B07}";
        private const string PanelUrl = "http://127.0.0.1:8750/";
        private const string LauncherBat = @"C:\Users\advay\Obsidian\CADCopilot\launch_panel_embedded.bat";

        private Inventor.Application _app;
        private DockableWindow _dock;
        private UserControl _host;
        private WebView2 _web;

        public void Activate(ApplicationAddInSite addInSiteObject, bool firstTime)
        {
            _app = addInSiteObject.Application;
            StartPanelServer();

            UserInterfaceManager uim = _app.UserInterfaceManager;
            _dock = uim.DockableWindows.Add(ClientId, "CadCopilotPanel", "CADCopilot");
            _dock.ShowVisibilityCheckBox = true;

            _host = new UserControl();
            _web = new WebView2();
            _web.Dock = DockStyle.Fill;
            _host.Controls.Add(_web);
            _host.CreateControl();
            _dock.AddChild(_host.Handle.ToInt32());
            _dock.DockingState = DockingStateEnum.kDockRight;
            _dock.Visible = true;

            // WebView2's default user-data folder is the host .exe dir (Program Files,
            // not writable) — point it at a writable per-user folder or init fails.
            string udf = System.IO.Path.Combine(
                System.Environment.GetFolderPath(System.Environment.SpecialFolder.LocalApplicationData),
                "CadCopilot", "WebView2");
            try { System.IO.Directory.CreateDirectory(udf); } catch { }
            CoreWebView2CreationProperties props = new CoreWebView2CreationProperties();
            props.UserDataFolder = udf;
            _web.CreationProperties = props;

            _web.CoreWebView2InitializationCompleted += delegate (object s, Microsoft.Web.WebView2.Core.CoreWebView2InitializationCompletedEventArgs e)
            {
                if (e.IsSuccess) NavigateWithRetry(0);
            };
            _web.EnsureCoreWebView2Async(null);
        }

        private void NavigateWithRetry(int attempt)
        {
            try { _web.CoreWebView2.Navigate(PanelUrl); }
            catch
            {
                if (attempt < 12)
                {
                    Timer t = new Timer();
                    t.Interval = 800;
                    t.Tick += delegate (object s, EventArgs e) { t.Stop(); t.Dispose(); NavigateWithRetry(attempt + 1); };
                    t.Start();
                }
            }
        }

        private void StartPanelServer()
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = LauncherBat;
                psi.UseShellExecute = true;
                psi.WindowStyle = ProcessWindowStyle.Minimized;
                Process.Start(psi);
            }
            catch { }
        }

        public void Deactivate()
        {
            try { if (_web != null) _web.Dispose(); } catch { }
            try { if (_host != null) _host.Dispose(); } catch { }
            try { if (_dock != null) _dock.Delete(); } catch { }
            _web = null; _host = null; _dock = null;
            if (_app != null) { Marshal.ReleaseComObject(_app); _app = null; }
            GC.Collect();
            GC.WaitForPendingFinalizers();
        }

        public void ExecuteCommand(int commandID) { }
        public object Automation { get { return null; } }
    }
}
