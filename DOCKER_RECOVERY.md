# 🚨 CRITICAL: C: Drive Full - Docker Crashed

Your C: drive has **0 bytes free**. This has caused Docker to crash and is preventing me from updating your documentation files.

## Immediate Steps to Fix

1.  **Free ~2GB on C: Drive Manually**
    - Empty your Recycle Bin.
    - Delete temporary files (`%TEMP%`).
    - Delete `C:\Users\Mati\.npm` (buffer) if safe.
    - Uninstall unused apps.

2.  **Restart Docker Desktop**
    - Once you have a little space, restart Docker Desktop.

3.  **Move Docker Data to F: (PERMANENT FIX)**
    - Your F: drive has **1.2 TB free**. You MUST move Docker there.
    - Open Docker Desktop Dashboard.
    - Go to **Settings (Gear Icon) -> Resources -> Disk image location**.
    - Click **Browse** and select a folder on F: (e.g., `F:\DockerData`).
    - Click **Apply & Restart**.

## If Docker Won't Start (Manual Move)

Since you only see `docker-desktop` (and not `docker-desktop-data`), follow these steps:

1.  Open PowerShell as Administrator.
2.  Run: `wsl --shutdown`
3.  **Check if `docker-desktop-data` exists**:
    Run `wsl --list`
    - If you _only_ see `docker-desktop`, proceed with that name.
    - If you see both, do these steps for _both_ (changing the name accordingly).

4.  **Export (Move Data to F:)**:
    ```powershell
    wsl --export docker-desktop "F:\docker-desktop.tar"
    ```
5.  **Unregister (Delete from C:)**:
    - **THIS WILL FREE SPACE IMMEDIATELY.**
    ```powershell
    wsl --unregister docker-desktop
    ```
6.  **Import (Restore to F:)**:
    ```powershell
    mkdir "F:\DockerWSL"
    wsl --import docker-desktop "F:\DockerWSL" "F:\docker-desktop.tar" --version 2
    ```
7.  **Start Docker Desktop**.

### ☢️ The "Nuclear" Option (If Export Fails)

If `wsl --export` fails (because C: is too full to even think), you can just **delete** the Docker distro to verify space. You will lose your existing built images (not your code).

1.  `wsl --unregister docker-desktop`
2.  Uninstall Docker Desktop.
3.  Clean up `C:\Users\Mati\AppData\Local\Docker` (delete it).
4.  Reinstall Docker Desktop.
5.  **IMMEDIATELY** upon install (before starting), configured it to use F: drive if possible, or repeat the move steps above _before_ pulling heavy images.
