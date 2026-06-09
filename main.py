"""
Remedi Bot - Automatizador de incidencias
Punto de entrada principal
"""
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Remedi Bot")
    app.setOrganizationName("AutoBot")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
