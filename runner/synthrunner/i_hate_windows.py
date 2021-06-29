from ctypes import WINFUNCTYPE, windll
from ctypes.wintypes import BOOL, DWORD
import keyboard
import os
import sys
import tkinter

import win32con
import win32gui
import win32process


kernel32 = windll.LoadLibrary("kernel32")
PHANDLER_ROUTINE = WINFUNCTYPE(BOOL, DWORD)
SetConsoleCtrlHandler = kernel32.SetConsoleCtrlHandler
SetConsoleCtrlHandler.argtypes = (PHANDLER_ROUTINE, BOOL)
SetConsoleCtrlHandler.restype = BOOL

CTRL_C_EVENT = 0


@PHANDLER_ROUTINE
def console_handler(ctrl_type):
    if ctrl_type == CTRL_C_EVENT:
        sys.exit(-1)
    return False


def suicide():
    # sys.exit() doesn't work with keyboard for unknown reasons
    os.kill(os.getpid(), 9)

def exit_on_ctrl_c():
    SetConsoleCtrlHandler(console_handler, True)

def exit_on_ctrl_shift_c():
    keyboard.add_hotkey('ctrl+shift+c', suicide)


def disable_tkinter_window():
    root = tkinter.Tk()
    root.geometry("0x0")
    root.overrideredirect(1)
    root.after(30, lambda: root.withdraw())


def make_windows_usable():
    exit_on_ctrl_shift_c()
    exit_on_ctrl_c()
    disable_tkinter_window()


def minimize_windows_for_pid(pid):
    print(pid)

    def minimize(hwnd, *args):
        if win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

    win32gui.EnumWindows(minimize, None)
