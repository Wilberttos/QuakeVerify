#!/usr/bin/env python3
"""
QuakeVerify - Node 3 (Laptop Server: MQTT Detector & Web Hosting)
Menjalankan:
1. Web Server lokal (port 8000) untuk membuka:
   - Dashboard Monitoring: http://localhost:8000/web/dashboard.html
   - Aplikasi Sensor iOS/HP: http://<IP_LAPTOP>:8000/web/edge_ios.html
2. MQTT Subscriber & Publisher ke HiveMQ Cloud (port 8883 TLS) yang menerima
   telemetri dari Edge 1 & Edge 2, menjalankan algoritma DualNodeSeismicClassifier,
   dan mengirim balik keputusan/alarm 2 arah ke topic alerts & status.
"""
import json
import os
import socket
import ssl
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import paho.mqtt.client as mqtt

from shared.config import settings
from shared.seismic_ai import DualNodeSeismicClassifier

classifier = DualNodeSeismicClassifier()
last_alert_time = 0.0


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[MQTT] Terhubung ke broker {settings.mqtt_host}:{settings.mqtt_port} (status: {reason_code})")
    telemetry_topic = settings.topic("edge/+/telemetry")
    command_topic = settings.topic("command")
    client.subscribe(telemetry_topic, qos=1)
    client.subscribe(command_topic, qos=1)
    print(f"[MQTT] Subscribe ke: {telemetry_topic}")
    print(f"[MQTT] Subscribe ke: {command_topic}")


def on_message(client, userdata, msg):
    global last_alert_time
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        print(f"[WARN] Payload bukan JSON valid di {msg.topic}: {e}")
        return

    # Handle 2-way command dari Dashboard atau HP (ARM / DISARM / TEST_ALARM / RESET)
    if msg.topic.endswith("/command"):
        cmd = payload.get("action", "").upper()
        if cmd == "ARM":
            classifier.armed = True
            print("[COMMAND] Sistem di-ARM (Aktif)")
        elif cmd == "DISARM":
            classifier.armed = False
            print("[COMMAND] Sistem di-DISARM (Nonaktif)")
        elif cmd == "TEST_ALARM":
            alert_msg = {
                "status": "EARTHQUAKE_ALERT",
                "severity_score": 95.0,
                "mmi_estimate": "VI (Simulasi Uji Alarm)",
                "reason": "Uji coba alarm dua arah dari Dashboard berhasil dipicu!",
                "timestamp_ms": int(time.time() * 1000),
            }
            client.publish(settings.topic("alerts"), json.dumps(alert_msg), qos=1)
            print("[COMMAND] TEST_ALARM dikirim ke seluruh HP Edge!")
            return

    # Handle telemetri dari Edge 1 atau Edge 2
    elif "/telemetry" in msg.topic:
        device_id = payload.get("device_id", "unknown")
        classifier.update_node(device_id, payload)

    # Evaluasi keputusan dengan algoritma Dual-Node Seismic Fusion
    decision = classifier.evaluate()
    decision_dict = decision.to_dict()

    # Publish status terbaru ke Dashboard & HP
    client.publish(settings.topic("status"), json.dumps(decision_dict), qos=0)

    # Jika EARTHQUAKE_ALERT atau STRUCTURAL_TILT_ALERT, kirim ke topic alerts (rate-limited tiap 2 detik)
    now = time.time()
    if decision.status in ("EARTHQUAKE_ALERT", "STRUCTURAL_TILT_ALERT") and (now - last_alert_time > 2.0):
        last_alert_time = now
        client.publish(settings.topic("alerts"), json.dumps(decision_dict), qos=1)
        print(f"🚨 [ALERT] {decision.status} | Skor: {decision.severity_score} | {decision.reason}")
    else:
        print(f"[STATUS] {decision.status:18s} | Skor: {decision.severity_score:4.1f} | {decision.reason}")


def start_web_server():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    handler = partial(SimpleHTTPRequestHandler, directory=root_dir)
    server = ThreadingHTTPServer(("0.0.0.0", settings.http_port), handler)
    local_ip = get_local_ip()
    print("=" * 72)
    print("🌍 QUAKEVERIFY - SERVER & WEB DASHBOARD BERJALAN")
    print(f"💻 Buka Dashboard di Laptop : http://localhost:{settings.http_port}/web/dashboard.html")
    print(f"📱 Buka Edge Sensor di iOS  : http://{local_ip}:{settings.http_port}/web/edge_ios.html")
    print(f"🔑 PROJECT_ID Aktif         : {settings.project_id}")
    print("=" * 72)
    server.serve_forever()


def main():
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    if settings.mqtt_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)

    print(f"[MQTT] Menghubungkan ke {settings.mqtt_host}:{settings.mqtt_port} ...")
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Menghentikan server QuakeVerify...")
        client.disconnect()


if __name__ == "__main__":
    main()
