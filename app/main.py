from __future__ import annotations

import tkinter as tk

from app.ui.main_window import UltimateBibleApp


def main() -> None:
    root = tk.Tk()
    UltimateBibleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
