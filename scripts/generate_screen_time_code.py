"""Build a Windows executable that displays a newly generated Screen Time code.

Configure SCREEN_TIME_CODE_EXE in the repository's .env, install the optional
build dependency with `pip install -r requirements-build.txt`, then run this
script. The generated code is embedded in the executable and is not printed.
"""

from __future__ import annotations

import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from phone_harness import config  # noqa: E402


def main() -> int:
    configured_path = config.get("SCREEN_TIME_CODE_EXE")
    if not configured_path:
        configured_path = Path.cwd() / "RevealCode.exe"
        print("SCREEN_TIME_CODE_EXE not configured; using default: ", configured_path)

    output_path = Path(configured_path).expanduser()
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    if output_path.suffix.lower() != ".exe":
        print("SCREEN_TIME_CODE_EXE must end in .exe.", file=sys.stderr)
        return 2

    if sys.platform != "win32":
        print("This script builds a Windows .exe and must run on Windows.", file=sys.stderr)
        return 2

    code = f"{secrets.randbelow(10_000):04d}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print("Creating Screen time code viewer...")

    with tempfile.TemporaryDirectory(prefix="sidetap-code-build-") as temp_dir:
        temp = Path(temp_dir)
        app_source = temp / "screen_time_code.py"
        app_source.write_text(
            "import tkinter as tk\n"
            "root = tk.Tk()\n"
            "root.title('Screen Time Code')\n"
            "root.resizable(False, False)\n"
            "root.attributes('-topmost', True)\n"
            "status = tk.Label(root, font=('Segoe UI', 14))\n"
            "status.pack(padx=32, pady=(24, 8))\n"
            "code_label = tk.Label(root, text='', font=('Segoe UI', 36, 'bold'))\n"
            "code_label.pack(padx=32, pady=(0, 24))\n"
            "def update_countdown(remaining=15):\n"
            "    if remaining <= 0:\n"
            "        status.config(text='Your Screen Time code')\n"
            f"        code_label.config(text={code!r})\n"
            "        return\n"
            "    status.config(text=f'Code appears in {remaining} seconds')\n"
            "    root.after(1000, lambda: update_countdown(remaining - 1))\n"
            "update_countdown()\n"
            "root.mainloop()\n",
            encoding="utf-8",
        )
        build_dir = temp / "build"
        dist_dir = temp / "dist"
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "PyInstaller",
                    "--noconfirm",
                    "--clean",
                    "--onefile",
                    "--windowed",
                    "--name",
                    "ScreenTimeCode",
                    "--workpath",
                    str(build_dir),
                    "--specpath",
                    str(temp),
                    "--distpath",
                    str(dist_dir),
                    str(app_source),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            print("Failed to create Screen time code viewer.", file=sys.stderr)
            return 1
        shutil.copy2(dist_dir / "ScreenTimeCode.exe", output_path)

    print(f"Created Screen Time code viewer: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
