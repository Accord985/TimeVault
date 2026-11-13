"""Build a Windows executable that displays a newly generated Screen Time code.

Configure SCREEN_TIME_CODE_EXE in the repository's .env, install the optional
build dependency with `pip install -r requirements-build.txt`, then run this
script. The generated code is embedded in the executable and is not printed.
"""

from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from phone_harness import config  # noqa: E402


def _same_executable_location(actual: str | Path, expected: str | Path) -> bool:
    """Compare file identity first, with canonical paths as a fallback."""
    try:
        return Path(actual).samefile(expected)
    except (OSError, ValueError):
        def canonical(path: str | Path) -> str:
            return os.path.normcase(os.path.abspath(os.path.realpath(path)))

        return canonical(actual) == canonical(expected)


def configured_output_path() -> Path:
    configured_path = config.get("SCREEN_TIME_CODE_EXE")
    if not configured_path:
        configured_path = Path.cwd() / "RevealCode.exe"
    output_path = Path(configured_path).expanduser()
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    if output_path.suffix.lower() != ".exe":
        raise ValueError("SCREEN_TIME_CODE_EXE must end in .exe.")
    return output_path


def build_screen_time_code_viewer(
    code: str,
    output_path: str | Path,
    *,
    expected_location: str | Path | None = None,
    announce: bool = False,
) -> Path:
    """Build a new viewer at `output_path` without overwriting an existing file."""
    if not isinstance(code, str) or len(code) != 4 or not code.isdigit():
        raise ValueError("Screen Time code must be exactly four digits.")
    if sys.platform != "win32":
        raise RuntimeError("This script builds a Windows .exe and must run on Windows.")

    output_path = Path(output_path).expanduser().resolve()
    if output_path.suffix.lower() != ".exe":
        raise ValueError("The Screen Time code viewer output path must end in .exe.")
    expected_location = Path(expected_location or output_path).expanduser().resolve()
    if expected_location.suffix.lower() != ".exe":
        raise ValueError("The expected Screen Time code viewer location must end in .exe.")
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing executable: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if announce:
        print("Creating Screen time code viewer...")

    with tempfile.TemporaryDirectory(prefix="sidetap-code-build-") as temp_dir:
        temp = Path(temp_dir)
        app_source = temp / "screen_time_code.py"
        app_source.write_text(
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            "import tkinter as tk\n"
            "from tkinter import messagebox\n"
            f"{inspect.getsource(_same_executable_location)}\n"
            f"expected = {str(expected_location)!r}\n"
            "actual = sys.executable\n"
            "if not _same_executable_location(actual, expected):\n"
            "    root = tk.Tk()\n"
            "    root.withdraw()\n"
            "    messagebox.showerror(\n"
            "        'Screen Time Code',\n"
            "        f'This executable must be run from its configured location.\\nExpected: {expected}\\nActual: {actual}',\n"
            "    )\n"
            "    root.destroy()\n"
            "    raise SystemExit(1)\n"
            "root = tk.Tk()\n"
            "root.title('Screen Time Code')\n"
            "root.resizable(False, False)\n"
            "root.attributes('-topmost', True)\n"
            "status = tk.Label(root, font=('Segoe UI', 14))\n"
            "status.pack(padx=32, pady=(24, 8))\n"
            "code_label = tk.Label(root, text='', font=('Segoe UI', 36, 'bold'))\n"
            "code_label.pack(padx=32, pady=(0, 24))\n"
            "def update_countdown(remaining=7):\n"
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
            raise RuntimeError("Failed to create Screen time code viewer.") from None
        shutil.copy2(dist_dir / "ScreenTimeCode.exe", output_path)
    return output_path


def main() -> int:
    try:
        output_path = configured_output_path()
        if config.get("SCREEN_TIME_CODE_EXE") and output_path.exists():
            raise FileExistsError(f"Refusing to overwrite existing executable: {output_path}")
        if not config.get("SCREEN_TIME_CODE_EXE"):
            print("SCREEN_TIME_CODE_EXE not configured; using default: ", output_path)
        from secrets import randbelow

        code = f"{randbelow(10_000):04d}"
        output_path = build_screen_time_code_viewer(code, output_path, announce=True)
    except (FileExistsError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Created Screen Time code viewer: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
