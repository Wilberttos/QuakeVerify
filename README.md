# 🌍 QuakeVerify: Sistem Verifikasi Gempa & Kemiringan Struktur Berbasis Multi-Node IoT (iOS & Laptop)

Proyek Tugas Mata Kuliah **Internet of Things (IoT)** — Praktik Multicommunication 2 Arah dan Multisensor.

## 1. Masalah & Ide Solusi
- **Masalah**: Sensor getaran tunggal pada bangunan atau kamar kos sering mengalami *false alarm* (alarm palsu) karena tidak bisa membedakan antara guncangan meja lokal (tersenggol kaki, barang jatuh, pintu dibanting) dengan gelombang gempa bumi sungguhan.
- **Solusi (QuakeVerify)**: Menggunakan **2 perangkat Edge (iPhone/iOS atau Android)** di dua titik berbeda dalam ruangan yang membaca **Accelerometer** dan **Gyroscope** secara *real-time*. Data diolah di *edge* dan dikirim ke **MQTT Broker (HiveMQ Cloud)** untuk dianalisis dengan algoritma **Dual-Node Spatial Consensus & STA/LTA Seismic AI**.
  - Jika **hanya 1 HP** berguncang $\rightarrow$ `LOCAL_DISTURBANCE` (Senggolan lokal, alarm ditahan).
  - Jika **kedua HP** berguncang serentak $\rightarrow$ `EARTHQUAKE_ALERT` (Gempa terverifikasi! Server mengirim alarm 2 arah yang membunyikan sirine Web Audio & layar merah berkedip di semua iPhone serta Dashboard).

## 2. Pemenuhan Ketentuan Tugas
| Ketentuan Tugas | Implementasi pada QuakeVerify |
| :--- | :--- |
| **Minimal 2 Edge Device** | **Edge 1 (iPhone A)** di Sudut Ruangan 1 & **Edge 2 (iPhone B)** di Sudut Ruangan 2 + **Server Laptop**. |
| **Minimal 2 Sensor** | **Accelerometer** ($a_x, a_y, a_z$ m/s²) & **Gyroscope** ($\omega_x, \omega_y, \omega_z$ rad/s) via iOS Safari `DeviceMotionEvent` atau Web `iot.myudak.com`. |
| **Minimal 2 Data Processing** | 1. **PGA (Peak Ground Acceleration), RMS Vibration, & Rasio Seismik STA/LTA**.<br>2. **3D Structural Tilt Angle ($\theta = \arccos(\vec{g} \cdot \vec{g}_{ref})$) & Integrasi Energi Rotasi**. |
| **Algoritma / AI** | **Dual-Node Spatial Cross-Verification + STA/LTA Anomaly Scoring (0–100) & Estimasi Skala MMI**. |
| **Komunikasi ke Cloud (2 Arah)** | **MQTT over TLS (Port 8883)** untuk Python Server & **MQTT over WebSocket TLS (Port 8884)** untuk iOS Safari dan Dashboard. |
| **Dashboard Lokal** | `web/dashboard.html` berjalan di jaringan yang sama dengan pengguna, dilengkapi grafik *live* dan kontrol 2 arah (**ARM / DISARM / UJI ALARM**). |
