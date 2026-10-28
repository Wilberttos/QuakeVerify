import math
import time
from dataclasses import dataclass, asdict
from typing import List, Tuple

GRAVITY = 9.81

@dataclass
class SensorSample:
    timestamp: float
    accel: Tuple[float, float, float]  # (ax, ay, az) in m/s^2
    gyro: Tuple[float, float, float]   # (gx, gy, gz) in rad/s (or deg/s converted to rad/s)

@dataclass
class EdgeTelemetry:
    device_id: str
    sequence: int
    pga_ms2: float          # Processing 1A: Peak Ground Acceleration (m/s^2)
    vibration_rms: float    # Processing 1B: RMS Vibration Energy (m/s^2)
    tilt_deg: float         # Processing 2A: 3D Structural Tilt Angle Deviation (degrees)
    rot_energy_rad: float   # Processing 2B: Integrated Rotational Energy (rad)
    sta_lta_ratio: float    # Processing 3: Short-Term / Long-Term Average seismic trigger ratio
    sent_at_ms: int

    def to_dict(self):
        return asdict(self)


class EdgeSignalProcessor:
    """
    Melakukan 2+ Jenis Pengolahan Data di sisi Edge per window (5 sampel):
    1. Pengolahan Getaran Translasi (Accelerometer):
       - Menghilangkan komponen gravitasi (9.81 m/s^2)
       - Menghitung Peak Ground Acceleration (PGA) & RMS Getaran
       - Menghitung rasio STA/LTA (Short-Term Average / Long-Term Average)
    2. Pengolahan Kemiringan & Rotasi Struktur (Accelerometer + Gyroscope):
       - Menghitung perubahan sudut kemiringan 3D (Tilt Angle Deviation dalam derajat)
       - Menghitung integrasi kecepatan sudut (Rotational Energy dalam radian)
    """
    def __init__(self):
        self.lta_baseline = 0.08  # Long-Term Average baseline vibration (m/s^2)
        self.ref_gravity_vec = None

    def process_window(self, device_id: str, sequence: int, samples: List[SensorSample]) -> EdgeTelemetry:
        if not samples:
            raise ValueError("Samples window cannot be empty")

        dynamic_accels = []
        tilt_angles = []

        for s in samples:
            ax, ay, az = s.accel
            mag = math.sqrt(ax * ax + ay * ay + az * az)
            # Dynamic ground acceleration without 1g gravity
            dyn_a = abs(mag - GRAVITY)
            dynamic_accels.append(dyn_a)

            # Set initial reference gravity vector to measure tilt shift
            if self.ref_gravity_vec is None and mag > 1.0:
                self.ref_gravity_vec = (ax / mag, ay / mag, az / mag)

            if self.ref_gravity_vec is not None and mag > 1.0:
                nx, ny, nz = ax / mag, ay / mag, az / mag
                rx, ry, rz = self.ref_gravity_vec
                dot = max(-1.0, min(1.0, nx * rx + ny * ry + nz * rz))
                angle_deg = math.degrees(math.acos(dot))
                tilt_angles.append(angle_deg)
            else:
                tilt_angles.append(0.0)

        # Processing 1: PGA & RMS Getaran
        pga_ms2 = max(dynamic_accels)
        vibration_rms = math.sqrt(sum(e * e for e in dynamic_accels) / len(dynamic_accels))

        # Update STA/LTA Ratio (algoritma seismologi standar)
        sta = vibration_rms
        self.lta_baseline = 0.92 * self.lta_baseline + 0.08 * max(vibration_rms, 0.05)
        sta_lta_ratio = sta / max(self.lta_baseline, 0.03)

        # Processing 2: 3D Tilt Deviation & Rotational Integration
        tilt_deg = sum(tilt_angles) / len(tilt_angles)
        rot_energy_rad = 0.0
        for prev, curr in zip(samples, samples[1:]):
            gx, gy, gz = curr.gyro
            dt = max(0.01, min(1.0, curr.timestamp - prev.timestamp))
            omega = math.sqrt(gx * gx + gy * gy + gz * gz)
            rot_energy_rad += omega * dt

        return EdgeTelemetry(
            device_id=device_id,
            sequence=sequence,
            pga_ms2=round(pga_ms2, 3),
            vibration_rms=round(vibration_rms, 3),
            tilt_deg=round(tilt_deg, 2),
            rot_energy_rad=round(rot_energy_rad, 3),
            sta_lta_ratio=round(sta_lta_ratio, 2),
            sent_at_ms=int(time.time() * 1000),
        )
