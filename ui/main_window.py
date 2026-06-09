"""
ui/main_window.py
Ventana principal del bot con diseño moderno.
"""
import asyncio
import queue
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFrame, QGridLayout,
    QLineEdit, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from core.browser import RemediAutomation


# ─────────────────────────────────────────────────────────────────
#  Worker: ejecuta Playwright en hilo separado sin bloquear la UI
# ─────────────────────────────────────────────────────────────────
class AutomationWorker(QThread):
    log_signal = pyqtSignal(str)
    ready_signal = pyqtSignal(bool)
    params_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.commands = queue.Queue()

    def ingresar_parametros(self, datos: dict):
        self.commands.put(("ingresar_parametros", datos))

    def detener(self):
        self.commands.put(("cerrar", None))

    def run(self):
        async def _run():
            bot = RemediAutomation(log_callback=self.log_signal.emit)
            try:
                await bot.iniciar()
                self.ready_signal.emit(True)

                while True:
                    accion, datos = await asyncio.to_thread(self.commands.get)
                    if accion == "cerrar":
                        await bot.cerrar()
                        break

                    if accion == "ingresar_parametros":
                        try:
                            await bot.ingresar_parametros(datos)
                            self.params_signal.emit(True)
                        except Exception as e:
                            self.log_signal.emit(f"Error al ingresar parametros: {e}")
                            self.params_signal.emit(False)
            except Exception as e:
                self.log_signal.emit(f"Error inesperado: {e}")
                self.ready_signal.emit(False)

        asyncio.run(_run())


