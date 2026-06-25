using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows.Forms;

internal static class CardOpsLauncher
{
    private static int Main(string[] args)
    {
        try
        {
            string repoRoot = FindRepoRoot();
            string script = Path.Combine(repoRoot, "tools", "CardOps-Launcher.ps1");
            if (!File.Exists(script))
            {
                MessageBox.Show(
                    "CardOps launcher script was not found:\n\n" + script,
                    "CardOps",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                return 1;
            }

            string powerShell = FindPowerShell();
            string arguments = "-NoProfile -ExecutionPolicy Bypass -STA -File "
                + Quote(script)
                + BuildForwardedArguments(args);

            var startInfo = new ProcessStartInfo
            {
                FileName = powerShell,
                Arguments = arguments,
                WorkingDirectory = repoRoot,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };

            Process.Start(startInfo);
            return 0;
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "CardOps", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static string FindRepoRoot()
    {
        string current = AppDomain.CurrentDomain.BaseDirectory;
        for (var directory = new DirectoryInfo(current); directory != null; directory = directory.Parent)
        {
            if (File.Exists(Path.Combine(directory.FullName, "tools", "CardOps-Launcher.ps1")))
            {
                return directory.FullName;
            }
        }

        string fallback = @"D:\WORK\GitRepos\PERSONAL\cardops";
        if (File.Exists(Path.Combine(fallback, "tools", "CardOps-Launcher.ps1")))
        {
            return fallback;
        }

        return current;
    }

    private static string FindPowerShell()
    {
        string[] candidates =
        {
            @"C:\Program Files\PowerShell\7\pwsh.exe",
            @"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        };

        foreach (string candidate in candidates)
        {
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        throw new FileNotFoundException("PowerShell 7 or Windows PowerShell was not found.");
    }

    private static string BuildForwardedArguments(string[] args)
    {
        if (args == null || args.Length == 0)
        {
            return string.Empty;
        }

        return " " + string.Join(" ", args.Select(Quote).ToArray());
    }

    private static string Quote(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }
}
