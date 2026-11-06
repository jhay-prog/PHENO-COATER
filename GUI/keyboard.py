import subprocess


def show_keyboard():
    keyboard_path = r"C:\Windows\System32\osk.exe"
    try:
        subprocess.Popen([keyboard_path])
    except OSError as exc:
        print(
            f"Warning: could not launch the on-screen keyboard "
            f"({keyboard_path}): {exc}"
        )
