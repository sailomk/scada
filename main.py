import sys
import random
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QFrame, QGridLayout, QPushButton)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap

# --- 1. Custom Gauge Widget (หน้าปัดวงกลมแบบในรูป) ---
class CircularGauge(QWidget):
    def __init__(self, label="LOAD", value=0, unit="%", color="#00d8d6"):
        super().__init__()
        self.label = label
        self.value = value
        self.unit = unit
        self.color = color
        self.setMinimumSize(150, 150)

    def set_value(self, val):
        self.value = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        side = min(width, height)
        rect = QRectF((width - side)/2 + 10, (height - side)/2 + 10, side - 20, side - 20)

        # Background Circle
        painter.setPen(QPen(QColor("#2c3e50"), 10))
        painter.drawEllipse(rect)
        
        # Progress Arc
        painter.setPen(QPen(QColor(self.color), 10, Qt.SolidLine, Qt.RoundCap))
        span_angle = int(-(self.value / 100 if self.unit == "%" else self.value / 500) * 360 * 16)
        painter.drawArc(rect, 90 * 16, span_angle)
        
        # Text
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{self.value}\n{self.unit}\n{self.label}")

# --- 2. Modbus Worker (ดึงข้อมูลแยก Thread) ---
class ModbusWorker(QThread):
    data_received = Signal(dict)

    def run(self):
        # ในการใช้งานจริง ให้ยกเลิกคอมเมนต์บรรทัดด้านล่างและระบุ IP/Port
        # from pymodbus.client import ModbusTcpClient
        # client = ModbusTcpClient('127.0.0.1', port=502)
        
        while True:
            # จำลองข้อมูล (Simulation Mode)
            # ในงานจริง: result = client.read_holding_registers(0, 10, slave=1)
            mock_data = {
                "Kilowatts/Hour:": f"{random.uniform(400000, 420000):,.2f} kW-hr",
                "Kilowatts:": f"{random.uniform(180, 200):.2f} kW",
                "Phase-1 Volt R:": f"{random.uniform(350, 360):.2f} V",
                "Phase-2 Volt S:": f"{random.uniform(350, 360):.2f} V",
                "Phase-3 Volt T:": f"{random.uniform(350, 360):.2f} V",
                "Frequency:": f"{random.uniform(49.5, 50.5):.2f} Hz",
                "Phase-1 Current:": f"{random.uniform(430, 440):.2f} A",
                "LoadValue": random.randint(70, 95),
                "CoolingValue": random.randint(120, 140)
            }
            self.data_received.emit(mock_data)
            self.msleep(1000)

# --- 3. Main Application UI ---
class ChillerDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin - Chiller Control System")
        self.resize(1280, 800)
        self.init_ui()
        
        # Start Worker
        self.worker = ModbusWorker()
        self.worker.data_received.connect(self.update_dashboard)
        self.worker.start()

    def init_ui(self):
        # Global Style
        self.setStyleSheet("""
            QMainWindow { background-color: #0d1117; }
            QFrame#DataCard { 
                background-color: #161b22; 
                border: 1px solid #30363d; 
                border-radius: 8px; 
                padding: 10px;
            }
            QLabel { color: #c9d1d9; font-family: 'Segoe UI'; }
            .Title { color: #ffffff; font-size: 18px; font-weight: bold; margin-bottom: 10px; }
            .Value { color: #58a6ff; font-family: 'Consolas'; font-size: 14px; font-weight: bold; }
            QPushButton { 
                background-color: #21262d; border: 1px solid #30363d; 
                color: white; padding: 8px; border-radius: 4px; text-align: left;
            }
            QPushButton:hover { background-color: #30363d; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Sidebar ---
        sidebar = QVBoxLayout()
        sidebar.setSpacing(10)
        nav_items = ["CHILLER PLANT", "CH01 DETAIL", "CH02 DETAIL", "CH03 DETAIL", "CDP DETAIL"]
        for item in nav_items:
            btn = QPushButton(item)
            if item == "CH01 DETAIL":
                btn.setStyleSheet("background-color: #238636; border: none;")
            sidebar.addWidget(btn)
        sidebar.addStretch()
        main_layout.addLayout(sidebar, 1)

        # --- Center Section ---
        center_layout = QVBoxLayout()
        header = QLabel("CHILLER NO.1 DETAIL")
        header.setProperty("class", "Title")
        center_layout.addWidget(header)

        # Chiller Image
        self.chiller_img = QLabel()
        self.chiller_img.setPixmap(QPixmap("chiller.jpg").scaled(500, 400, Qt.KeepAspectRatio))
        self.chiller_img.setText("[ CHILLER 3D GRAPHIC ]")
        self.chiller_img.setAlignment(Qt.AlignCenter)
        self.chiller_img.setStyleSheet("background: #161b22; border-radius: 15px; margin: 20px;")
        center_layout.addWidget(self.chiller_img)

        # Gauges Row
        gauge_layout = QHBoxLayout()
        self.load_gauge = CircularGauge(" % LOAD", 0, "%", "#00d8d6")
        self.cooling_gauge = CircularGauge("COOLING LOAD", 0, "ton", "#ff9f43")
        gauge_layout.addWidget(self.load_gauge)
        gauge_layout.addWidget(self.cooling_gauge)
        center_layout.addLayout(gauge_layout)
        
        main_layout.addLayout(center_layout, 3)

        # --- Right Section (Tables) ---
        right_layout = QVBoxLayout()
        
        # Table Containers
        self.value_labels = {}
        
        # Power Status
        right_layout.addWidget(self.create_data_group("POWER STATUS", [
            "Kilowatts/Hour:", "Kilowatts:", "Phase-1 Volt R:", "Phase-2 Volt S:", "Phase-3 Volt T:", "Frequency:"
        ]))
        
        # Amp Status
        right_layout.addWidget(self.create_data_group("AMP STATUS", [
            "Phase-1 Current:"
        ]))
        
        main_layout.addLayout(right_layout, 2)

    def create_data_group(self, title, fields):
        frame = QFrame()
        frame.setObjectName("DataCard")
        layout = QGridLayout(frame)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #79c0ff; font-weight: bold; font-size: 14px;")
        layout.addWidget(title_lbl, 0, 0, 1, 2)

        for i, field in enumerate(fields, 1):
            name_lbl = QLabel(field)
            val_lbl = QLabel("---")
            val_lbl.setProperty("class", "Value")
            val_lbl.setAlignment(Qt.AlignRight)
            
            layout.addWidget(name_lbl, i, 0)
            layout.addWidget(val_lbl, i, 1)
            self.value_labels[field] = val_lbl
            
        return frame

    def update_dashboard(self, data):
        # Update Table Values
        for field, value in data.items():
            if field in self.value_labels:
                self.value_labels[field].setText(value)
        
        # Update Gauges
        if "LoadValue" in data:
            self.load_gauge.set_value(data["LoadValue"])
        if "CoolingValue" in data:
            self.cooling_gauge.set_value(data["CoolingValue"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChillerDashboard()
    window.showMaximized()
    sys.exit(app.exec())
