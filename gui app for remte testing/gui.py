#!/usr/bin/env python3
"""
@file: gui_test.py
@brief: GUI application for the real time parameter tuning and monitoring of an EV charger using XCP protocol.
@author: Nishan Dananjaya
@date: 2025-06-26
@version: 1.0

XCP Parameter Tuning GUI Application

This application provides a GUI for monitoring and tuning parameters via WebSocket.
The WebSocket server provides remote access to parameter functionality.
"""

import sys
import time
import numpy as np
import json
import os
from PyQt5 import QtCore
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QFormLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QTabWidget, 
                             QTableWidget, QTableWidgetItem, QSpinBox, 
                             QDoubleSpinBox, QCheckBox, QSplitter, QFileDialog,
                             QMessageBox, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread
import pyqtgraph as pg
import threading
from websocket_server_test import WebSocketServer

PARAMETER_DEFS = [
    {"name": "INPUT_VOLTAGE", "address": 0x20000000, "size": 4, "type": "float", "min": 0, "max": 1000, "description": "Input AC voltage (V)"},
    {"name": "INPUT_CURRENT", "address": 0x20000004, "size": 4, "type": "float", "min": 0, "max": 100, "description": "Input AC current (A)"},
    {"name": "OUTPUT_VOLTAGE", "address": 0x20000008, "size": 4, "type": "float", "min": 0, "max": 1000, "description": "Output DC voltage (V)"},
    {"name": "OUTPUT_CURRENT", "address": 0x2000000C, "size": 4, "type": "float", "min": 0, "max": 500, "description": "Output DC current (A)"},
    {"name": "TEMPERATURE", "address": 0x20000010, "size": 4, "type": "float", "min": -20, "max": 100, "description": "Charger temperature (°C)"},
    {"name": "CHARGE_RATE", "address": 0x20000014, "size": 4, "type": "float", "min": 0, "max": 100, "description": "Charge rate (kW)"},
    {"name": "EFFICIENCY", "address": 0x20000018, "size": 4, "type": "float", "min": 0, "max": 100, "description": "Charging efficiency (%)"},
    {"name": "STATE_OF_CHARGE", "address": 0x2000001C, "size": 4, "type": "float", "min": 0, "max": 100, "description": "Battery state of charge (%)"},
    {"name": "CHARGE_TIME", "address": 0x20000020, "size": 4, "type": "float", "min": 0, "max": 1440, "description": "Elapsed charge time (minutes)"},
    {"name": "REMAINING_TIME", "address": 0x20000024, "size": 4, "type": "float", "min": 0, "max": 1440, "description": "Estimated remaining charge time (minutes)"}
]

