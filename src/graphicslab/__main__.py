import sys
import moderngl_window
from graphicslab import app


def main():
    args = sys.argv[1:]
    if "-wnd" not in args:
        args.append("-wnd")
        args.append("glfw")
    moderngl_window.run_window_config(
        app.App,
        args=args
    )


if __name__ == "__main__":
    main()
