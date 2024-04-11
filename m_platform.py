import platform, threading

PLATFORM = platform.system()
output_change_listener = None
sig = False


if PLATFORM == "Windows":
    deviceEnumerator = None
    HWIND = None
    TIMER_ID = None
    import comtypes, win32gui, win32con, timer
    from pycaw.constants import CLSID_MMDeviceEnumerator
    from pycaw.pycaw import DEVICE_STATE, AudioUtilities, EDataFlow, IMMDeviceEnumerator

    # -----------------PLATFORM SPECIFIC HELPER FUNCTIONS-----------------------
    def ping_timer(id, time):
        global HWIND, TIMER_ID
        win32gui.PostMessage(HWIND, win32con.WM_TIMER, TIMER_ID, 0)

    def resize_callback(oldWndProc, app_callback_resize, hWnd, message, wParam, lParam):
        global HWIND, TIMER_ID
        if message == win32con.WM_ENTERSIZEMOVE:
            TIMER_ID = timer.set_timer(5, ping_timer)
        elif message == win32con.WM_EXITSIZEMOVE:
            timer.kill_timer(TIMER_ID)  # Stop the timer

        elif (message == win32con.WM_TIMER and wParam == TIMER_ID) or message in (
            win32con.WM_SIZE,
            win32con.WM_MOVE,
        ):
            app_callback_resize()
        win32gui.RedrawWindow(hWnd, None, None, win32con.RDW_INVALIDATE | win32con.RDW_ERASE)
        return win32gui.CallWindowProc(oldWndProc, hWnd, message, wParam, lParam)

    # -----------------PLATFORM SPECIFIC HELPER FUNCTIONS-----------------------
    def init_resize_function(callback_function):
        global HWIND
        HWIND = win32gui.GetForegroundWindow()
        oldWndProc = win32gui.SetWindowLong(
            HWIND,
            win32con.GWL_WNDPROC,
            lambda *args: resize_callback(oldWndProc, callback_function, *args),
        )

    def resize(event, resize_callback, *args):
        pass

    def init_platform_audio(callback_function):
        global deviceEnumerator, output_change_listener
        deviceEnumerator = comtypes.CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_ALL)
        output_change_listener = threading.Thread(target=callback_function, daemon=True)
        output_change_listener.start()

    def get_default_output_device():
        global deviceEnumerator
        default_device = AudioUtilities.CreateDevice(
            deviceEnumerator.GetDefaultAudioEndpoint(EDataFlow.eRender.value, DEVICE_STATE.ACTIVE.value)
        )
        return (default_device.FriendlyName, default_device.id)

    def uninit_platform_audio():
        comtypes.CoUninitialize()

else:

    def init_resize_function(callback_function):
        pass

    def resize_callback():
        pass

    def resize(condition: bool, resize_callback: function, *args):
        if condition:
            resize_callback(args)

    def init_platform_audio(callback_function):
        pass

    def get_default_output_device(self):
        pass

    def uninit_platform_audio():
        pass

    pass