class ParameterMonitorThread(QThread):
    """Thread for monitoring parameter values"""
    
    new_values = pyqtSignal(dict)
    
    def __init__(self, parameter_defs, update_interval=100):
        super().__init__()
        self.parameter_defs = parameter_defs
        self.update_interval = update_interval
        self.running = False
        
    def run(self):
        self.running = True
        while self.running:
            values = {}
            for param in self.parameter_defs:
                if param["type"] == "float":
                    value = np.random.uniform(param["min"], param["max"])
                elif param["type"] == "uint16":
                    value = np.random.randint(param["min"], param["max"])
                else:  # uint8
                    value = np.random.randint(param["min"], param["max"])
                
                values[param["name"]] = value
                
            if values:
                self.new_values.emit(values)
                
            time.sleep(self.update_interval / 1000.0)
            
    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Parameter Tuning Server - EV Charger")
        self.setMinimumSize(1200, 900)
        
        self.ws_server = WebSocketServer(port=8000)
        self.ws_server.register_value_callback(self.handle_value_update)
        self.ws_server.register_connection_callback(self.handle_connection_change)
        self.server_running = False
        self.client_connected = False
        
        self.history_length = 200
        self.parameter_history = {}
        self.time_values = np.zeros(self.history_length)
        
        for param in PARAMETER_DEFS:
            self.parameter_history[param["name"]] = np.zeros(self.history_length)
            
        self.init_ui()
        
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plots)
        self.plot_timer.start(100)
    
    def handle_value_update(self, values):
        if self.client_connected:
            self.update_parameter_displays(values)

    def handle_connection_change(self, connected):
        self.client_connected = connected
        status = "connected" if connected else "disconnected"
        self.log_message(f"Client {status}")
        self.statusBar().showMessage(f"Client {status}")

    def init_ui(self):
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        
        server_group = QGroupBox("Server Control")
        server_layout = QVBoxLayout()
        
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("WebSocket Port:"))
        self.ws_port_input = QLineEdit("8000")
        self.ws_port_input.setMaximumWidth(80)
        settings_layout.addWidget(self.ws_port_input)
        
        settings_layout.addStretch()
        server_layout.addLayout(settings_layout)
        
        buttons_layout = QHBoxLayout()
        
        self.start_server_button = QPushButton("Start Server")
        self.start_server_button.clicked.connect(self.toggle_server)
        self.start_server_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        buttons_layout.addWidget(self.start_server_button)
        
        self.server_status_label = QLabel("Server Status: Stopped")
        self.server_status_label.setStyleSheet("color: red; font-weight: bold;")
        buttons_layout.addWidget(self.server_status_label)
        
        buttons_layout.addStretch()
        server_layout.addLayout(buttons_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Server logs will appear here...")
        server_layout.addWidget(QLabel("Server Log:"))
        server_layout.addWidget(self.log_text)
        
        server_group.setLayout(server_layout)
        self.main_layout.addWidget(server_group)
        
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        self.params_tab = QWidget()
        params_layout = QVBoxLayout(self.params_tab)
        
        self.param_table = QTableWidget()
        self.param_table.setColumnCount(6)
        self.param_table.setHorizontalHeaderLabels(["Parameter", "Address", "Description", "Value", "Unit", "Set Value"])
        self.param_table.horizontalHeader().setStretchLastSection(True)
        self.param_table.setColumnWidth(1, 100)
        self.param_table.setColumnWidth(2, 200)
        
        self.param_table.setRowCount(len(PARAMETER_DEFS))
        self.param_controls = {}
        
        for i, param in enumerate(PARAMETER_DEFS):
            self.param_table.setItem(i, 0, QTableWidgetItem(param["name"]))
            self.param_table.setItem(i, 1, QTableWidgetItem(f"0x{param['address']:08X}"))
            self.param_table.setItem(i, 2, QTableWidgetItem(param.get("description", "")))
            
            value_item = QTableWidgetItem()
            value_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.param_table.setItem(i, 3, value_item)
            
            unit = ""
            if "VOLTAGE" in param["name"]:
                unit = "V"
            elif "CURRENT" in param["name"]:
                unit = "A"
            elif "TEMPERATURE" in param["name"]:
                unit = "°C"
            elif "EFFICIENCY" in param["name"] or "STATE_OF_CHARGE" in param["name"]:
                unit = "%"
            elif "CHARGE_RATE" in param["name"]:
                unit = "kW"
            elif "TIME" in param["name"]:
                unit = "min"
            self.param_table.setItem(i, 4, QTableWidgetItem(unit))
            
            if param["type"] == "float":
                control = QDoubleSpinBox()
                control.setDecimals(3)
                control.setSingleStep(0.1)
                control.setRange(param["min"], param["max"])
            else:
                control = QSpinBox()
                control.setRange(param["min"], param["max"])
                
            control.valueChanged.connect(lambda v, n=param["name"]: self.parameter_changed(n, v))
            self.param_table.setCellWidget(i, 5, control)
            self.param_controls[param["name"]] = control
            
        params_layout.addWidget(self.param_table)
        
        param_buttons_layout = QHBoxLayout()
        
        self.read_all_button = QPushButton("Read All")
        self.read_all_button.clicked.connect(self.read_all_parameters)
        param_buttons_layout.addWidget(self.read_all_button)
        
        self.write_selected_button = QPushButton("Write Selected")
        self.write_selected_button.clicked.connect(self.write_selected_parameters)
        param_buttons_layout.addWidget(self.write_selected_button)
        
        self.save_config_button = QPushButton("Save Config")
        self.save_config_button.clicked.connect(self.save_parameter_config)
        param_buttons_layout.addWidget(self.save_config_button)
        
        self.load_config_button = QPushButton("Load Config")
        self.load_config_button.clicked.connect(self.load_parameter_config)
        param_buttons_layout.addWidget(self.load_config_button)
        
        params_layout.addLayout(param_buttons_layout)
        
        self.monitoring_tab = QWidget()
        monitoring_layout = QVBoxLayout(self.monitoring_tab)
        
        self.plots = {}
        self.plot_curves = {}
        
        splitter = QSplitter(Qt.Vertical)
        
        charger_group = QGroupBox("Charger Parameters")
        charger_layout = QVBoxLayout()
        
        charger_plot = pg.PlotWidget()
        charger_plot.setLabel('left', 'Value')
        charger_plot.setLabel('bottom', 'Time (s)')
        charger_plot.showGrid(x=True, y=True)
        charger_plot.addLegend()
        charger_layout.addWidget(charger_plot)
        
        for param_name in ["INPUT_VOLTAGE", "INPUT_CURRENT", "OUTPUT_VOLTAGE", "OUTPUT_CURRENT"]:
            curve = charger_plot.plot(pen=pg.mkPen(color=pg.intColor(len(self.plot_curves)), width=2), name=param_name)
            self.plot_curves[param_name] = curve
            
        charger_group.setLayout(charger_layout)
        splitter.addWidget(charger_group)
        
        battery_group = QGroupBox("Battery Parameters")
        battery_layout = QVBoxLayout()
        
        battery_plot = pg.PlotWidget()
        battery_plot.setLabel('left', 'Value')
        battery_plot.setLabel('bottom', 'Time (s)')
        battery_plot.showGrid(x=True, y=True)
        battery_plot.addLegend()
        battery_layout.addWidget(battery_plot)
        
        for param_name in ["STATE_OF_CHARGE", "CHARGE_RATE", "EFFICIENCY"]:
            curve = battery_plot.plot(pen=pg.mkPen(color=pg.intColor(len(self.plot_curves)), width=2), name=param_name)
            self.plot_curves[param_name] = curve
            
        battery_group.setLayout(battery_layout)
        splitter.addWidget(battery_group)
        
        system_group = QGroupBox("System Parameters")
        system_layout = QVBoxLayout()
        
        system_plot = pg.PlotWidget()
        system_plot.setLabel('left', 'Value')
        system_plot.setLabel('bottom', 'Time (s)')
        system_plot.showGrid(x=True, y=True)
        system_plot.addLegend()
        system_layout.addWidget(system_plot)
        
        for param_name in ["TEMPERATURE", "CHARGE_TIME", "REMAINING_TIME"]:
            curve = system_plot.plot(pen=pg.mkPen(color=pg.intColor(len(self.plot_curves)), width=2), name=param_name)
            self.plot_curves[param_name] = curve
            
        system_group.setLayout(system_layout)
        splitter.addWidget(system_group)
        
        monitoring_layout.addWidget(splitter)
        
        monitor_controls_layout = QHBoxLayout()
        
        self.start_monitor_button = QPushButton("Start Monitoring")
        self.start_monitor_button.clicked.connect(self.toggle_monitoring)
        monitor_controls_layout.addWidget(self.start_monitor_button)
        
        self.clear_plots_button = QPushButton("Clear Plots")
        self.clear_plots_button.clicked.connect(self.clear_plots)
        monitor_controls_layout.addWidget(self.clear_plots_button)
        
        self.save_plots_button = QPushButton("Save Plots")
        self.save_plots_button.clicked.connect(self.save_plots)
        monitor_controls_layout.addWidget(self.save_plots_button)
        
        monitoring_layout.addLayout(monitor_controls_layout)
        
        self.api_tab = QWidget()
        api_layout = QVBoxLayout(self.api_tab)
        
        api_info = QTextEdit()
        api_info.setReadOnly(True)
        api_info.setHtml("""
        <h2>WebSocket API Documentation</h2>
        <p>The server provides a JSON-over-TCP API for reading and writing parameters.</p>
        
        <h3>Connection</h3>
        <p>Connect to: <code>localhost:8000</code> (or the configured port)</p>
        
        <h3>Commands</h3>
        
        <h4>Read Parameter</h4>
        <pre>{
        "command": "read",
        "params": {
            "address": 0x20000000,
            "size": 4
        }
    }</pre>
        
        <h4>Write Parameter</h4>
        <pre>{
        "command": "write",
        "params": {
            "address": 0x20000000,
            "value": 1.234,
            "size": 4
        }
    }</pre>
        
        <h3>Parameter Addresses</h3>
        <table border="1" cellpadding="5">
        <tr><th>Parameter</th><th>Address</th><th>Size</th><th>Type</th></tr>
        <tr><td>INPUT_VOLTAGE</td><td>0x20000000</td><td>4</td><td>float</td></tr>
        <tr><td>INPUT_CURRENT</td><td>0x20000004</td><td>4</td><td>float</td></tr>
        <tr><td>OUTPUT_VOLTAGE</td><td>0x20000008</td><td>4</td><td>float</td></tr>
        <tr><td>OUTPUT_CURRENT</td><td>0x2000000C</td><td>4</td><td>float</td></tr>
        <tr><td>TEMPERATURE</td><td>0x20000010</td><td>4</td><td>float</td></tr>
        <tr><td>CHARGE_RATE</td><td>0x20000014</td><td>4</td><td>float</td></tr>
        <tr><td>EFFICIENCY</td><td>0x20000018</td><td>4</td><td>float</td></tr>
        <tr><td>STATE_OF_CHARGE</td><td>0x2000001C</td><td>4</td><td>float</td></tr>
        <tr><td>CHARGE_TIME</td><td>0x20000020</td><td>4</td><td>float</td></tr>
        <tr><td>REMAINING_TIME</td><td>0x20000024</td><td>4</td><td>float</td></tr>
        </table>
        
        <h3>Example Client (Python)</h3>
        <pre>import socket
    import json

    sock = socket.socket()
    sock.connect(('localhost', 8000))

    # Read INPUT_VOLTAGE parameter
    cmd = {"command": "read", "params": {"address": 0x20000000, "size": 4}}
    sock.send(json.dumps(cmd).encode())
    response = json.loads(sock.recv(1024).decode())
    print(f"INPUT_VOLTAGE value: {response['value']}")

    sock.close()</pre>
        """)
        
        api_layout.addWidget(api_info)
        
        self.tabs.addTab(self.params_tab, "Parameters")
        self.tabs.addTab(self.monitoring_tab, "Monitoring")
        self.tabs.addTab(self.api_tab, "API Documentation")
        
        self.setCentralWidget(self.main_widget)
        
        self.monitor_thread = ParameterMonitorThread(PARAMETER_DEFS)
        self.monitor_thread.new_values.connect(self.update_parameter_displays)
        
        self.update_ui_state(False)
        
    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def update_ui_state(self, server_running):
        if server_running:
            self.start_server_button.setText("Stop Server")
            self.start_server_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
                QPushButton:pressed {
                    background-color: #b71c1c;
                }
            """)
            self.server_status_label.setText("Server Status: Running")
            self.server_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.read_all_button.setEnabled(True)
            self.write_selected_button.setEnabled(True)
            self.start_monitor_button.setEnabled(True)
            
            self.ws_port_input.setEnabled(False)
        else:
            self.start_server_button.setText("Start Server")
            self.start_server_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #3e8e41;
                }
            """)
            self.server_status_label.setText("Server Status: Stopped")
            self.server_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.read_all_button.setEnabled(False)
            self.write_selected_button.setEnabled(False)
            self.start_monitor_button.setEnabled(False)
            
            self.ws_port_input.setEnabled(True)
            
            if hasattr(self, 'monitor_thread') and self.monitor_thread.running:
                self.toggle_monitoring()
                
    def toggle_server(self):
        if not self.server_running:
            try:
                ws_port = int(self.ws_port_input.text())
            except ValueError:
                QMessageBox.warning(self, "Invalid Port", "Please enter a valid port number")
                return
                
            self.log_message("Starting server...")
            
            self.ws_server.port = ws_port
                
            try:
                threading.Thread(target=self.ws_server.start, daemon=True).start()
                self.server_running = True
                self.update_ui_state(True)
                self.log_message(f"WebSocket server started on port {ws_port}")
                self.statusBar().showMessage(f"Server running - WebSocket: {ws_port}")
            except Exception as e:
                self.log_message(f"Failed to start WebSocket server: {str(e)}")
                QMessageBox.warning(self, "Server Error", f"Failed to start WebSocket server: {str(e)}")
                self.update_ui_state(False)
        else:
            self.log_message("Stopping server...")
            
            if hasattr(self, 'monitor_thread') and self.monitor_thread.running:
                self.toggle_monitoring()
                
            try:
                self.ws_server.stop()
                self.log_message("WebSocket server stopped")
            except Exception as e:
                self.log_message(f"Error stopping WebSocket server: {str(e)}")
            
            self.server_running = False
            self.update_ui_state(False)
            self.statusBar().showMessage("Server stopped")
            
    def toggle_monitoring(self):
        if not self.monitor_thread.running:
            if not self.client_connected:
                QMessageBox.information(self, "No Client", 
                                      "No client connected - showing simulated values")
            self.monitor_thread.start()
            self.start_monitor_button.setText("Stop Monitoring")
            self.log_message("Parameter monitoring started")
        else:
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            self.start_monitor_button.setText("Start Monitoring")
            self.log_message("Parameter monitoring stopped")
            
    def update_parameter_displays(self, values):
        for i, param in enumerate(PARAMETER_DEFS):
            name = param["name"]
            if name in values:
                value = values[name]
                
                if param["type"] == "float":
                    display_value = f"{value:.3f}"
                else:
                    display_value = str(value)
                
                self.param_table.item(i, 3).setText(display_value)
                
                self.parameter_history[name][:-1] = self.parameter_history[name][1:]
                self.parameter_history[name][-1] = value
                
    def update_plots(self):
        current_time = time.time()
        if self.time_values[0] == 0:
            self.time_values[:] = current_time
        else:
            self.time_values[:-1] = self.time_values[1:]
            self.time_values[-1] = current_time
        
        relative_time = self.time_values - self.time_values[0]
        
        for name, curve in self.plot_curves.items():
            curve.setData(relative_time, self.parameter_history[name])
            
    def clear_plots(self):
        for name in self.parameter_history:
            self.parameter_history[name][:] = 0
            
        self.time_values[:] = 0
        self.update_plots()
        self.log_message("Plot data cleared")
        
    def save_plots(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Plot Data",
                                                 os.path.expanduser("~") + "/plot_data.csv",
                                                 "CSV Files (*.csv)")
        if not file_path:
            return
            
        try:
            with open(file_path, 'w') as f:
                f.write("Time")
                for param in PARAMETER_DEFS:
                    f.write(f",{param['name']}")
                f.write("\n")
                
                for i in range(self.history_length):
                    f.write(f"{self.time_values[i]}")
                    for param in PARAMETER_DEFS:
                        f.write(f",{self.parameter_history[param['name']][i]}")
                    f.write("\n")
                    
            self.log_message(f"Plot data saved to {file_path}")
            self.statusBar().showMessage(f"Plot data saved to {file_path}")
        except Exception as e:
            self.log_message(f"Error saving plot data: {str(e)}")
            QMessageBox.warning(self, "Save Error", f"Error saving plot data: {str(e)}")
        
    def read_all_parameters(self):
        if not self.server_running:
            return
            
        values = {}
        for param in PARAMETER_DEFS:
            if param["type"] == "float":
                value = np.random.uniform(param["min"], param["max"])
            elif param["type"] == "uint16":
                value = np.random.randint(param["min"], param["max"])
            else:  # uint8
                value = np.random.randint(param["min"], param["max"])
                
            values[param["name"]] = value
                
            if param["name"] in self.param_controls:
                control = self.param_controls[param["name"]]
                control.blockSignals(True)
                control.setValue(value)
                control.blockSignals(False)
                
        self.update_parameter_displays(values)
        self.log_message("All parameters read successfully")
        
    def write_selected_parameters(self):
        if not self.server_running:
            return
            
        selected_rows = self.param_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select parameters to write")
            return
            
        success_count = 0
        for row in selected_rows:
            i = row.row()
            param = PARAMETER_DEFS[i]
            control = self.param_controls[param["name"]]
            value = control.value()
            
            success_count += 1
            self.log_message(f"Parameter {param['name']} written: {value}")
                    
        self.log_message(f"Written {success_count} of {len(selected_rows)} selected parameters")
        
    def parameter_changed(self, param_name, value):
        pass
        
    def save_parameter_config(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Parameter Configuration",
                                                os.path.expanduser("~") + "/xcp_config.json",
                                                "JSON Files (*.json)")
        if not file_path:
            return
            
        try:
            config = {}
            for param in PARAMETER_DEFS:
                if param["name"] in self.param_controls:
                    control = self.param_controls[param["name"]]
                    config[param["name"]] = {
                        "value": control.value(),
                        "address": param["address"],
                        "type": param["type"],
                        "size": param["size"]
                    }
                    
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.log_message(f"Configuration saved to {file_path}")
            self.statusBar().showMessage(f"Configuration saved to {file_path}")
        except Exception as e:
            self.log_message(f"Error saving configuration: {str(e)}")
            QMessageBox.warning(self, "Save Error", f"Error saving configuration: {str(e)}")
                
    def load_parameter_config(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Parameter Configuration",
                                                os.path.expanduser("~"),
                                                "JSON Files (*.json)")
        if not file_path:
            return
            
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
                
            loaded_count = 0
            for param_name, param_config in config.items():
                if param_name in self.param_controls:
                    control = self.param_controls[param_name]
                    control.blockSignals(True)
                    control.setValue(param_config["value"])
                    control.blockSignals(False)
                    loaded_count += 1
                    
            self.log_message(f"Configuration loaded from {file_path} ({loaded_count} parameters)")
            self.statusBar().showMessage(f"Configuration loaded: {loaded_count} parameters")
        except Exception as e:
            self.log_message(f"Error loading configuration: {str(e)}")
            QMessageBox.warning(self, "Load Error", f"Error loading configuration: {str(e)}")
                
    def closeEvent(self, event):
        if self.server_running:
            reply = QMessageBox.question(self, 'Close Application',
                                    'Server is running. Stop server and close?',
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.toggle_server()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Parameter Tuning Server")
    app.setApplicationVersion("1.0")
    
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    window.statusBar().showMessage("Ready - Configure settings and start server")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()