"""Where a gesture becomes a real action on your PC.

One function per verb, on purpose: remapping a gesture later means
changing which function app.py calls, never touching this file. Everything
here goes through pyautogui — free, no account, no server.

Window-management and desktop shortcuts differ by OS, so this detects
`platform.system()` once and picks the right keys. macOS also requires
granting your terminal (or Python) Accessibility permission in System
Settings before pyautogui can move the mouse at all; Linux needs an X11
session — Wayland blocks synthetic input for most compositors.
"""

from __future__ import annotations

import logging
import platform

import pyautogui

log = logging.getLogger("jarvis.hands.actions")

# Drag your physical mouse to any screen corner at any moment to kill
# pyautogui instantly — this stays on deliberately as the emergency stop.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0  # the webcam loop already paces itself at frame rate

OS = platform.system()  # "Windows", "Darwin", "Linux"
SCREEN_W, SCREEN_H = pyautogui.size()


def move_cursor(x: float, y: float) -> None:
    """x, y are normalized [0,1]. No easing here — the caller (mouse.py)
    already smoothed the position before it reaches this function."""
    pyautogui.moveTo(x * SCREEN_W, y * SCREEN_H)


def mouse_down() -> None:
    pyautogui.mouseDown()


def mouse_up() -> None:
    pyautogui.mouseUp()


def scroll(amount: int) -> None:
    """Positive scrolls up, negative scrolls down — matches pyautogui's
    own convention."""
    if amount:
        pyautogui.scroll(amount)


def switch_window(forward: bool = True) -> None:
    """One step of app switching. Windows/Linux: Alt+Tab. macOS: Cmd+Tab."""
    if OS == "Darwin":
        keys = ("command", "tab") if forward else ("command", "shift", "tab")
    else:
        keys = ("alt", "tab") if forward else ("alt", "shift", "tab")
    pyautogui.hotkey(*keys)
    log.info("switch_window forward=%s", forward)


def task_view() -> None:
    """All-windows overview: Windows Task View, macOS Mission Control.
    Linux varies by desktop environment — Super+Tab is common but not
    universal; adjust here if yours differs."""
    if OS == "Darwin":
        pyautogui.hotkey("ctrl", "up")
    elif OS == "Windows":
        pyautogui.hotkey("win", "tab")
    else:
        pyautogui.hotkey("super", "tab")
    log.info("task_view")


def show_desktop() -> None:
    """Windows: Show Desktop (reliable). macOS/Linux shortcuts vary by
    version and settings — check your own if this doesn't respond."""
    if OS == "Darwin":
        pyautogui.hotkey("fn", "f11")
    elif OS == "Windows":
        pyautogui.hotkey("win", "d")
    else:
        pyautogui.hotkey("super", "d")
    log.info("show_desktop")
