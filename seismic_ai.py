import math
import time
from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class SeismicDecision:
    status: str             # NORMAL | LOCAL_DISTURBANCE | EARTHQUAKE_ALERT | STRUCTURAL_TILT_ALERT | DISARMED
    severity_score: float   # 0.0 - 100.0
    mmi_estimate: str       # Skala MMI (I - VII+)
    reason: str
    node1_active: bool
    node2_active: bool
    timestamp_ms: int

    def to_dict(self):
        return asdict(self)


class DualNodeSeismicClassifier:
    """
    Algoritma AI / Multi-Sensor Spatial Fusion (QuakeVerify):
    Membandingkan telemetri dari 2 Edge Device (iPhone/HP 1 & iPhone/HP 2)
    untuk memverifikasi apakah getaran adalah:
    - NORMAL: Kedua node tenang
    - LOCAL_DISTURBANCE: Hanya 1 node yang terguncang (misal meja tersenggol / HP jatuh) -> Cegah False Alarm!
    - EARTHQUAKE_ALERT: Kedua node di titik berbeda mendeteksi gelombang seismik serentak (PGA & RMS melewati ambang + kemiripan waktu)
    - STRUCTURAL_TILT_ALERT: Terjadi kemiringan struktur/meja ekstrem (> 12 derajat) pasca guncangan
    """
    def __init__(self, pga_threshold: float = 0.85, rms_threshold: float = 0.45, tilt_threshold: float = 12.0):
        self.pga_threshold = pga_threshold
        self.rms_threshold = rms_threshold
        self.tilt_threshold = tilt_threshold
        self.armed = True
        self.latest_nodes: Dict[str, dict] = {}

    def update_node(self, device_id: str, telemetry: dict):
        telemetry["received_at"] = time.time()
        self.latest_nodes[device_id] = telemetry

    def _is_shaking(self, node: Optional[dict]) -> bool:
        if not node:
            return False
        # Data dianggap basi jika lebih dari 6 detik tidak update
        if time.time() - node.get("received_at", 0) > 6.0:
            return False
        return (
            node.get("pga_ms2", 0.0) >= self.pga_threshold
            or node.get("vibration_rms", 0.0) >= self.rms_threshold
            or node.get("sta_lta_ratio", 0.0) >= 3.2
        )

    def _is_tilted(self, node: Optional[dict]) -> bool:
        if not node:
            return False
        if time.time() - node.get("received_at", 0) > 6.0:
            return False
        return node.get("tilt_deg", 0.0) >= self.tilt_threshold

    def evaluate(self) -> SeismicDecision:
        now_ms = int(time.time() * 1000)
        if not self.armed:
            return SeismicDecision(
                status="DISARMED",
                severity_score=0.0,
                mmi_estimate="I (Disarmed)",
                reason="Sistem sedang dinonaktifkan (DISARMED) oleh pengguna.",
                node1_active=False,
                node2_active=False,
                timestamp_ms=now_ms,
            )

        n1 = self.latest_nodes.get("edge1")
        n2 = self.latest_nodes.get("edge2")

        s1 = self._is_shaking(n1)
        s2 = self._is_shaking(n2)
        t1 = self._is_tilted(n1)
        t2 = self._is_tilted(n2)

        pga1 = n1.get("pga_ms2", 0.0) if n1 else 0.0
        pga2 = n2.get("pga_ms2", 0.0) if n2 else 0.0
        rms1 = n1.get("vibration_rms", 0.0) if n1 else 0.0
        rms2 = n2.get("vibration_rms", 0.0) if n2 else 0.0

        # Hitung Composite Seismic Score (0 - 100) dengan Weighted Spatial Consensus
        avg_pga = (pga1 + pga2) / 2.0
        avg_rms = (rms1 + rms2) / 2.0
        raw_score = min(100.0, (avg_pga * 22.0) + (avg_rms * 35.0))

        # Estimasi Skala MMI (Modified Mercalli Intensity)
        if avg_pga < 0.2:
            mmi = "I (Tidak Terasa)"
        elif avg_pga < 0.8:
            mmi = "II-III (Lemah)"
        elif avg_pga < 2.0:
            mmi = "IV (Sedang)"
        elif avg_pga < 4.0:
            mmi = "V (Kuat)"
        else:
            mmi = "VI+ (Sangat Kuat / Bahaya)"

        if s1 and s2:
            score = max(75.0, round(raw_score, 1))
            return SeismicDecision(
                status="EARTHQUAKE_ALERT",
                severity_score=score,
                mmi_estimate=mmi,
                reason=f"Terverifikasi GEMPA! Kedua node mendeteksi gelombang serentak (PGA: {pga1:.2f} & {pga2:.2f} m/s²).",
                node1_active=True,
                node2_active=True,
                timestamp_ms=now_ms,
            )

        if t1 and t2:
            return SeismicDecision(
                status="STRUCTURAL_TILT_ALERT",
                severity_score=80.0,
                mmi_estimate=mmi,
                reason="Kedua node mendeteksi kemiringan bidang/struktur melebihi batas aman!",
                node1_active=True,
                node2_active=True,
                timestamp_ms=now_ms,
            )

        if s1 and not s2:
            return SeismicDecision(
                status="LOCAL_DISTURBANCE",
                severity_score=round(min(45.0, pga1 * 12.0), 1),
                mmi_estimate="Lokal (Node 1)",
                reason=f"Gangguan lokal hanya di Node 1 (PGA {pga1:.2f} m/s²), Node 2 tenang. Alarm gempa ditahan.",
                node1_active=True,
                node2_active=False,
                timestamp_ms=now_ms,
            )

        if s2 and not s1:
            return SeismicDecision(
                status="LOCAL_DISTURBANCE",
                severity_score=round(min(45.0, pga2 * 12.0), 1),
                mmi_estimate="Lokal (Node 2)",
                reason=f"Gangguan lokal hanya di Node 2 (PGA {pga2:.2f} m/s²), Node 1 tenang. Alarm gempa ditahan.",
                node1_active=False,
                node2_active=True,
                timestamp_ms=now_ms,
            )

        return SeismicDecision(
            status="NORMAL",
            severity_score=round(raw_score, 1),
            mmi_estimate="I (Aman)",
            reason="Kondisi stabil. Tidak ada anomali getaran pada kedua node.",
            node1_active=False,
            node2_active=False,
            timestamp_ms=now_ms,
        )
