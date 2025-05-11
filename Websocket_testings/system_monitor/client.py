import psutil
import json
import subprocess
import websocket
import time 
import datetime

def get_cpu_temperature():
    # Get cpu temperature using lm sensors
    try:
        result = subprocess.run(['sensors'],capture_output=True, text=True)
        output = result.stdout
        for Line in output.split('\n'):
            if 'Core 0' in Line:
                temp = Line.split(':')[1].strip().split(' ')[0]
                return float(temp.replace("°C", ""))
        return None
    except Exception as e:
        print(f"Error getting CPU temperature: {e}")
        return None

def get_system_metrics():
    # Get system metrics using psutil
    metrics = {
        'timestamp': datetime.datetime.now().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'cpu_frequency': {
            'current': psutil.cpu_freq().current if psutil.cpu_freq() else None,
            'max': psutil.cpu_freq().max if psutil.cpu_freq() else None
        },
        'memory': {
            'total': psutil.virtual_memory().total /(1024 ** 3),
            'used': psutil.virtual_memory().used /(1024 ** 3),
            'percent': psutil.virtual_memory().percent
        },
        'disk': {
            'total': psutil.disk_usage('/').total /(1024 ** 3),
            'used': psutil.disk_usage('/').used /(1024**3),
            'free': psutil.disk_usage('/').free /(1024 ** 3),
            'percent': psutil.disk_usage('/').percent
        },
        'network': {
            'bytes_sent': psutil.net_io_counters().bytes_sent /(1024 ** 3),
            'bytes_recv': psutil.net_io_counters().bytes_recv /(1024 ** 3)
        },
        'uptime': str(datetime.timedelta(seconds=int(time.time() - psutil.boot_time()))),
        'cpu_temperature': get_cpu_temperature()
    }
    return metrics

def main():
    # websocket connection cnfiguration
    ws_url = "wss://evenly-pure-titmouse.ngrok-free.app"
    print(f"Connecting to websocket server at {ws_url}")
    ws = websocket.WebSocket()
    try:
        ws.connect(ws_url)
        print("Connected to websocket server")

        while True:
            metrics = get_system_metrics()
            print(f"Sending metrics: {metrics}")
            ws.send(json.dumps(metrics))
            print(f"Sent metrics at {metrics['timestamp']}")
            time.sleep(30) # Adjus the sleep time as needed
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ws.close()
        print("Disconnected from the websocket server")
    
if __name__ == "__main__":
    main()
# This script collects system metrics and sends them to a websocket server every 30 seconds.
# It includes CPU usage, memory usage, disk usage, network statistics, and CPU temperature.