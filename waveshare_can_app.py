"""
Waveshare USB-CAN-A Analyzer
A modern PyQt6 GUI for the Waveshare USB-CAN-A adapter using waveshare_can_bus.py.

Usage:
    python waveshare_can_app.py

Dependencies:
    pip install PyQt6 pyserial python-can
    Place waveshare_can_bus.py in the same directory (or on PYTHONPATH).
"""

import sys
import os
import time
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QSplitter,
    QFrame, QSpinBox, QStatusBar, QToolButton, QSizePolicy, QScrollArea,
)

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation,
    QEasingCurve, QRect,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter, QPen,
    QBrush, QLinearGradient, QFontDatabase,
)

# ── Try importing the Waveshare bus ──────────────────────────────────────────
try:
    from waveshare_can_bus import (
        WaveshareCANBus, CANProtocol, CANBaudRate, CANFrameType, CANMode,
    )
    from can import Message
    BUS_AVAILABLE = True
except ImportError:
    BUS_AVAILABLE = False

import serial.tools.list_ports

# ── Palette ──────────────────────────────────────────────────────────────────
# Dark industrial theme: near-black surface, electric cyan accent, amber for TX
COLORS = {
    "bg":           "#0E1117",
    "surface":      "#161B25",
    "surface2":     "#1E2535",
    "border":       "#2A3347",
    "accent":       "#00C6FF",     # cyan — RX frames, active indicators
    "accent_dim":   "#005E7A",
    "amber":        "#FFB547",     # TX frames
    "amber_dim":    "#7A4E00",
    "error":        "#FF4C4C",
    "success":      "#3DDB84",
    "text":         "#E8EDF5",
    "text_muted":   "#6B7A99",
    "text_dim":     "#3A4560",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: 'Inter', 'SF Pro Display', 'Segoe UI', sans-serif;
    font-size: 13px;
}}

/* ── Groups ── */
QGroupBox {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 20px;
    padding: 12px 10px 10px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: {COLORS['text_muted']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    top: 2px;
}}

/* ── Inputs ── */
QLineEdit, QComboBox, QSpinBox {{
    background-color: {COLORS['surface2']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 2px 10px;
    color: {COLORS['text']};
    selection-background-color: {COLORS['accent_dim']};
    min-height: 28px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {COLORS['accent']};
    outline: none;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['surface2']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent_dim']};
    color: {COLORS['text']};
    border-radius: 6px;
    padding: 2px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {COLORS['surface']};
    border: none;
    width: 18px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {COLORS['surface2']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 2px 16px;
    font-weight: 500;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {COLORS['border']};
    border-color: {COLORS['text_muted']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent_dim']};
}}
QPushButton:disabled {{
    color: {COLORS['text_dim']};
    border-color: {COLORS['text_dim']};
}}
QPushButton#primary {{
    background-color: {COLORS['accent']};
    color: {COLORS['bg']};
    border: none;
    font-weight: 700;
}}
QPushButton#primary:hover {{
    background-color: #33D4FF;
}}
QPushButton#primary:pressed {{
    background-color: {COLORS['accent_dim']};
    color: {COLORS['text']};
}}
QPushButton#danger {{
    background-color: transparent;
    color: {COLORS['error']};
    border: 1px solid {COLORS['error']};
}}
QPushButton#danger:hover {{
    background-color: rgba(255,76,76,0.15);
}}
QPushButton#send_btn {{
    background-color: {COLORS['surface2']};
    color: {COLORS['accent']};
    border: 1px solid {COLORS['accent']};
    font-weight: 600;
    border-radius: 6px;
}}
QPushButton#send_btn:hover {{
    background-color: {COLORS['border']};
    border-color: {COLORS['accent']};
}}
QPushButton#send_btn:pressed {{
    background-color: {COLORS['accent_dim']};
    border-color: {COLORS['accent']};
    color: {COLORS['text']};
}}
QPushButton#send_btn:disabled {{
    background-color: {COLORS['surface2']};
    color: {COLORS['text_dim']};
    border: 1px solid {COLORS['text_dim']};
}}

/* ── Table ── */
QTableWidget {{
    background-color: {COLORS['surface']};
    gridline-color: {COLORS['border']};
    border: none;
    border-radius: 0px;
    selection-background-color: {COLORS['surface2']};
    alternate-background-color: {COLORS['bg']};
    font-family: 'JetBrains Mono', 'Fira Code', 'Menlo', 'Consolas', monospace;
    font-size: 12px;
}}
QTableWidget::item {{
    padding: 2px 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {COLORS['surface2']};
    color: {COLORS['text']};
}}
QHeaderView::section {{
    background-color: {COLORS['bg']};
    color: {COLORS['text_muted']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    padding: 6px 8px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

/* ── Scroll bars ── */
QScrollBar:vertical {{
    background: {COLORS['bg']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {COLORS['bg']};
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['border']};
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── CheckBox ── */
QCheckBox {{
    color: {COLORS['text']};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {COLORS['border']};
    background: {COLORS['surface2']};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {COLORS['bg']};
    border-top: 1px solid {COLORS['border']};
    color: {COLORS['text_muted']};
    font-size: 11px;
}}
QStatusBar::item {{
    border: none;
}}

/* ── Labels ── */
QLabel#heading {{
    font-size: 18px;
    font-weight: 700;
    color: {COLORS['text']};
    letter-spacing: -0.3px;
}}
QLabel#mono {{
    font-family: 'JetBrains Mono', 'Fira Code', 'Menlo', 'Consolas', monospace;
    font-size: 12px;
    color: {COLORS['accent']};
}}
QLabel#muted {{
    color: {COLORS['text_muted']};
    font-size: 11px;
}}
QLabel#row_header {{
    padding: 0px 4px;
}}

