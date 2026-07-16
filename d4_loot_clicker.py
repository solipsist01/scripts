#!/usr/bin/env python3

#pip3 install pynput --break-system-packages
#sudo apt install python3-tk python3-dev
import time
import threading

from pynput import keyboard
from pynput.mouse import Button, Controller


mouse = Controller()

clicking = False
right_click = False

pressed = set()


def click_loop():
    global clicking

    while True:
        if clicking:
            button = Button.right if right_click else Button.left

            mouse.press(button)
            time.sleep(0.01)
            mouse.release(button)

            time.sleep(0.04)  # ~20 clicks/sec
        else:
            time.sleep(0.01)


def on_press(key):
    global clicking, right_click

    pressed.add(key)

    if key == keyboard.Key.backspace:
        right_click = (
            keyboard.Key.ctrl_l in pressed or
            keyboard.Key.ctrl_r in pressed
        )

        clicking = True


def on_release(key):
    global clicking

    pressed.discard(key)

    if key == keyboard.Key.backspace:
        clicking = False


threading.Thread(target=click_loop, daemon=True).start()

print("D4 Clicker running")
print("Backspace = left click")
print("Ctrl + Backspace = right click")
print("CTRL+C to quit")

with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()