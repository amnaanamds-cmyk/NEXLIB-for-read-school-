# NexLib — School Library Management System

A single-window, fully offline desktop app for managing a school or college library — books, members, issue/return, OPAC, inventory, inter-library loans, acquisitions, serials, reports, and more. Any school can install it and set up its own profile on first launch; everything is stored locally, with no cloud account and no internet connection required.

## Download (Windows)

No Python installation needed — just download and run:

1. Go to the **[Releases](../../releases/latest)** page of this repository.
2. Download `NexLib.exe` from the latest release.
3. Double-click `NexLib.exe` to run it.

Windows may show a "Windows protected your PC" SmartScreen warning because the app isn't code-signed — click **More info → Run anyway**. This is normal for small open-source tools without a paid code-signing certificate.

Each install keeps its own local database at `%USERPROFILE%\NexLib\nexlib.db`, so copies on different computers never share or overwrite each other's data.

## First run

The first time you open NexLib it shows a one-time setup wizard:

1. Enter your school/college name, address, and daily fine rate.
2. Create the first administrator account (username + password).

After that, it goes straight to a login screen on every launch.

## Running from source instead

If you'd rather run it with Python (any OS):

```bash
pip install -r requirements.txt
python main.py
```

## Building the .exe yourself

On Windows, with Python installed:

```bat
build_exe.bat
```

This produces `dist\NexLib.exe`. A GitHub Actions workflow (`.github/workflows/build-exe.yml`) also builds this automatically on every push and publishes it to the Releases page whenever a `v*` tag is pushed.

## Features

Books catalog, member management (with ID cards, PINs, photos), issue/return with fines, OPAC public search kiosk, inventory audits, inter-library loan requests, acquisitions/purchase orders, serials & periodicals, PDF/Excel reports and analytics, barcode/QR tools, staff account management, automated local backups, and more — all offline.