/* ── Divider ── */
QFrame#divider {{
    color: {COLORS['border']};
    border: 1px solid {COLORS['border']};
    max-height: 1px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {COLORS['border']};
    width: 2px;
    height: 2px;
}}
"""

# ── Helpers ─────────────────────────────────────────────────────────────────

def _hex_label(val: int, width: int = 2) -> str:
    return f"0x{val:0{width}X}"


def _parse_hex_id(text: str) -> Optional[int]:
    text = text.strip().replace("0x", "").replace("0X", "")
    try:
        val = int(text, 16)
        return val
    except ValueError:
        return None


def _parse_hex_data(text: str) -> Optional[bytes]:
    tokens = text.strip().split()
    try:
        return bytes(int(t, 16) for t in tokens if t)
    except ValueError:
        return None


# ── Indicator dot ────────────────────────────────────────────────────────────

class StatusDot(QLabel):
    """Tiny coloured circle indicator."""

    def __init__(self, color=COLORS["text_dim"], parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(10, 10)
        self._update_pixmap()

    def set_color(self, color: str):
        self._color = color
        self._update_pixmap()

    def _update_pixmap(self):
        px = QPixmap(10, 10)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(self._color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(1, 1, 8, 8)
        p.end()
        self.setPixmap(px)


# ── Counter badge ─────────────────────────────────────────────────────────────

class CountBadge(QLabel):
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._count = 0
        self._update()

    def increment(self):
        self._count += 1
        self._update()

    def reset(self):
        self._count = 0
        self._update()

    def _update(self):
        self.setText(f"{self._label}  {self._count}")
        self.setStyleSheet(
            f"color: {self._color}; font-family: 'JetBrains Mono','Menlo','Consolas',monospace;"
            f"font-size: 12px; font-weight: 600;"
        )


# ── Receive thread ───────────────────────────────────────────────────────────

class ReceiveThread(QThread):
    frame_received = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self._bus = bus
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            try:
                msg = self._bus.recv(timeout=0.1)
                if msg is not None:
                    self.frame_received.emit(msg)
            except Exception as exc:
                if self._running:
                    self.error_occurred.emit(str(exc))
                break

    def stop(self):
        self._running = False
        self.wait(1000)


# ── Send row widget ───────────────────────────────────────────────────────────

class _FocusLineEdit(QLineEdit):
    """QLineEdit that emits a custom signal when it gains focus."""
    focused = pyqtSignal()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focused.emit()


class SendRow(QWidget):
    """One manual-send row: ID | Data | Extended | Remote | [Send]

    Emits ``row_focused`` whenever any interactive field inside the row
    receives focus or is clicked, so the parent can highlight this row
    as selected without requiring the user to click on blank space.
    """

    row_focused = pyqtSignal(object)   # payload: self

    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.setProperty("selected", False)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        # Row number (exposed as num_label for renumbering)
        self.num_label = QLabel(f"{index + 1:02d}")
        self.num_label.setFixedWidth(24)
        self.num_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
        self.num_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.num_label)

        # ID field
        self.id_edit = _FocusLineEdit()
        self.id_edit.setPlaceholderText("ID (hex)")
        self.id_edit.setFixedWidth(80)
        self.id_edit.setToolTip("CAN frame ID in hex, e.g. 0xF9 or F9")
        self.id_edit.focused.connect(lambda: self.row_focused.emit(self))
        layout.addWidget(self.id_edit)

        # Data field
        self.data_edit = _FocusLineEdit()
        self.data_edit.setPlaceholderText("Data bytes (hex, space-separated)  e.g.  C0 E8 03 00 00")
        self.data_edit.setToolTip("Up to 8 hex bytes separated by spaces")
        self.data_edit.focused.connect(lambda: self.row_focused.emit(self))
        layout.addWidget(self.data_edit)

        layout.addSpacing(4)

        # Extended checkbox — clicking it also selects the row
        self.ext_check = QCheckBox("Ext")
        self.ext_check.setToolTip("Extended 29-bit frame ID")
        self.ext_check.setFixedWidth(48)
        self.ext_check.clicked.connect(lambda: self.row_focused.emit(self))
        layout.addWidget(self.ext_check)

        layout.addSpacing(4)

        # Remote checkbox
        self.rtr_check = QCheckBox("RTR")
        self.rtr_check.setToolTip("Remote Transmission Request")
        self.rtr_check.setFixedWidth(48)
        self.rtr_check.clicked.connect(lambda: self.row_focused.emit(self))
        layout.addWidget(self.rtr_check)

        # Spacer before send button
        layout.addSpacing(12)

        # Send button — also selects the row when clicked
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(lambda: self.row_focused.emit(self))
        layout.addWidget(self.send_btn)


# ── Main window ───────────────────────────────────────────────────────────────

class WaveshareCANApp(QMainWindow):
    _MAX_LOG_ROWS = 2000
    _NUM_SEND_ROWS = 8
    _MIN_SEND_ROWS = 5

    # Persistent send-row state; created automatically on first save
    def _get_data_dir() -> Path:
        if sys.platform == "darwin":
            # ~/Library/Application Support/WaveshareCANAnalyzer
            base = Path(os.environ.get("HOME", "~")).expanduser() / "Library" / "Application Support"
        elif sys.platform == "win32":
            # C:\Users\<user>\AppData\Roaming\WaveshareCANAnalyzer
            base = Path(os.environ.get("APPDATA", "~\\AppData\\Roaming")).expanduser()
        else:
            # Linux fallback: ~/.local/share/WaveshareCANAnalyzer
            base = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
        return base / "WaveshareCANAnalyzer"

    _DATA_DIR = _get_data_dir()
    _SAVE_FILE: Path = _DATA_DIR / "send_rows.canframes"
    _CONFIG_FILE: Path = _DATA_DIR / "config.json"

    def __init__(self):
        super().__init__()
        self.bus: Optional[WaveshareCANBus] = None
        self.rx_thread: Optional[ReceiveThread] = None
        self._connected = False
        self._tx_count = 0
        self._rx_count = 0
        self._auto_scroll = True

        self.setWindowTitle("Waveshare CAN Analyzer")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 820)

        self._setup_ui()
        self._refresh_ports()
        self._load_conn_settings()   # restore connection settings from previous session
        self._load_send_rows()       # restore rows saved from previous session

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 14, 16, 8)
        root.setSpacing(10)

        # ── Header bar ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)

        title = QLabel("CAN Analyzer")
        title.setObjectName("heading")
        header.addWidget(title)

        subtitle = QLabel("Waveshare USB-CAN-A")
        subtitle.setObjectName("muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(subtitle)

        header.addStretch()

        # TX / RX counters
        self.tx_badge = CountBadge("TX", COLORS["amber"])
        self.rx_badge = CountBadge("RX", COLORS["accent"])
        header.addWidget(self.tx_badge)
        sep = QLabel("·")
        sep.setStyleSheet(f"color: {COLORS['text_dim']};")
        header.addWidget(sep)
        header.addWidget(self.rx_badge)

        # Status dot + label
        self.status_dot = StatusDot(COLORS["text_dim"])
        header.addWidget(self.status_dot)
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        header.addWidget(self.status_label)

        root.addLayout(header)

        # ── Thin divider ────────────────────────────────────────────────────
        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(div)

        # ── Main splitter: left panel | log table ────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        root.addWidget(splitter, stretch=1)

        # Left column
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(8)
        left_col.setMinimumWidth(300)
        left_col.setMaximumWidth(400)
        splitter.addWidget(left_col)

        # ── Connection group ──────────────────────────────────────────────
        conn_group = QGroupBox("Connection")
        cg_layout = QGridLayout(conn_group)
        cg_layout.setSpacing(5)
        cg_layout.setContentsMargins(10, 16, 10, 10)
        cg_layout.setColumnStretch(1, 1)

        port_label = QLabel("Port")
        port_label.setObjectName("row_header")
        cg_layout.addWidget(port_label, 0, 0)
        port_row = QHBoxLayout()
        port_row.setSpacing(4)
        port_row.setContentsMargins(0, 0, 0, 0)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(130)
        port_row.addWidget(self.port_combo)
        refresh_btn = QPushButton("↻")
        refresh_btn.setToolTip("Refresh serial ports")
        refresh_btn.clicked.connect(self._refresh_ports)
        port_row.addWidget(refresh_btn)
        cg_layout.addLayout(port_row, 0, 1)

        serial_baud_label = QLabel("Serial Baud")
        serial_baud_label.setObjectName("row_header")
        cg_layout.addWidget(serial_baud_label, 1, 0)
        self.serial_baud_combo = QComboBox()
        for br in ["2000000", "1000000", "921600", "115200"]:
            self.serial_baud_combo.addItem(br)
        self.serial_baud_combo.setCurrentText("2000000")
        cg_layout.addWidget(self.serial_baud_combo, 1, 1)

        can_baud_label = QLabel("CAN Baud")
        can_baud_label.setObjectName("row_header")
        cg_layout.addWidget(can_baud_label, 2, 0)
        self.can_baud_combo = QComboBox()
        baud_map = {
            "1 Mbps": CANBaudRate.MBPS_1 if BUS_AVAILABLE else "MBPS_1",
            "800 kbps": CANBaudRate.KBPS_800 if BUS_AVAILABLE else "KBPS_800",
            "500 kbps": CANBaudRate.KBPS_500 if BUS_AVAILABLE else "KBPS_500",
            "400 kbps": CANBaudRate.KBPS_400 if BUS_AVAILABLE else "KBPS_400",
            "250 kbps": CANBaudRate.KBPS_250 if BUS_AVAILABLE else "KBPS_250",
            "200 kbps": CANBaudRate.KBPS_200 if BUS_AVAILABLE else "KBPS_200",
            "125 kbps": CANBaudRate.KBPS_125 if BUS_AVAILABLE else "KBPS_125",
            "100 kbps": CANBaudRate.KBPS_100 if BUS_AVAILABLE else "KBPS_100",
            "50 kbps":  CANBaudRate.KBPS_50  if BUS_AVAILABLE else "KBPS_50",
        }
        self._baud_map = baud_map
        for label in baud_map:
            self.can_baud_combo.addItem(label)
        self.can_baud_combo.setCurrentText("250 kbps")
        cg_layout.addWidget(self.can_baud_combo, 2, 1)

        protocol_label = QLabel("Protocol")
        protocol_label.setObjectName("row_header")
        cg_layout.addWidget(protocol_label, 3, 0)
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["Variable length", "Fixed 20 bytes"])
        cg_layout.addWidget(self.protocol_combo, 3, 1)

        frame_type_label = QLabel("Frame Type")
        frame_type_label.setObjectName("row_header")
        cg_layout.addWidget(frame_type_label, 4, 0)
        self.frame_type_combo = QComboBox()
        self.frame_type_combo.addItems(["Standard (11-bit)", "Extended (29-bit)"])
        cg_layout.addWidget(self.frame_type_combo, 4, 1)

        can_mode_label = QLabel("CAN Mode")
        can_mode_label.setObjectName("row_header")
        cg_layout.addWidget(can_mode_label, 5, 0)
        self.can_mode_combo = QComboBox()
        # Order matches CANMode enum: NORMAL=0, LOOPBACK=1, SILENT=2, SILENT_LOOPBACK=3
        mode_map = {
            "Normal":          CANMode.NORMAL          if BUS_AVAILABLE else "NORMAL",
            "Loopback":        CANMode.LOOPBACK        if BUS_AVAILABLE else "LOOPBACK",
            "Silent":          CANMode.SILENT          if BUS_AVAILABLE else "SILENT",
            "Loopback Silent": CANMode.SILENT_LOOPBACK if BUS_AVAILABLE else "SILENT_LOOPBACK",
        }
        self._mode_map = mode_map
        self.can_mode_combo.addItems(list(mode_map.keys()))
        cg_layout.addWidget(self.can_mode_combo, 5, 1)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("primary")
        self.connect_btn.setFixedHeight(34)
        self.connect_btn.clicked.connect(self._toggle_connection)
        cg_layout.addWidget(self.connect_btn, 6, 0, 1, 2)

        left_layout.addWidget(conn_group)

        # ── Filter group ───────────────────────────────────────────────────
        filter_group = QGroupBox("Hardware Filter  (Fixed protocol only)")
        fg_layout = QGridLayout(filter_group)
        fg_layout.setSpacing(5)
        fg_layout.setContentsMargins(10, 16, 10, 10)

        filter_id_label = QLabel("Filter ID")
        filter_id_label.setObjectName("row_header")
        fg_layout.addWidget(filter_id_label, 0, 0)
        self.filter_id_edit = QLineEdit("0x00000000")
        self.filter_id_edit.setToolTip("Frames matching this ID pass the hardware filter")
        fg_layout.addWidget(self.filter_id_edit, 0, 1)

        block_id_label = QLabel("Block ID")
        block_id_label.setObjectName("row_header")
        fg_layout.addWidget(block_id_label, 1, 0)
        self.block_id_edit = QLineEdit("0x00000000")
        self.block_id_edit.setToolTip("Frames matching this ID are blocked")
        fg_layout.addWidget(self.block_id_edit, 1, 1)

        left_layout.addWidget(filter_group)

        # ── Options group ─────────────────────────────────────────────────
        opt_group = QGroupBox("Options")
        og_layout = QVBoxLayout(opt_group)
        og_layout.setSpacing(10)
        og_layout.setContentsMargins(10, 16, 10, 10)

        self.auto_retransmit_check = QCheckBox("Auto-retransmit on error")
        self.auto_retransmit_check.setChecked(True)
        og_layout.addWidget(self.auto_retransmit_check)

        self.auto_scroll_check = QCheckBox("Auto-scroll log")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.stateChanged.connect(
            lambda s: setattr(self, "_auto_scroll", bool(s))
        )
        og_layout.addWidget(self.auto_scroll_check)

        self.show_only_rx_check = QCheckBox("Show RX only")
        og_layout.addWidget(self.show_only_rx_check)

        left_layout.addWidget(opt_group)
        left_layout.addStretch()

        # Wire auto-save on every connection / filter / option widget
        # (done here so all widgets are guaranteed to exist)
        for widget in (
            self.serial_baud_combo, self.can_baud_combo, self.protocol_combo,
            self.frame_type_combo, self.can_mode_combo,
        ):
            widget.currentIndexChanged.connect(self._save_conn_settings)
        for widget in (self.filter_id_edit, self.block_id_edit):
            widget.textChanged.connect(self._save_conn_settings)
        self.auto_retransmit_check.toggled.connect(self._save_conn_settings)
        # port_combo is wired in _refresh_ports after items are populated

        # Right column: vertical splitter → log pane (top) + send pane (bottom)
        right_col = QWidget()
        right_outer = QVBoxLayout(right_col)
        right_outer.setContentsMargins(10, 0, 0, 0)
        right_outer.setSpacing(0)
        splitter.addWidget(right_col)

        splitter.setSizes([320, 860])

        # Vertical splitter between log and send panel
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setHandleWidth(4)
        v_splitter.setStyleSheet(f"""
            QSplitter::handle:vertical {{
                background-color: {COLORS['border']};
                height: 4px;
            }}
            QSplitter::handle:vertical:hover {{
                background-color: {COLORS['accent_dim']};
            }}
        """)
        right_outer.addWidget(v_splitter)

        # Log pane widget
        log_pane = QWidget()
        right_layout = QVBoxLayout(log_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        v_splitter.addWidget(log_pane)

        # ── Log table ─────────────────────────────────────────────────────
        log_header = QHBoxLayout()
        log_header.setContentsMargins(8, 0, 0, 0)
        log_header.setSpacing(8)
        log_lbl = QLabel("Frame Log")
        log_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; letter-spacing: 1.2px;"
            f"text-transform: uppercase; color: {COLORS['text_muted']};"
        )
        log_header.addWidget(log_lbl)
        log_header.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self._clear_log)
        log_header.addWidget(clear_btn)

        right_layout.addLayout(log_header, stretch=0)

        self.log_table = QTableWidget(0, 8)
        self.log_table.setHorizontalHeaderLabels([
            "No", "Time", "Dir", "Format", "Type", "ID (Hex)", "DLC", "Data (Hex)",
        ])
        self.log_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.log_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.log_table.horizontalHeader().setDefaultSectionSize(72)
        self.log_table.setColumnWidth(0, 50)
        self.log_table.setColumnWidth(1, 100)
        self.log_table.setColumnWidth(2, 42)
        self.log_table.setColumnWidth(3, 80)
        self.log_table.setColumnWidth(4, 64)
        self.log_table.setColumnWidth(5, 90)
        self.log_table.setColumnWidth(6, 40)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setShowGrid(False)
        self.log_table.setWordWrap(False)
        self.log_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        right_layout.addWidget(self.log_table, stretch=1)

        # ── Manual send panel ─────────────────────────────────────────────
        # Wrap in its own pane widget so v_splitter can resize it independently
        send_pane = QWidget()
        send_pane_layout = QVBoxLayout(send_pane)
        send_pane_layout.setContentsMargins(0, 4, 0, 0)
        send_pane_layout.setSpacing(0)
        v_splitter.addWidget(send_pane)

        # Default split: log gets ~60 %, send gets ~40 %
        v_splitter.setSizes([480, 320])
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 0)

        send_group = QGroupBox("Manual Send")
        sg_layout = QVBoxLayout(send_group)
        sg_layout.setSpacing(0)
        sg_layout.setContentsMargins(6, 8, 6, 6)

        send_scroll = QScrollArea()
        send_scroll.setWidgetResizable(True)
        send_scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }}")
        send_container = QWidget()
        send_container_layout = QVBoxLayout(send_container)
        send_container_layout.setSpacing(4)
        send_container_layout.setContentsMargins(4, 8, 8, 4)

        self._send_container_layout = send_container_layout
        self.send_rows: list[SendRow] = []
        for i in range(self._NUM_SEND_ROWS):
            row = self._make_row(i)
            self.send_rows.append(row)
            send_container_layout.addWidget(row)

        send_container_layout.addStretch()
        send_scroll.setWidget(send_container)
        sg_layout.addWidget(send_scroll)

        sg_layout.addSpacing(10)

        # Insert / Delete buttons (rows auto-save on every edit)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        insert_btn = QPushButton("+ Insert")
        insert_btn.setToolTip("Insert a row below the selected row")
        insert_btn.clicked.connect(self._insert_send_row)
        delete_btn = QPushButton("− Delete")
        delete_btn.setToolTip("Delete the selected row")
        delete_btn.clicked.connect(self._delete_send_row)
        btn_row.addWidget(insert_btn)
        btn_row.addWidget(delete_btn)
        btn_row.addStretch()
        autosave_lbl = QLabel("auto-saved")
        autosave_lbl.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 10px; font-style: italic;"
        )
        btn_row.addWidget(autosave_lbl)
        sg_layout.addLayout(btn_row)

        send_pane_layout.addWidget(send_group)

        # ── Status bar ────────────────────────────────────────────────────
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_msg = QLabel("Ready · waveshare_can_bus.py"
                                  if BUS_AVAILABLE else
                                  "⚠  waveshare_can_bus.py not found — import failed")
        self._status_msg.setStyleSheet(
            f"color: {'#FFB547' if not BUS_AVAILABLE else COLORS['text_muted']}; font-size: 11px;"
        )
        sb.addWidget(self._status_msg)

        if not BUS_AVAILABLE:
            self.connect_btn.setEnabled(False)

    # ── Connection settings persistence ──────────────────────────────────────

    def _save_conn_settings(self):
        """Silently persist all connection / filter / option widget values."""
        settings = {
            "version":         1,
            "port":            self.port_combo.currentData() or "",
            "serial_baud":     self.serial_baud_combo.currentText(),
            "can_baud":        self.can_baud_combo.currentText(),
            "protocol":        self.protocol_combo.currentIndex(),
            "frame_type":      self.frame_type_combo.currentIndex(),
            "can_mode":        self.can_mode_combo.currentIndex(),
            "auto_retransmit": self.auto_retransmit_check.isChecked(),
            "filter_id":       self.filter_id_edit.text(),
            "block_id":        self.block_id_edit.text(),
        }
        try:
            self._CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._CONFIG_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except Exception as exc:
            self._set_status(f"Settings save failed: {exc}", error=True)

    def _load_conn_settings(self):
        """
        Restore connection settings from the previous session.

        Port selection is handled separately in _refresh_ports (which has
        access to the live port list needed to check availability).
        All other widgets are restored here, silently, before the port combo
        is populated — so the user sees their last-used values immediately.
        """
        if not self._CONFIG_FILE.exists():
            return
        try:
            s = json.loads(self._CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return   # corrupted — keep defaults

        if s.get("version") != 1:
            return

        # Serial baud
        serial_baud = s.get("serial_baud", "")
        if serial_baud and self.serial_baud_combo.findText(serial_baud) != -1:
            self.serial_baud_combo.setCurrentText(serial_baud)

        # CAN baud
        can_baud = s.get("can_baud", "")
        if can_baud and self.can_baud_combo.findText(can_baud) != -1:
            self.can_baud_combo.setCurrentText(can_baud)

        # Index-based combos
        for attr, key in (
            ("protocol_combo",   "protocol"),
            ("frame_type_combo", "frame_type"),
            ("can_mode_combo",   "can_mode"),
        ):
            idx = s.get(key)
            combo = getattr(self, attr)
            if isinstance(idx, int) and 0 <= idx < combo.count():
                combo.setCurrentIndex(idx)

        # Checkbox
        if isinstance(s.get("auto_retransmit"), bool):
            self.auto_retransmit_check.setChecked(s["auto_retransmit"])

        # Filter / block ID text fields
        if s.get("filter_id"):
            self.filter_id_edit.setText(s["filter_id"])
        if s.get("block_id"):
            self.block_id_edit.setText(s["block_id"])

    # ── Port refresh ─────────────────────────────────────────────────────────

    def _refresh_ports(self):
        # Temporarily block the port combo's signal so repopulating doesn't
        # trigger a spurious save with an intermediate selection.
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        available = set()
        for p in sorted(ports, key=lambda x: x.device):
            self.port_combo.addItem(f"{p.device}  —  {p.description}", userData=p.device)
            available.add(p.device)
        if not ports:
            self.port_combo.addItem("No ports found")
        self.port_combo.blockSignals(False)

        # Re-select the previously saved port if it is still available
        try:
            saved = json.loads(self._CONFIG_FILE.read_text(encoding="utf-8"))
            saved_port = saved.get("port", "")
        except Exception:
            saved_port = ""

        if saved_port and saved_port in available:
            for i in range(self.port_combo.count()):
                if self.port_combo.itemData(i) == saved_port:
                    self.port_combo.setCurrentIndex(i)
                    break
        elif saved_port:
            # Port was saved but is not currently plugged in — show a hint
            self._set_status(
                f"Saved port {saved_port!r} not found — plug it in or select another.",
                error=True,
            )

        # Wire save after the initial population so changing the port saves
        self.port_combo.currentIndexChanged.connect(self._save_conn_settings)

    # ── Connection ───────────────────────────────────────────────────────────

    def _toggle_connection(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self.port_combo.currentData()
        if not port:
            self._set_status("No port selected", error=True)
            return

        serial_baud = int(self.serial_baud_combo.currentText())

        protocol = (CANProtocol.VARIABLE
                    if self.protocol_combo.currentIndex() == 0
                    else CANProtocol.FIXED)

        can_baud_label = self.can_baud_combo.currentText()
        can_baud = self._baud_map[can_baud_label]

        frame_type = (CANFrameType.STANDARD
                      if self.frame_type_combo.currentIndex() == 0
                      else CANFrameType.EXTENDED)

        can_mode = self._mode_map[self.can_mode_combo.currentText()]

        auto_retransmit = 0x00 if self.auto_retransmit_check.isChecked() else 0x01

        filter_id = _parse_hex_id(self.filter_id_edit.text()) or 0
        block_id  = _parse_hex_id(self.block_id_edit.text()) or 0

        # ── Step 1: open port ────────────────────────────────────────────
        self._set_status(f"Connecting to {port}…")
        try:
            bus = WaveshareCANBus(
                channel=port,
                baudrate=serial_baud,
                serial_timeout=0.1,
            )
        except Exception as exc:
            self._set_status(f"Connection failed: {exc}", error=True)
            return

        # ── Step 2: loopback verify ──────────────────────────────────────
        # Switch silently to loopback mode, send a probe frame, confirm
        # we receive the same frame back.  Then reconfigure with the user's
        # chosen settings before handing the bus to the receive thread.
        self._set_status(f"Verifying port {port}…")
        try:
            bus.configure(
                protocol=CANProtocol.VARIABLE,
                can_baudrate=can_baud,
                frame_type=CANFrameType.STANDARD,
                can_mode=CANMode.LOOPBACK,
                auto_retransmit=0x00,
                settle_s=0.15,
            )
            probe_id   = 0x7EF          # arbitrary test ID unlikely to collide
            probe_data = bytes([0xCA, 0xFE, 0xBA, 0xBE])
            probe_msg  = Message(
                arbitration_id=probe_id,
                data=probe_data,
                dlc=len(probe_data),
                is_extended_id=False,
            )
            bus.send(probe_msg)

            # Drain incoming frames for up to 500 ms looking for the echo
            deadline = time.time() + 0.5
            verified = False
            while time.time() < deadline:
                echo = bus.recv(timeout=max(0.0, deadline - time.time()))
                if echo is None:
                    break
                if (echo.arbitration_id == probe_id
                        and bytes(echo.data[:len(probe_data)]) == probe_data):
                    verified = True
                    break

            if not verified:
                bus.shutdown()
                self._set_status(
                    f"Port {port} did not echo the probe frame — "
                    "check that the adapter is connected and the baud rate is correct.",
                    error=True,
                )
                return

        except Exception as exc:
            try:
                bus.shutdown()
            except Exception:
                pass
            self._set_status(f"Loopback verify failed: {exc}", error=True)
            return

        # ── Step 3: reconfigure with user settings ───────────────────────
        try:
            bus.configure(
                protocol=protocol,
                can_baudrate=can_baud,
                frame_type=frame_type,
                filter_id=filter_id,
                block_id=block_id,
                can_mode=can_mode,
                auto_retransmit=auto_retransmit,
                settle_s=0.15,
            )
        except Exception as exc:
            try:
                bus.shutdown()
            except Exception:
                pass
            self._set_status(f"Adapter configuration failed: {exc}", error=True)
            return

        self.bus = bus
        self._connected = True
        self._update_send_buttons(True)
        self.connect_btn.setText("Disconnect")
        self.connect_btn.setObjectName("danger")
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
        self.status_dot.set_color(COLORS["success"])
        self.status_label.setText(f"Connected  ·  {port}  ·  {can_baud_label}")
        self.status_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px; font-weight: 500;")

        self._set_status(f"Connected to {port} @ {serial_baud} bps · CAN {can_baud_label}")

        # Start receive thread
        self.rx_thread = ReceiveThread(self.bus)
        self.rx_thread.frame_received.connect(self._on_rx_frame)
        self.rx_thread.error_occurred.connect(lambda e: self._set_status(f"RX error: {e}", error=True))
        self.rx_thread.start()

    # ── Auto-save / auto-load send rows ─────────────────────────────────────

    def _make_row(self, index: int) -> "SendRow":
        """Construct one SendRow, wire its signals, and return it (not yet in a layout)."""
        row = SendRow(index)
        row.send_btn.clicked.connect(lambda _, r=row: self._send_row(r))
        row.row_focused.connect(self._select_send_row)
        # Auto-save whenever the user edits a field
        row.id_edit.textChanged.connect(self._save_send_rows)
        row.data_edit.textChanged.connect(self._save_send_rows)
        row.ext_check.toggled.connect(self._save_send_rows)
        row.rtr_check.toggled.connect(self._save_send_rows)
        row.send_btn.setEnabled(self._connected)
        return row

    def _save_send_rows(self):
        """
        Silently persist all manual-send rows to the fixed user-data file.

        Called automatically after every structural change or field edit.
        Errors are only surfaced to the status bar; they never block the UI.

        File format (version 1):
        {
            "version": 1,
            "frames": [
                { "id": "F9", "data": "C0 E8 03 00 00", "ext": false, "rtr": false }
            ]
        }
        """
        frames = [
            {
                "id":   row.id_edit.text().strip(),
                "data": row.data_edit.text().strip(),
                "ext":  row.ext_check.isChecked(),
                "rtr":  row.rtr_check.isChecked(),
            }
            for row in self.send_rows
        ]
        payload = {"version": 1, "frames": frames}
        try:
            self._SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._SAVE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            self._set_status(f"Auto-save failed: {exc}", error=True)

    def _load_send_rows(self):
        """
        Restore send rows from the fixed user-data file on startup.

        If the file does not exist (first launch) or cannot be parsed,
        this is a silent no-op — the default rows from _setup_ui are kept.
        """
        if not self._SAVE_FILE.exists():
            return

        try:
            payload = json.loads(self._SAVE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return   # corrupted file — keep defaults

        if payload.get("version") != 1:
            return   # unknown format — keep defaults

        frames = payload.get("frames", [])
        if not isinstance(frames, list) or not frames:
            return

        # Replace the default rows built by _setup_ui
        for row in self.send_rows:
            row.deleteLater()
        self.send_rows.clear()

        layout = self._send_container_layout
        while layout.count() > 1:      # keep only the trailing stretch
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, entry in enumerate(frames):
            row = self._make_row(i)
            # Block signals while setting text so that textChanged doesn't fire
            # _save_send_rows before this row has been appended to self.send_rows,
            # which would write an incomplete list to disk and lose the last row.
            row.id_edit.blockSignals(True)
            row.data_edit.blockSignals(True)
            row.id_edit.setText(entry.get("id", ""))
            row.data_edit.setText(entry.get("data", ""))
            row.id_edit.blockSignals(False)
            row.data_edit.blockSignals(False)
            row.ext_check.setChecked(bool(entry.get("ext", False)))
            row.rtr_check.setChecked(bool(entry.get("rtr", False)))
            self.send_rows.append(row)
            layout.insertWidget(layout.count() - 1, row)

        # Ensure at least _MIN_SEND_ROWS rows are always present
        while len(self.send_rows) < self._MIN_SEND_ROWS:
            i = len(self.send_rows)
            row = self._make_row(i)
            self.send_rows.append(row)
            layout.insertWidget(layout.count() - 1, row)


    def _disconnect(self):
        if self.rx_thread:
            self.rx_thread.stop()
            self.rx_thread = None

        if self.bus:
            try:
                self.bus.shutdown()
            except Exception:
                pass
            self.bus = None

        self._connected = False
        self._update_send_buttons(False)
        self.connect_btn.setText("Connect")
        self.connect_btn.setObjectName("primary")
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)

        self.status_dot.set_color(COLORS["text_dim"])
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        self._set_status("Disconnected")

    def _update_send_buttons(self, enabled: bool):
        for row in self.send_rows:
            row.send_btn.setEnabled(enabled)

    # ── Send row management ──────────────────────────────────────────────────

    def _insert_send_row(self):
        """Insert a new send row below the currently selected row (or at end)."""
        # Determine insertion index: after the selected row, or at end
        insert_after = len(self.send_rows) - 1  # default: append at end
        for i, row in enumerate(self.send_rows):
            if row.property("selected"):
                insert_after = i
                break

        insert_pos = insert_after + 1  # layout position (0-based within send rows)

        new_row = self._make_row(insert_pos)

        # Insert into data list
        self.send_rows.insert(insert_pos, new_row)

        # Insert into layout (before the stretch item at the end)
        layout = self._send_container_layout
        layout.insertWidget(insert_pos, new_row)

        # Re-number all rows
        self._renumber_send_rows()
        self._save_send_rows()

        # Select the newly inserted row
        self._select_send_row(new_row)

    def _delete_send_row(self):
        """Delete the currently selected send row (or the last row if none selected)."""
        if not self.send_rows:
            return

        # Find selected row
        target_idx = len(self.send_rows) - 1  # default: last row
        for i, row in enumerate(self.send_rows):
            if row.property("selected"):
                target_idx = i
                break

        row = self.send_rows.pop(target_idx)
        row.deleteLater()

        self._renumber_send_rows()
        self._save_send_rows()

        # Select the row now at the same position (or the last one)
        if self.send_rows:
            new_sel = min(target_idx, len(self.send_rows) - 1)
            self._select_send_row(self.send_rows[new_sel])

    def _select_send_row(self, target_row):
        """Track which send row is selected (no visual change)."""
        for row in self.send_rows:
            row.setProperty("selected", row is target_row)

    def _renumber_send_rows(self):
        """Update the row-number labels after inserts or deletes."""
        for i, row in enumerate(self.send_rows):
            row.index = i
            row.num_label.setText(f"{i + 1:02d}")

    # ── Sending ──────────────────────────────────────────────────────────────

    def _send_row(self, row: SendRow):
        if not self._connected or not self.bus:
            return

        frame_id = _parse_hex_id(row.id_edit.text())
        if frame_id is None:
            self._set_status("Invalid frame ID — enter a hex value e.g. F9 or 0x1F3", error=True)
            return

        is_ext = row.ext_check.isChecked()
        is_rtr = row.rtr_check.isChecked()

        max_id = 0x1FFFFFFF if is_ext else 0x7FF
        if frame_id > max_id:
            self._set_status(f"ID 0x{frame_id:X} out of range for {'extended' if is_ext else 'standard'} frame", error=True)
            return

        if is_rtr:
            data = b""
        else:
            data = _parse_hex_data(row.data_edit.text())
            if data is None:
                self._set_status("Invalid data — enter hex bytes separated by spaces e.g.  C0 E8 03 00 00", error=True)
                return
            if len(data) > 8:
                self._set_status("Max 8 data bytes", error=True)
                return

        try:
            msg = Message(
                arbitration_id=frame_id,
                data=data,
                dlc=len(data),
                is_extended_id=is_ext,
                is_remote_frame=is_rtr,
            )
            self.bus.send(msg)
            self._tx_count += 1
            self.tx_badge.increment()
            self._log_frame(msg, direction="TX")
            self._set_status(
                f"Sent  ID=0x{frame_id:X}  DLC={len(data)}  "
                f"Data={' '.join(f'{b:02X}' for b in data)}"
            )
        except Exception as exc:
            self._set_status(f"Send error: {exc}", error=True)

    # ── Receiving ─────────────────────────────────────────────────────────────

    def _on_rx_frame(self, msg):
        self._rx_count += 1
        self.rx_badge.increment()
        if not self.show_only_rx_check.isChecked():
            pass  # will be logged below
        self._log_frame(msg, direction="RX")

    # ── Log ───────────────────────────────────────────────────────────────────

    def _log_frame(self, msg, direction: str):
        if self.show_only_rx_check.isChecked() and direction != "RX":
            return

        row = self.log_table.rowCount()

        # Trim if too long
        if row >= self._MAX_LOG_ROWS:
            self.log_table.removeRow(0)
            row = self.log_table.rowCount()

        self.log_table.insertRow(row)
        total = self._tx_count + self._rx_count

        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        is_tx = direction == "TX"
        color = COLORS["amber"] if is_tx else COLORS["accent"]

        def cell(text, fg=None, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
            item = QTableWidgetItem(text)
            item.setTextAlignment(align)
            if fg:
                item.setForeground(QColor(fg))
            return item

        center = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter

        self.log_table.setItem(row, 0, cell(str(total), COLORS["text_dim"], center))
        self.log_table.setItem(row, 1, cell(ts, COLORS["text_muted"]))
        self.log_table.setItem(row, 2, cell(direction, color, center))
        self.log_table.setItem(row, 3, cell("EXT" if msg.is_extended_id else "STD", COLORS["text_muted"], center))
        self.log_table.setItem(row, 4, cell("RTR" if msg.is_remote_frame else "DATA", COLORS["text_muted"], center))
        self.log_table.setItem(row, 5, cell(f"0x{msg.arbitration_id:03X}", color))
        self.log_table.setItem(row, 6, cell(str(msg.dlc), COLORS["text_muted"], center))

        data_str = " ".join(f"{b:02X}" for b in msg.data) if msg.data else "—"
        self.log_table.setItem(row, 7, cell(data_str))
        self.log_table.setRowHeight(row, 28)

        if self._auto_scroll:
            self.log_table.scrollToBottom()

    def _clear_log(self):
        self.log_table.setRowCount(0)
        self._tx_count = 0
        self._rx_count = 0
        self.tx_badge.reset()
        self.rx_badge.reset()
        self._set_status("Log cleared")

    # ── Status bar ────────────────────────────────────────────────────────────

    def _set_status(self, msg: str, error: bool = False):
        color = COLORS["error"] if error else COLORS["text_muted"]
        self._status_msg.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._status_msg.setText(msg)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._disconnect()
        super().closeEvent(event)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Waveshare CAN Analyzer")
    app.setApplicationVersion("1.0")

    window = WaveshareCANApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()