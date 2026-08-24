#!/usr/bin/env python3

# Install:
#     pip install pynput
#
# Linux may additionally need:
#     sudo apt install python3-tk python3-dev
#
# Windows:
#     pip install pynput

import time
import threading

from pynput import keyboard
from pynput.mouse import Button, Controller


mouse = Controller()
keyboard_controller = keyboard.Controller()

clicking = False
right_click = False

# Shift + Backspace mode
shift_backspace = False

# Keys currently physically pressed according to pynput
pressed = set()

# Prevent multiple Shift+Backspace activations while the
# backspace key is held down.
shift_backspace_started = False

# Lock keyboard injection so the click thread cannot
# interfere with type_clan().
keyboard_lock = threading.Lock()


def is_shift_held():
    return (
        keyboard.Key.shift_l in pressed
        or keyboard.Key.shift_r in pressed
    )


def is_ctrl_held():
    return (
        keyboard.Key.ctrl_l in pressed
        or keyboard.Key.ctrl_r in pressed
    )


def press_enter():
    keyboard_controller.press(keyboard.Key.enter)
    keyboard_controller.release(keyboard.Key.enter)


def type_clan():
    """
    Type /clan even when the user is physically holding Shift.

    Normally:

        Shift + /  -> ?

    So simply typing "/" while Shift is held can result in:

        ?CLAN

    We temporarily release any Shift keys, type /clan, and
    then restore Shift so the Shift+Backspace mode continues.
    """

    with keyboard_lock:

        shift_l_was_held = keyboard.Key.shift_l in pressed
        shift_r_was_held = keyboard.Key.shift_r in pressed

        # Temporarily release Shift.
        #
        # This is the cross-platform equivalent of xdotool's
        # --clearmodifiers for the specific modifier we need
        # to neutralize.
        if shift_l_was_held:
            keyboard_controller.release(keyboard.Key.shift_l)

        if shift_r_was_held:
            keyboard_controller.release(keyboard.Key.shift_r)

        try:
            # Now "/" is really "/" rather than "?"
            # and the letters are lowercase.
            keyboard_controller.type("/clan")

        finally:
            # Restore Shift so the user's physical
            # Shift+Backspace operation can continue.
            if shift_l_was_held:
                keyboard_controller.press(keyboard.Key.shift_l)

            if shift_r_was_held:
                keyboard_controller.press(keyboard.Key.shift_r)


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
    global clicking
    global right_click
    global shift_backspace
    global shift_backspace_started

    pressed.add(key)

    # ==========================================
    # BACKSPACE
    # ==========================================
    if key == keyboard.Key.backspace:

        shift_held = is_shift_held()

        if shift_held:

            # Don't restart the mode if Backspace generates
            # repeated key events while it remains held.
            if not shift_backspace_started:

                shift_backspace_started = True
                shift_backspace = True

                # Disable normal clicking
                clicking = False

        else:

            # ORIGINAL BACKSPACE BEHAVIOR
            right_click = is_ctrl_held()

            clicking = True


def on_release(key):
    global clicking
    global right_click
    global shift_backspace
    global shift_backspace_started

    pressed.discard(key)

    # ==========================================
    # BACKSPACE RELEASE
    # ==========================================
    if key == keyboard.Key.backspace:

        # IMPORTANT:
        # Backspace release does NOT stop
        # Shift + Backspace mode.
        clicking = False
        right_click = False

    # ==========================================
    # SHIFT RELEASE
    # ==========================================
    elif key in (
        keyboard.Key.shift_l,
        keyboard.Key.shift_r
    ):

        # Releasing Shift is the stop condition.
        shift_backspace = False
        shift_backspace_started = False

        clicking = False
        right_click = False


# ==============================================
# START CLICK THREAD
# ==============================================

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