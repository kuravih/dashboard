from os import path as os_path

RESOURCE_DIR = os_path.dirname(os_path.abspath(__file__))


def get_path(filename):
    return os_path.join(RESOURCE_DIR, filename)


ICON_STEP_BACK = get_path("backward-step-solid.svg")
ICON_BACKSPACE = get_path("delete-left-solid.svg")
ICON_DISK = get_path("floppy-disk-solid.svg")
ICON_FOLDER = get_path("folder-solid.svg")
ICON_STEP_FORWARD = get_path("forward-step-solid.svg")
ICON_GEAR = get_path("gear-solid.svg")
ICON_HOUSE = get_path("house-solid.svg")
ICON_MAGNIFY = get_path("magnifying-glass-solid.svg")
ICON_EYE = get_path("eye-solid.svg")
ICON_PAUSE = get_path("pause-solid.svg")
ICON_RUN = get_path("person-running-solid.svg")
ICON_PLAY = get_path("play-solid.svg")
ICON_SWITCH = get_path("right-left-solid.svg")
ICON_ROTATE_RIGHT = get_path("rotate-right-solid.svg")
ICON_STAIRS = get_path("stairs-solid.svg")
ICON_SHOE = get_path("shoe-prints-solid.svg")
ICON_STOP = get_path("stop-solid.svg")
ICON_TURN_DOWN = get_path("turn-down-solid.svg")
ICON_UNPAUSE = get_path("unpause-solid.svg")
ICON_MOVE = get_path("up-down-left-right-solid.svg")
ICON_PRINT = get_path("print-solid.svg")
ICON_PDF = get_path("file-pdf-solid.svg")
ICON_LEFT_ARROW = get_path("left-long-solid.svg")
ICON_RIGHT_ARROW = get_path("right-long-solid.svg")
ICON_UP_ARROW = get_path("up-long-solid.svg")
ICON_DOWN_ARROW = get_path("down-long-solid.svg")
ICON_CAMERA = get_path("camera-solid.svg")
ICON_CENTER = get_path("arrows-to-circle-solid.svg")
ICON_INFO = get_path("circle-info-solid.svg")
ICON_SUN = get_path("sun-solid-full.svg")
ICON_PAPER_PLANE = get_path("paper-plane-solid-full.svg")
ICON_PLUS = get_path("plus-solid-full.svg")
ICON_MINUS = get_path("minus-solid-full.svg")

