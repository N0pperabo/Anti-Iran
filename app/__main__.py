"""Application entrypoint for python -m app."""

import logging
import sys
from PySide6.QtWidgets import QApplication
from app.state_manager import ApplicationStateManager
from ui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GitHub Actions Browser Automation Studio")
    app.setOrganizationName("AutomationStudio")

    state_mgr = ApplicationStateManager()
    window = MainWindow(state_mgr)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
