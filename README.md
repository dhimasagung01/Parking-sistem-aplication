# 🚗 Parking - Sistem Manajemen Parkir Berbasis Web

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-green)
![Status](https://img.shields.io/badge/Status-Active-success)

**Parking** adalah aplikasi manajemen parkir berbasis web yang dirancang untuk mendigitalkan proses pencatatan kendaraan masuk dan keluar. Aplikasi ini menggunakan **Python (Flask)** sebagai backend dan **JSON** sebagai penyimpanan data (database), sehingga ringan dan mudah dijalankan tanpa perlu instalasi database server (seperti MySQL).

---

## ✨ Fitur Utama

* **Dashboard Real-time:** Menampilkan statistik kendaraan aktif (Mobil/Motor) dan total pendapatan harian.
* **Sistem Tiket Otomatis:** Generate nomor resi unik (`P-MB...`) saat kendaraan masuk.
* **Kalkulasi Tarif Cerdas:**
    * Tarif per jam untuk reguler (Mobil: Rp5.000, Motor: Rp3.000).
    * Pembulatan durasi ke atas (misal: 1 jam 5 menit dihitung 2 jam).
* **Sistem Membership:** Tarif *flat* (Rp5.000) untuk member terdaftar.
* **Manajemen Member:** Tambah dan Hapus data member.
* **Riwayat Transaksi:** Laporan lengkap kendaraan yang sudah keluar dengan filter pencarian.
* **Validasi Ketat:** Mencegah input ganda, validasi plat nomor, dan nomor telepon.
* **Dark Mode UI:** Tampilan antarmuka modern yang nyaman di mata.

---

## 🛠️ Teknologi yang Digunakan

* **Backend:** Python 3 (Flask Microframework)
* **Frontend:** HTML5, CSS3 (Custom Styling), JavaScript
* **Database:** JSON (`data_parkir.json`)
* **Tools:** Git, VS Code

---

## 💻 Cara Menjalankan (Installation Guide)

Ikuti langkah-langkah di bawah ini untuk menjalankan aplikasi ini di komputer Anda (Localhost).

### 1. Prasyarat (Prerequisites)
Pastikan komputer Anda sudah terinstall:
* [Python 3.x](https://www.python.org/downloads/)
* [Git](https://git-scm.com/downloads)

### 2. Clone Repository
Buka terminal (CMD/PowerShell/Terminal) dan jalankan perintah berikut untuk mengunduh proyek ini:

```bash
# Clone repository ini
git clone https://github.com/dhimasagung01/sistem-parkir.git

# Masuk ke folder project
cd sistem-parkir

# Buka folder dengan
code .


Agar library tidak bentrok dengan sistem utama komputer Anda.
# Untuk Windows
python -m venv venv
venv\Scripts\activate

# Untuk Mac/Linux
python3 -m venv venv
source venv/bin/activate

Install framework Flask yang dibutuhkan:
pip install flask

Jalankan server Flask dengan perintah:
python app.py

Jika berhasil, akan muncul tulisan: Running on http://127.0.0.1:5000
saling url yang ada ke browser

