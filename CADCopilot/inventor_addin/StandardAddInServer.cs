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

        private static string LogDir()
        {
            return System.IO.Path.Combine(
                System.Environment.GetFolderPath(System.Environment.SpecialFolder.LocalApplicationData),
                "CadCopilot");
        }

        private static void Log(string msg)
        {
            try
            {
                string dir = LogDir();
                System.IO.Directory.CreateDirectory(dir);
                System.IO.File.AppendAllText(System.IO.Path.Combine(dir, "addin.log"),
                    System.DateTime.Now.ToString("HH:mm:ss.fff") + "  " + msg + "\r\n");
            }
            catch { }
        }

        public void Activate(ApplicationAddInSite addInSiteObject, bool firstTime)
        {
            Log("=== Activate start (firstTime=" + firstTime + ") asm=" + Assembly.GetExecutingAssembly().Location);
            AppDomain.CurrentDomain.UnhandledException += delegate (object s, UnhandledExceptionEventArgs e)
            { Log("UNHANDLED: " + e.ExceptionObject); };
            System.Threading.Tasks.TaskScheduler.UnobservedTaskException += delegate (object s, System.Threading.Tasks.UnobservedTaskExceptionEventArgs e)
            { Log("UNOBSERVED TASK: " + e.Exception); e.SetObserved(); };

            _app = addInSiteObject.Application;
            try { StartPanelServer(); Log("panel server launch requested"); }
            catch (Exception ex) { Log("StartPanelServer threw: " + ex); }

            try
            {
                UserInterfaceManager uim = _app.UserInterfaceManager;
                _dock = uim.DockableWindows.Add(ClientId, "CadCopilotPanel", "CADCopilot");
                Log("dock created");
                _dock.ShowVisibilityCheckBox = true;
                try { _dock.SetMinimumSize(480, 360); Log("min size set"); }
                catch (Exception ex) { Log("SetMinimumSize threw: " + ex.Message); }

                string udf = System.IO.Path.Combine(LogDir(), "WebView2");
                try { System.IO.Directory.CreateDirectory(udf); } catch { }

                _host = new UserControl();
                _web = new WebView2();
                CoreWebView2CreationProperties props = new CoreWebView2CreationProperties();
                props.UserDataFolder = udf;
                _web.CreationProperties = props;
                _web.Dock = DockStyle.Fill;
                _host.Controls.Add(_web);
                _host.CreateControl();
                Log("host created, handle=" + _host.Handle.ToInt64());

                _dock.AddChild(_host.Handle.ToInt64());
                Log("AddChild done");
                _dock.DockingState = DockingStateEnum.kDockRight;
                _dock.Visible = true;
                Log("dock visible=" + _dock.Visible);

                _web.CoreWebView2InitializationCompleted += delegate (object s, Microsoft.Web.WebView2.Core.CoreWebView2InitializationCompletedEventArgs e)
                {
                    Log("WebView2 init completed, success=" + e.IsSuccess + (e.IsSuccess ? "" : " err=" + e.InitializationException));
                    if (e.IsSuccess) NavigateWithRetry(0);
                };
                _web.EnsureCoreWebView2Async(null);
                Log("EnsureCoreWebView2Async called -- Activate returning");
            }
            catch (Exception ex)
            {
                Log("ACTIVATE EXCEPTION: " + ex);
                try { MessageBox.Show(ex.ToString(), "CADCopilot add-in error", MessageBoxButtons.OK, MessageBoxIcon.Error); } catch { }
            }
        }

        private void NavigateWithRetry(int attempt)
        {
            try { _web.CoreWebView2.Navigate(PanelUrl); Log("navigated (attempt " + attempt + ")"); }
            catch (Exception ex)
            {
                Log("navigate attempt " + attempt + " failed: " + ex.Message);
                if (attempt < 15)
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
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = LauncherBat;
            psi.UseShellExecute = true;
            psi.WindowStyle = ProcessWindowStyle.Minimized;
            Process.Start(psi);
        }

        public void Deactivate()
        {
            Log("=== Deactivate called ===");
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
