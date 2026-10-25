"""
Smart Library Management System v2 — main.py
Entry point
"""
import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    from gui import SmartLibraryGUI
    root = tk.Tk()
    app  = SmartLibraryGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    ww = root.winfo_width()
    wh = root.winfo_height()
    root.geometry(f"+{(sw-ww)//2}+{(sh-wh)//2}")
    root.mainloop()

if __name__ == '__main__':
    main()
