import sys
import os

# Add the current directory to sys.path so it can find chiptunepalace package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chiptunepalace.gui.main_window import MainWindow
from PySide6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
