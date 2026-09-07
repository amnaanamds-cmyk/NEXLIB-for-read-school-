import os
import sys

def create_shortcut():
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        print("Required libraries missing. Installing win32com and winshell...")
        os.system('pip install winshell pypiwin32')
        import winshell
        from win32com.client import Dispatch

    desktop = winshell.desktop()
    path = os.path.join(desktop, "NexLib.lnk")
    target = sys.executable.replace("python.exe", "pythonw.exe")
    wdir = os.getcwd()
    icon = os.path.join(wdir, "assets", "nexlib.ico")
    arguments = os.path.join(wdir, "launch_app.pyw")

    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = target
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = wdir
    shortcut.IconLocation = icon
    shortcut.save()

    print(f"✅ Shortcut created on Desktop: {path}")

if __name__ == "__main__":
    create_shortcut()
