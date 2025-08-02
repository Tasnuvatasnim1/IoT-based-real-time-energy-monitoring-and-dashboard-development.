from flask import Flask, render_template, jsonify, request, redirect, url_for
import tinytuya
import time
from datetime import datetime, timedelta
import json
import os
import threading
from collections import defaultdict
from functools import lru_cache

# Configuration - can be set via environment variables
DEVICE_ID = os.getenv('DEVICE_ID', 'bf493814f4d1067dcbqvx5')
LOCAL_KEY = os.getenv('LOCAL_KEY', 'b_L?wvt`9AO=dJ&}')
VERSION = os.getenv('VERSION', '3.5')

# Initialize Flask
app = Flask(__name__, template_folder='templates')
JSON_FILE = 'energy_data.json'
STORAGE_INTERVAL = 300  # 5 minutes
file_lock = threading.Lock()

# Device initialization with auto-discovery
def initialize_device():
    try:
        # First try to get IP from environment variable
        device_ip = os.getenv('DEVICE_IP', '')
        
        if not device_ip:
            print("Discovering device IP...")
            devices = tinytuya.deviceScan()
            for ip, device_info in devices.items():
                if device_info.get('gwId') == DEVICE_ID:
                    device_ip = ip
                    print(f"Discovered device at IP: {device_ip}")
                    break
            
            if not device_ip:
                raise Exception("Device not found on network")

        device = tinytuya.OutletDevice(DEVICE_ID, device_ip, LOCAL_KEY)
        device.set_version(float(VERSION))
        return device
    except Exception as e:
        print(f"Device initialization error: {e}")
        return None

device = initialize_device()

def init_files():
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')
    if not os.path.exists(JSON_FILE):
        with file_lock:
            with open(JSON_FILE, 'w') as f:
                json.dump([], f)

@lru_cache(maxsize=1, typed=False)
def get_cached_device_status():
    """Cache device status for 10 seconds to reduce direct device calls"""
    if not device:
        return {}
    try:
        return device.status().get('dps', {})
    except:
        return {}

def save_energy_data(data):
    try:
        with file_lock:
            with open(JSON_FILE, 'r') as f:
                existing_data = json.load(f)
            
            entry = {
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'current_ma': data.get('18', 0),
                    'power_w': data.get('19', 0) / 10,
                    'voltage_v': data.get('20', 0) / 10,
                    'total_kwh': data.get('17', 0) / 1000,
                    'is_on': bool(data.get('1', False))
                }
            }
            
            existing_data.append(entry)
            
            # Keep only last 30 days of data
            cutoff = datetime.now() - timedelta(days=30)
            existing_data = [
                entry for entry in existing_data 
                if datetime.fromisoformat(entry['timestamp']) > cutoff
            ]
            
            with open(JSON_FILE, 'w') as f:
                json.dump(existing_data, f)
    except Exception as e:
        print(f"Error saving data: {e}")

def get_historical_data(days=1):
    try:
        with file_lock:
            with open(JSON_FILE, 'r') as f:
                all_data = json.load(f)
        
        cutoff = datetime.now() - timedelta(days=days)
        recent_data = [
            entry for entry in all_data 
            if datetime.fromisoformat(entry['timestamp']) > cutoff
        ]
        
        daily_data = defaultdict(lambda: {'power': [], 'voltage': [], 'current': [], 'timestamps': []})
        
        for entry in recent_data:
            date = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d')
            daily_data[date]['power'].append(entry['data']['power_w'])
            daily_data[date]['voltage'].append(entry['data']['voltage_v'])
            daily_data[date]['current'].append(entry['data']['current_ma'])
            daily_data[date]['timestamps'].append(entry['timestamp'])
        
        return daily_data
    except Exception as e:
        print(f"Error reading data: {e}")
        return {}

def analyze_data(data):
    analysis = {}
    for date, values in data.items():
        if values['power']:
            analysis[date] = {
                'power': {
                    'avg': round(sum(values['power'])/len(values['power']), 2),
                    'max': round(max(values['power']), 2),
                    'min': round(min(values['power']), 2)
                },
                'voltage': {
                    'avg': round(sum(values['voltage'])/len(values['voltage']), 2),
                    'max': round(max(values['voltage']), 2),
                    'min': round(min(values['voltage']), 2)
                },
                'current': {
                    'avg': round(sum(values['current'])/len(values['current'])/1000, 3),
                    'max': round(max(values['current'])/1000, 3),
                    'min': round(min(values['current'])/1000, 3)
                }
            }
    return analysis

