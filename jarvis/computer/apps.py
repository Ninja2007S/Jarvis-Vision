from __future__ import annotations

import subprocess


APPROVED_APPLICATIONS = {
    "notepad": [
        "notepad.exe"
    ],

    "calculator": [
        "calc.exe"
    ],

    "explorer": [
        "explorer.exe"
    ],
}


def open_application(
    name: str,
) -> bool:

    name = name.lower().strip()

    command = APPROVED_APPLICATIONS.get(
        name
    )

    if not command:
        return False

    subprocess.Popen(
        command,
        shell=False,
    )

    return True