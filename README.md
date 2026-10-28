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

## 3. Cara Menjalankan dari Awal (Khusus Pengguna iPhone / iOS & Laptop)

### Langkah 1: Persiapan di Laptop (VS Code / Terminal)
1. Pastikan **Python 3.10+** sudah terpasang di laptop (Windows / Mac).
2. Buka folder `quakeverify-iot` ini di **VS Code** atau Terminal.
3. Salin file `.env.example` menjadi `.env`:
   ```bash
   cp .env.example .env
   ```
4. Install pustaka Python yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```

### Langkah 2: Jalankan Server Detector & Dashboard di Laptop
Jalankan perintah berikut di terminal laptop:
```bash
python detector.py
```
Lalu buka browser di laptop dan akses:
👉 **`http://localhost:8000/web/dashboard.html`**

### Langkah 3: Menghubungkan 2 HP iOS (iPhone) Tanpa Termux
Karena iOS tidak memiliki aplikasi Termux, kamu punya **2 cara sangat mudah** di Safari iPhone:

#### Cara A — Menggunakan Web Edge Bawaan Proyek Ini (`edge_ios.html`)
1. Hubungkan iPhone dan Laptop ke **WiFi atau Hotspot yang sama**.
2. Buka link yang muncul di terminal laptop (contoh: `http://192.168.1.x:8000/web/edge_ios.html`) di Safari iPhone, **ATAU** buka file `web/edge_ios.html` melalui GitHub Pages / tunnel HTTPS.
3. Pilih peran **Edge 1** di iPhone pertama dan **Edge 2** di iPhone kedua, pastikan `PROJECT_ID` sama, lalu tekan **"🚀 Aktifkan Sensor iOS"**.
4. Kamu juga bisa menekan tombol **"💥 Simulasi Senggolan"** atau **"🌋 Simulasi Gempa 5dtk"** langsung di layar iPhone untuk mendemokan perubahan status secara instan!

#### Cara B — Menggunakan `https://iot.myudak.com/` di Safari iPhone (Sesuai Slide 23 & 31 PPT Dosen)
1. Buka Safari di iPhone 1 dan iPhone 2, kunjungi **`https://iot.myudak.com/`**.
2. Isi `PROJECT_ID` yang sama, lalu jalankan pembacaan sensor.
3. Untuk menguji skenario lengkap dari laptop kapan saja tanpa perlu menggoyang 2 HP sekaligus, buka terminal kedua di laptop dan jalankan simulator:
   ```bash
   # Skenario 1: Kondisi Normal (Aman)
   python simulasi_edge.py --node both --scenario normal

   # Skenario 2: Meja 1 Tersenggol (Hanya Edge 1 goyang -> LOCAL_DISTURBANCE)
   python simulasi_edge.py --node both --scenario bump

   # Skenario 3: Gempa Bumi (Kedua Edge goyang serentak -> EARTHQUAKE_ALERT!)
   python simulasi_edge.py --node both --scenario quake
   ```