def monitor_energy():
    init_files()
    last_save_time = time.time()
    while True:
        try:
            if time.time() - last_save_time >= STORAGE_INTERVAL:
                # Clear cache to get fresh device data
                get_cached_device_status.cache_clear()
                data = get_cached_device_status()
                if data:  # Only save if we got data
                    save_energy_data(data)
                    last_save_time = time.time()
            time.sleep(60)
        except Exception as e:
            print(f"Monitoring error: {e}")

monitor_thread = threading.Thread(target=monitor_energy)
monitor_thread.daemon = True
monitor_thread.start()

@app.route('/')
def index():
    try:
        # Get the most recent data from JSON instead of querying device
        with file_lock:
            with open(JSON_FILE, 'r') as f:
                all_data = json.load(f)
        
        if all_data:
            latest = all_data[-1]['data']
            return render_template('dashboard.html',
                                is_on=latest['is_on'],
                                current_ma=latest['current_ma'],
                                power_w=latest['power_w'],
                                voltage_v=latest['voltage_v'],
                                total_kwh=latest['total_kwh'])
        
        # Fallback to device if no data exists
        data = get_cached_device_status()
        return render_template('dashboard.html',
                            is_on=bool(data.get('1', False)),
                            current_ma=data.get('18', 0),
                            power_w=data.get('19', 0)/10,
                            voltage_v=data.get('20', 0)/10,
                            total_kwh=data.get('17', 0)/1000)
    except Exception as e:
        print(f"Dashboard error: {e}")
        return render_template('dashboard.html',
                            is_on=None,
                            current_ma=0,
                            power_w=0,
                            voltage_v=0,
                            total_kwh=0)

@app.route('/live_data')
def live_data():
    try:
        # Use cached device status (refreshes every 10 seconds)
        data = get_cached_device_status()
        return jsonify({
            'is_on': bool(data.get('1', False)),
            'power': float(data.get('19', 0))/10,
            'voltage': float(data.get('20', 0))/10,
            'current': float(data.get('18', 0)),
            'total_kwh': float(data.get('17', 0))/1000
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def history():
    try:
        days = int(request.args.get('days', 7))
        historical_data = get_historical_data(days)
        analysis = analyze_data(historical_data)
        return render_template('history.html', analysis=analysis)
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/historical_data')
def historical_data():
    try:
        date = request.args.get('date')
        with file_lock:
            with open(JSON_FILE, 'r') as f:
                all_data = json.load(f)
        
        selected_data = [
            entry for entry in all_data 
            if datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d') == date
        ]
        
        if not selected_data:
            return jsonify({'error': 'No data for selected date'}), 404
        
        total_watt_hours = 0
        previous_time = None
        previous_power = None
        
        for entry in selected_data:
            current_time = datetime.fromisoformat(entry['timestamp'])
            power = entry['data']['power_w']
            
            if previous_time and previous_power is not None:
                time_diff_hours = (current_time - previous_time).total_seconds() / 3600
                total_watt_hours += (previous_power + power) / 2 * time_diff_hours
            
            previous_time = current_time
            previous_power = power
        
        total_kwh = round(total_watt_hours / 1000, 3)
        
        return jsonify({
            'timestamps': [datetime.fromisoformat(e['timestamp']).strftime('%H:%M') for e in selected_data],
            'power': [e['data']['power_w'] for e in selected_data],
            'voltage': [e['data']['voltage_v'] for e in selected_data],
            'current': [e['data']['current_ma']/1000 for e in selected_data],
            'total_kwh': total_kwh
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/manual')
def manual():
    return render_template('manual.html')

@app.route('/on')
def turn_on():
    if device:
        device.set_status(True, '1')
        get_cached_device_status.cache_clear()
    return redirect(url_for('index'))

@app.route('/off')
def turn_off():
    if device:
        device.set_status(False, '1')
        get_cached_device_status.cache_clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_files()
    print("Starting server...")
    print(f"Access the dashboard at:")
    print(f"Local: http://127.0.0.1:5000")
    print(f"Network: http://<your-local-ip>:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)