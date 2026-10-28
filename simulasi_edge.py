#!/usr/bin/env python3
"""
QuakeVerify - Simulator Edge Node (Bisa dijalankan di Laptop untuk simulasi
atau pengujian cepat tanpa harus mengguncang 2 iPhone secara bersamaan).

Contoh pemakaian di terminal laptop:
  python simulasi_edge.py --node edge1 --scenario normal
  python simulasi_edge.py --node edge1 --scenario bump
  python simulasi_edge.py --node both  --scenario quake
"""
import argparse
import json
import math
import random
import ssl
import time
import paho.mqtt.client as mqtt

from shared.config import settings
from shared.processing import EdgeSignalProcessor, SensorSample


def generate_samples(scenario: str) -> list[SensorSample]:
    samples = []
    now = time.monotonic()
    for i in range(5):
        t = now + i * 0.08
        if scenario == "normal":
            ax = random.gauss(0.0, 0.03)
            ay = random.gauss(0.0, 0.03)
            az = 9.81 + random.gauss(0.0, 0.04)
            gx, gy, gz = random.gauss(0, 0.01), random.gauss(0, 0.01), random.gauss(0, 0.01)
        elif scenario == "bump":
            # Senggolan tajam sesaat di 1 meja
            spike = 2.4 if i in (1, 2) else 0.1
            ax = random.uniform(-spike, spike)
            ay = random.uniform(-spike, spike)
            az = 9.81 + random.uniform(-spike, spike)
            gx, gy, gz = random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4), 0.05
        elif scenario == "quake":
            # Gelombang seismik harmonik kuat di semua sumbu
            phase = t * 12.0
            ax = 2.8 * math.sin(phase) + random.gauss(0, 0.2)
            ay = 2.5 * math.cos(phase) + random.gauss(0, 0.2)
            az = 9.81 + 1.9 * math.sin(phase * 1.5)
            gx, gy, gz = 0.65 * math.sin(phase), 0.55 * math.cos(phase), 0.35
        else:
            ax, ay, az = 4.5, 4.5, 7.2  # tilted
            gx, gy, gz = 0.1, 0.1, 0.1
        samples.append(SensorSample(timestamp=t, accel=(ax, ay, az), gyro=(gx, gy, gz)))
    return samples


def main():
    parser = argparse.ArgumentParser(description="Simulator Edge Node QuakeVerify")
    parser.add_argument("--node", choices=["edge1", "edge2", "both"], default="both",
                        help="Pilih node yang ingin disimulasikan (edge1, edge2, atau both)")
    parser.add_argument("--scenario", choices=["normal", "bump", "quake"], default="quake",
                        help="Skenario getaran: normal (diam), bump (1 meja tersenggol), quake (gempa serentak)")
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if settings.mqtt_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)

    def on_message(c, u, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        print(f"🔔 [ALARM DITERIMA DI EDGE] Status: {data.get('status')} | {data.get('reason')}")

    client.on_message = on_message
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.subscribe(settings.topic("alerts"), qos=1)
    client.loop_start()

    proc1 = EdgeSignalProcessor()
    proc2 = EdgeSignalProcessor()
    seq = 1

    print(f"[SIMULATOR] Menjalankan node={args.node} dengan skenario='{args.scenario}' ke PROJECT_ID={settings.project_id}")
    try:
        while True:
            if args.node in ("edge1", "both"):
                sc1 = args.scenario
                t1 = proc1.process_window("edge1", seq, generate_samples(sc1))
                client.publish(settings.topic("edge/edge1/telemetry"), json.dumps(t1.to_dict()), qos=1)
                print(f"[EDGE1] seq={seq} PGA={t1.pga_ms2} m/s² RMS={t1.vibration_rms} Tilt={t1.tilt_deg}° STA/LTA={t1.sta_lta_ratio}")

            if args.node in ("edge2", "both"):
                # Jika skenario 'bump' pada mode 'both', hanya edge1 yang goyang, edge2 tetap normal!
                sc2 = "normal" if (args.node == "both" and args.scenario == "bump") else args.scenario
                t2 = proc2.process_window("edge2", seq, generate_samples(sc2))
                client.publish(settings.topic("edge/edge2/telemetry"), json.dumps(t2.to_dict()), qos=1)
                print(f"[EDGE2] seq={seq} PGA={t2.pga_ms2} m/s² RMS={t2.vibration_rms} Tilt={t2.tilt_deg}° STA/LTA={t2.sta_lta_ratio}")

            seq += 1
            time.sleep(1.5)
    except KeyboardInterrupt:
        print("\n[SIMULATOR] Berhenti.")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