# ─────────────────────────────────────────────────────────────────
#  Ventana principal
# ─────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self._build_ui()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.detener()
            self.worker.wait(3000)
        event.accept()

    # ── Construcción de la UI ──────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("Remedi Bot — Automatizador de Incidencias")
        self.setMinimumSize(720, 540)
        self.resize(760, 600)
        self._apply_theme()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        params_card = self._card()
        params_layout = QVBoxLayout(params_card)
        params_layout.setContentsMargins(24, 20, 24, 20)
        params_layout.setSpacing(14)

        params_title = QLabel("Parametros")
        params_title.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        params_title.setStyleSheet("color: #E2E8F0;")

        self.btn_iniciar = QPushButton("Abrir Nueva Incidencia")
        self.btn_iniciar.setFont(QFont("Segoe UI", 10, QFont.Medium))
        self.btn_iniciar.setFixedHeight(36)
        self.btn_iniciar.setCursor(Qt.PointingHandCursor)
        self.btn_iniciar.setStyleSheet(self._btn_primary_style())
        self.btn_iniciar.clicked.connect(self._on_iniciar)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.input_cliente = QLineEdit()
        self.input_cliente.setPlaceholderText("Dos apellidos")

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Corte FO", "Atenuacion", "Reclamo"])

        self.input_origen = QLineEdit()
        self.input_origen.setPlaceholderText("CONSTITU-WDM-TS01")

        self.input_destino = QLineEdit()
        self.input_destino.setPlaceholderText("TALCA-WDM-TS01")

        self.combo_via = QComboBox()
        self.combo_via.addItems(["Tigo", "Entel", "Claro", "Movistar", "GTD", "Otro"])

        for campo in (self.input_cliente, self.combo_tipo, self.input_origen, self.input_destino, self.combo_via):
            campo.setFixedHeight(34)
            campo.setStyleSheet(self._input_style())

        form.addWidget(self._field_label("Cliente"), 0, 0)
        form.addWidget(self.input_cliente, 0, 1)
        form.addWidget(self._field_label("Tipo"), 1, 0)
        form.addWidget(self.combo_tipo, 1, 1)
        form.addWidget(self._field_label("Origen"), 2, 0)
        form.addWidget(self.input_origen, 2, 1)
        form.addWidget(self._field_label("Destino"), 3, 0)
        form.addWidget(self.input_destino, 3, 1)
        form.addWidget(self._field_label("Via"), 4, 0)
        form.addWidget(self.combo_via, 4, 1)
        form.setColumnStretch(1, 1)

        self.btn_ingresar = QPushButton("Ingresar parametros al Remedi")
        self.btn_ingresar.setFont(QFont("Segoe UI", 11, QFont.Medium))
        self.btn_ingresar.setFixedHeight(42)
        self.btn_ingresar.setCursor(Qt.PointingHandCursor)
        self.btn_ingresar.setStyleSheet(self._btn_primary_style())
        self.btn_ingresar.setEnabled(False)
        self.btn_ingresar.clicked.connect(self._on_ingresar_parametros)

        params_layout.addWidget(params_title)
        params_layout.addWidget(self.btn_iniciar)
        params_layout.addLayout(form)
        params_layout.addWidget(self.btn_ingresar)
        root.addWidget(params_card)

        # ── Consola de log ────────────────────────────────────────
        log_label = QLabel("Registro de actividad")
        log_label.setFont(QFont("Segoe UI", 9))
        log_label.setStyleSheet("color: #64748B;")
        root.addWidget(log_label)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFont(QFont("Cascadia Code", 9))
        self.log_console.setStyleSheet("""
            QTextEdit {
                background-color: #0F172A;
                color: #7DD3FC;
                border: 1px solid #1E3A5F;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.log_console.setMinimumHeight(150)
        root.addWidget(self.log_console)

        # ── Status bar ────────────────────────────────────────────
        self.status_label = QLabel("Listo para iniciar")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet("color: #475569;")
        self.status_label.setAlignment(Qt.AlignRight)
        root.addWidget(self.status_label)

    # ── Lógica del botón ──────────────────────────────────────────
    def _on_iniciar(self):
        self.btn_iniciar.setEnabled(False)
        self.btn_iniciar.setText("Abriendo...")
        self.status_label.setText("Automatización en curso...")
        self.log_console.clear()

        self.worker = AutomationWorker()
        self.worker.log_signal.connect(self._append_log)
        self.worker.ready_signal.connect(self._on_ready)
        self.worker.params_signal.connect(self._on_params_done)
        self.worker.start()

    def _on_ready(self, success: bool):
        self.btn_iniciar.setEnabled(True)
        if success:
            self.btn_iniciar.setText("Nueva Incidencia abierta")
            self.btn_iniciar.setEnabled(False)
            self.btn_ingresar.setEnabled(True)
            self.status_label.setText("Modulo listo")
            self._append_log("Nueva Incidencia esta abierta.")
        else:
            self.btn_iniciar.setText("▶   Reintentar")
            self.status_label.setText("Se produjo un error")

    def _on_ingresar_parametros(self):
        if not self.worker or not self.worker.isRunning():
            self._append_log("Primero inicia la automatizacion.")
            return

        datos = {
            "cliente": self.input_cliente.text().strip(),
            "tipo": self.combo_tipo.currentText(),
            "origen": self.input_origen.text().strip(),
            "destino": self.input_destino.text().strip(),
            "via": self.combo_via.currentText(),
        }

        faltantes = [nombre for nombre in ("cliente", "origen", "destino") if not datos[nombre]]
        if faltantes:
            self._append_log("Completa: " + ", ".join(faltantes))
            return

        self.btn_ingresar.setEnabled(False)
        self.status_label.setText("Ingresando parametros...")
        self.worker.ingresar_parametros(datos)

    def _on_params_done(self, success: bool):
        self.btn_ingresar.setEnabled(True)
        self.status_label.setText("Parametros ingresados" if success else "Error al ingresar parametros")

    def _append_log(self, msg: str):
        self.log_console.append(msg)
        self.log_console.verticalScrollBar().setValue(
            self.log_console.verticalScrollBar().maximum()
        )

    # ── Helpers de estilo ─────────────────────────────────────────
    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0F1B2D;
                color: #E2E8F0;
            }
            QScrollBar:vertical {
                background: #1E293B;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 4px;
            }
        """)

    def _card(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #162032;
                border: 1px solid #1E3A5F;
                border-radius: 12px;
            }
        """)
        return frame

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #1E293B; border: none;")
        return line

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont("Segoe UI", 10))
        label.setStyleSheet("color: #CBD5E1;")
        return label

    def _input_style(self) -> str:
        return """
            QLineEdit, QComboBox {
                background-color: #0F172A;
                color: #E2E8F0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #38BDF8;
            }
        """

    def _btn_primary_style(self) -> str:
        return """
            QPushButton {
                background-color: #1D6FA4;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #2589C4;
            }
            QPushButton:pressed {
                background-color: #155A87;
            }
            QPushButton:disabled {
                background-color: #1E3A5F;
                color: #475569;
            }
        """
