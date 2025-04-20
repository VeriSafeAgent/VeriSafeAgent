import re
import subprocess
from utils_.utils_ import log


try:
    from shlex import quote # Python 3
except ImportError:
    from pipes import quote # Python 2

class ADB():
    """
    interface of ADB
    send adb commands via this, see:
    http://developer.android.com/tools/help/adb.html
    """
    UP = 0
    DOWN = 1
    DOWN_AND_UP = 2
    def __init__(self, device: str = ""):
        if device:
            self.cmd_prefix = ['adb', "-s", device]
        else:
            self.cmd_prefix = ['adb']

    def shell(self, extra_args):
        """
        run an `adb shell` command
        @param extra_args:
        @return: output of adb shell command
        """
        if isinstance(extra_args, str) or isinstance(extra_args, str):
            extra_args = extra_args.split()
        if not isinstance(extra_args, list):
            msg = "invalid arguments: %s\nshould be list or str, %s given" % (extra_args, type(extra_args))
            log(msg, "yellow")

        shell_extra_args = ['shell'] + [ quote(arg) for arg in extra_args ]
        return self.run_cmd(shell_extra_args)

    def touch(self, x, y, event_type=DOWN_AND_UP):
        self.shell("input tap %d %d" % (x, y))

    def long_touch(self, x, y, duration=2000    ):
        """
        Long touches at (x, y)
        """
        self.drag((x, y), (x, y), duration)

    def drag(self, start_xy, end_xy, duration):
        """
        Sends drag event n PX (actually it's using C{input swipe} command.
        @param start_xy: starting point in pixel
        @param end_xy: ending point in pixel
        @param duration: duration of the event in ms
        @param orientation: the orientation (-1: undefined)
        """
        (x0, y0) = start_xy
        (x1, y1) = end_xy

        self.shell("input touchscreen swipe %d %d %d %d %d" % (x0, y0, x1, y1, duration))

    def type(self, text):
        if isinstance(text, str):
            escaped = text.replace("%s", "\\%s")
            encoded = escaped.replace(" ", "%s")
        else:
            encoded = str(text)
        # TODO find out which characters can be dangerous, and handle non-English characters
        self.shell("input text %s" % encoded)

    def press(self, key_code):
        """
        Press a key
        @param key_code: key code to press
        BACK = back, 66 = Enter, 3 = Home, 4 = Back
        """
        self.shell("input keyevent %s" % key_code)

    def run_cmd(self, extra_args):
        """
        run an adb command and return the output
        :return: output of adb command
        @param extra_args: arguments to run in adb
        """
        if isinstance(extra_args, str) or isinstance(extra_args, str):
            extra_args = extra_args.split()
        if not isinstance(extra_args, list):
            msg = "invalid arguments: %s\nshould be list or str, %s given" % (extra_args, type(extra_args))
            log(msg, "yellow")
            raise Exception(msg)

        args = [] + self.cmd_prefix
        args += extra_args

        log(f'command: {args}', "yellow")
        r = subprocess.check_output(args).strip()
        if not isinstance(r, str):
            r = r.decode()
        log(f'return: {r}', "yellow")
        return r
    
    def get_property(self, property_name):
        """
        get the value of property
        @param property_name:
        @return:
        """
        return self.shell(["getprop", property_name])