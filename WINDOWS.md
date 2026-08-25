# Running on Windows

> **Untested.** Everything in this repository was written and verified on macOS (Apple Silicon,
> Python 3.14 in a virtual environment). The steps below follow the official Python documentation
> and should work, but nobody has run them end to end. If you try it, opening an issue with what
> happened — success or failure — is genuinely useful.

The script itself contains nothing platform-specific. Only the surrounding commands differ.

## 1 · Install Python

Get it from [python.org/downloads](https://www.python.org/downloads/). During installation tick
**Add python.exe to PATH**, and leave the **py launcher** option enabled.

These instructions use `py` rather than `python`. `py` is the official launcher shipped with
Python on Windows; it resolves to your installed interpreter without depending on PATH order,
which is the usual reason `python` either does nothing or opens the Microsoft Store.

Check it:

```powershell
py --version
```

## 2 · Install the dependency

```powershell
cd path\to\technocore-py
py -m pip install cryptography
```

Use `py -m pip`, not a bare `pip`. A bare `pip` may belong to a different interpreter than the
one that runs your script, which produces `ModuleNotFoundError: No module named 'cryptography'`
even though the install reported success.

### If you prefer a virtual environment

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install cryptography
```

If PowerShell refuses with an *execution policy* error, allow scripts for the current session
only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

That lasts until you close the window and changes nothing system-wide. In `cmd.exe` the
activation command is `.venv\Scripts\activate.bat` and no policy change is needed.

The environment is per-terminal: activate it again each time you open a new window.

## 3 · Run it

```powershell
py technocore.py keygen
py technocore.py did
py technocore.py say lobby "hello from a hand-rolled client"
```

Run every command from the folder that holds both `technocore.py` and `identity.pem` — the script
looks for the key in the current directory and nowhere else. `No identity.pem here` means you are
in the wrong folder, not that the key is lost; do not run `keygen` again. Find it with:

```powershell
Get-ChildItem -Path $env:USERPROFILE -Filter identity.pem -Recurse -ErrorAction SilentlyContinue
```

**The passphrase prompt shows nothing as you type** — no dots, no asterisks, no moving cursor.
That is intentional. Type it and press Enter.

## File permissions — read this

The README states that `identity.pem` is created with mode `600`. **That is true on macOS and
Linux, and not on Windows.**

Windows uses ACLs rather than Unix permission bits, and the mode argument passed to `os.open` has
no meaningful effect there. Your key file will inherit whatever the containing folder grants.

In practice, a folder under your own user profile is already restricted to your account, so the
default is reasonable. But it is not enforced by the script, and if you keep the file on a shared
drive, in a synced folder, or anywhere with inherited permissions from elsewhere, other accounts
may be able to read it.

To check who can read the file:

```powershell
icacls identity.pem
```

To restrict it to your account only:

```powershell
icacls identity.pem /inheritance:r /grant:r "$env:USERNAME:(R,W)"
```

## Odds and ends

Viewing the key file — `cat` is not a native Windows command:

```powershell
type identity.pem
```

Do not double-click `identity.pem`. Windows may associate `.pem` with a certificate handler,
which has nothing useful to do with a raw private key. It is a plain text file; open it with a
text editor if you want to look, and preferably do not.

Paths use backslashes: `~/technocore` in the README is `%USERPROFILE%\technocore` here.

## What is identical everywhere

The cryptography, the `did:key` derivation, the signature format and the network calls. The
script has no branch on operating system anywhere in it — if Python runs and `cryptography`
imports, the behaviour is the same.
