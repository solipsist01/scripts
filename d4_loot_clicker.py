#!/usr/bin/env python3

# pip3 install pynput --break-system-packages
# sudo apt install python3-tk python3-dev xdotool

import time
import threading
import subprocess

from pynput import keyboard
from pynput.mouse import Button, Controller


mouse = Controller()
keyboard_controller = keyboard.Controller()

clicking = False
right_click = False

# New Shift + Backspace mode
shift_backspace = False

# Prevent xdotool's temporary modifier clearing from
# accidentally stopping Shift + Backspace mode.
typing_clan = False

pressed = set()


def press_enter():
    keyboard_controller.press(keyboard.Key.enter)
    keyboard_controller.release(keyboard.Key.enter)


def type_clan():
    global typing_clan

    typing_clan = True

    try:
        subprocess.run(
            [
                "xdotool",
                "key",
                "--clearmodifiers",
                "slash",
                "c",
                "l",
                "a",
                "n"
            ],
            check=False
        )
    finally:
        typing_clan = False


def click_loop():
    global clicking, right_click, shift_backspace

    while True:

        # ==========================================
        # SHIFT + BACKSPACE MODE
        # ==========================================
        if shift_backspace:

            # Enter
            press_enter()

            time.sleep(0.05)

            # /clan
            type_clan()

            # xdotool may have generated modifier events.
            # If Shift + Backspace mode was active before
            # typing, explicitly keep it active here.
            shift_held = (
                keyboard.Key.shift_l in pressed or
                keyboard.Key.shift_r in pressed
            )

            if shift_held:
                shift_backspace = True

            time.sleep(0.05)

            # Enter
            if shift_backspace:
                press_enter()

            time.sleep(0.1)

            # ======================================
            # CLICK + ENTER LOOP
            # ======================================
            while shift_backspace:

                # Left click
                mouse.click(Button.left)

                # Enter
                press_enter()

                time.sleep(0.05)

        # ==========================================
        # ORIGINAL BACKSPACE / CTRL+BACKSPACE MODE
        # ==========================================
        elif clicking:

            button = Button.right if right_click else Button.left

            mouse.press(button)
            time.sleep(0.01)
            mouse.release(button)

            time.sleep(0.04)

        else:
            time.sleep(0.01)


def on_press(key):
    global clicking, right_click, shift_backspace

    pressed.add(key)

    # ==========================================
    # BACKSPACE
    # ==========================================
    if key == keyboard.Key.backspace:

        shift_held = (
            keyboard.Key.shift_l in pressed or
            keyboard.Key.shift_r in pressed
        )

        if shift_held:

            # Shift + Backspace starts NEW mode
            shift_backspace = True

            # Disable normal clicking
            clicking = False

        else:

            # ORIGINAL BACKSPACE BEHAVIOR
            right_click = (
                keyboard.Key.ctrl_l in pressed or
                keyboard.Key.ctrl_r in pressed
            )

            clicking = True


def on_release(key):
    global clicking, right_click, shift_backspace

    pressed.discard(key)

    # ==========================================
    # BACKSPACE RELEASE
    # ==========================================
    if key == keyboard.Key.backspace:

        # IMPORTANT:
        # Backspace release does NOT stop the
        # Shift + Backspace mode.
        clicking = False

    # ==========================================
    # SHIFT RELEASE
    # ==========================================
    elif key in (
        keyboard.Key.shift_l,
        keyboard.Key.shift_r
    ):

        # This is the actual stop condition.
        shift_backspace = False

        clicking = False


# Start click thread
threading.Thread(
    target=click_loop,
    daemon=True
).start()


print("D4 Clicker running")
print()
print("Backspace = left click")
print("Ctrl + Backspace = right click")
print()
print("Shift + Backspace =")
print("    Enter")
print("    /clan")
print("    Enter")
print("    Left click -> Enter -> repeat")
print("    until Shift is released")
print()
print("CTRL+C to quit")


with keyboard.Listener(
    on_press=on_press,
    on_release=on_release
) as listener:
    listener.join()