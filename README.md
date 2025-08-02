# IoT-Based Real-Time Energy Monitoring and Dashboard

## 📌 Project Overview

This project presents a cost-effective IoT-based system to monitor real-time energy consumption of a household appliance (e.g., refrigerator) using a **Tuya-compatible smart plug**. The system collects and processes power, voltage, and current data using Python, displays it on a dynamic dashboard, and allows **remote device control** via Cloudflare Tunnel.

---

## ⚙️ System Components

- **Smart Plug**: Tuya-compatible, 100–250V, 20A max load
- **Backend**: Python + Flask
- **Frontend**: HTML, CSS, JavaScript, Chart.js
- **API Access**: Local key via TinyTuya
- **Remote Access**: Cloudflare Tunnel with custom domain

---

## 🚀 Features

- Real-time monitoring of:
  - Power (W)
  - Voltage (V)
  - Current (A)
- Historical consumption view (daily kWh)
- ON/OFF control from dashboard
- Secure global access via HTTPS
- Local JSON data logging
- Intuitive UI for non-technical users

---

## 📁 Project Structure
├── app.py # Main Flask server
├── dashboard/
│ ├── templates/ # HTML files
│ ├── static/ # CSS/JS/Chart.js
│ └── manual.pdf # User manual
├── utils/
│ └── energy_logger.py # Data capture & processing
├── data/
│ └── energy_logs.json # Logged data (auto-generated)
├── cloudflare_config.yaml # Cloudflare Tunnel config (optional)
└── README.md


---

## 🧪 Requirements

- Python 3.8+
- Flask
- TinyTuya
- Chart.js (linked via CDN)
- Cloudflare Tunnel (optional, for remote access)

## Install Python dependencies:
pip install flask tinytuya

