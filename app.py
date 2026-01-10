from flask import Flask, flash, render_template, request, redirect, url_for
import json
import os
from datetime import datetime
import math

app = Flask(__name__)
FILE_NAME = "data_parkir.json"
app.secret_key = "kunci_rahasia_parkir_saya"

# ==================== DATA FUNCTIONS ====================
def load_data():
    try:
        if os.path.exists(FILE_NAME):
            with open(FILE_NAME, 'r') as file:
                data = json.load(file)
                # Pastikan key selalu ada (Defensive)
                return {
                    "tiket_aktif": data.get("tiket_aktif", {}),
                    "riwayat_transaksi": data.get("riwayat_transaksi", []),
                    "member": data.get("member", {})
                }
    except (json.JSONDecodeError, PermissionError) as e:
        print(f"Error loading JSON: {e}") # Log ke terminal untuk developer
        # Return struktur kosong agar web tetap jalan (tidak error 500)
        return {"tiket_aktif": {}, "riwayat_transaksi": [], "member": {}}
    except Exception as e:
        print(f"Unknown Error loading data: {e}")
        return {"tiket_aktif": {}, "riwayat_transaksi": [], "member": {}}

def save_data(data):
    try:
        with open(FILE_NAME, 'w') as file:
            json.dump(data, file, indent=4)
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False

def buat_no_resi(kode_jenis, jam_masuk, menit_masuk, no_kendaraan):
    jam_str = str(jam_masuk).zfill(2)
    menit_str = str(menit_masuk).zfill(2)
    return "P-" + kode_jenis + jam_str + "." + menit_str + "-" + no_kendaraan.upper()

def hitung_biaya(t_masuk, t_keluar, tarif, is_member):
    if t_keluar < t_masuk: 
        t_keluar += 24 * 60
    durasi_menit = t_keluar - t_masuk
    if durasi_menit <= 0: durasi_menit = 60
    
    durasi_jam = durasi_menit // 60
    if durasi_menit % 60 > 0: durasi_jam += 1
    
    total_biaya = 5000 if is_member else durasi_jam * tarif
    return durasi_jam, total_biaya, durasi_menit

def calculate_parking_fee(ticket, tanggal_keluar, jam_keluar, menit_keluar):
    # Convert dates
    masuk = datetime.strptime(
        f"{ticket['tanggal']} {ticket['jam_masuk']}:{ticket['menit_masuk']}",
        "%Y-%m-%d %H:%M"
    )
    
    keluar = datetime.strptime(
        f"{tanggal_keluar} {jam_keluar}:{menit_keluar}",
        "%Y-%m-%d %H:%M"
    )

    # Calculate duration in minutes
    duration_minutes = (keluar - masuk).total_seconds() / 60

    if duration_minutes <= 0:
        raise ValueError("Invalid checkout time")

    # Member rule (flat rate, max 24 hours)
    if ticket["is_member"]:
        if duration_minutes > 24 * 60:
            raise ValueError("Member parking exceeds 24 hours")
        return 5000

    # Convert minutes to billable hours (round up)
    billable_hours = math.ceil(duration_minutes / 60)

    # Pricing
    if ticket["jenis_kendaraan"].lower() == "motor":
        rate = 3000
    elif ticket["jenis_kendaraan"].lower() == "mobil":
        rate = 5000
    else:
        raise ValueError("Unknown vehicle type")

    return billable_hours * rate, billable_hours

# ==================== ROUTES ====================
@app.route('/')
def dashboard():
    data = load_data() # Load data asli dari JSON
    tiket_aktif = data["tiket_aktif"]
    
    # --- LOGIKA BARU: Hitung Mobil vs Motor ---
    jml_mobil = 0
    jml_motor = 0
    
    for tiket in tiket_aktif.values():
        if tiket['jenis_kendaraan'] == 'Mobil':
            jml_mobil += 1
        elif tiket['jenis_kendaraan'] == 'Motor':
            jml_motor += 1
            
    # Hitung total (bisa juga pakai len(tiket_aktif))
    jml_aktif = jml_mobil + jml_motor 
    
    # Statistik lain (tetap sama)
    jml_member = len(data["member"])
    jml_transaksi = len(data.get("riwayat_transaksi", []))
    total_pendapatan = sum(t['total_bayar'] for t in data.get("riwayat_transaksi", []))

    # Kirim variabel jml_mobil dan jml_motor ke HTML
    return render_template('dashboard.html', 
                           tiket_aktif=tiket_aktif,
                           jml_aktif=jml_aktif,
                           jml_mobil=jml_mobil,   # <--- Kirim ini
                           jml_motor=jml_motor,   # <--- Kirim ini
                           jml_member=jml_member,
                           jml_transaksi=jml_transaksi,
                           total_pendapatan=total_pendapatan)

@app.route('/masuk', methods=['GET', 'POST'])
def parkir_masuk():
    # 1. Load data dengan aman
    data = load_data()
    
    # Default value untuk form (waktu sekarang)
    sekarang = datetime.now()
    new_resi = None

    if request.method == 'POST':
        try:
            # --- BLOCK VALIDASI INPUT ---
            # Menggunakan .get() lebih aman daripada request.form['key']
            no_kendaraan = request.form.get('no_kendaraan', '').strip().upper()
            jenis_pilihan = request.form.get('jenis_kendaraan')
            tanggal = request.form.get('tanggal')
            
            # Cek kelengkapan data
            if not no_kendaraan or not jenis_pilihan:
                raise ValueError("Mohon lengkapi Nomor Kendaraan dan Jenis Kendaraan.")

            # Konversi input angka (bisa error jika user input huruf)
            try:
                jam_masuk = int(request.form.get('jam', sekarang.hour))
                menit_masuk = int(request.form.get('menit', sekarang.minute))
            except ValueError:
                raise ValueError("Jam dan Menit harus berupa angka.")

            # Validasi Logic (Contoh: Jam tidak boleh > 23)
            if not (0 <= jam_masuk <= 23) or not (0 <= menit_masuk <= 59):
                raise ValueError("Format waktu tidak valid.")

            # --- BLOCK LOGIKA ---
            # (Kode logika tarif sama seperti sebelumnya...)
            if jenis_pilihan == "1":
                jenis_kendaraan = "Mobil"; kode_jenis = "MB"; tarif_per_jam = 5000
            else:
                jenis_kendaraan = "Motor"; kode_jenis = "MT"; tarif_per_jam = 3000

            if not tanggal:
                raise ValueError("Mohon lengkapi Tanggal.")

            # Cek Member
            telp_member = request.form.get('telp_member', '').strip()
            is_member = False
            if telp_member and telp_member in data["member"]:
                is_member = True
                data["member"][telp_member]["jumlah_kunjungan"] += 1

            # Buat Resi
            no_resi = buat_no_resi(kode_jenis, jam_masuk, menit_masuk, no_kendaraan)
            
            # Simpan ke Dictionary
            data["tiket_aktif"].append({
                "no_resi": no_resi,
                "no_kendaraan": no_kendaraan,
                "jenis_kendaraan": jenis_kendaraan,
                "kode_jenis": kode_jenis,
                "jam_masuk": jam_masuk,
                "menit_masuk": menit_masuk,
                "total_masuk_menit": jam_masuk * 60 + menit_masuk,
                "tarif_per_jam": tarif_per_jam,
                "is_member": is_member,
                "telp_member": telp_member,
                "waktu_masuk_str": f"{jam_masuk:02d}:{menit_masuk:02d}",
                'tanggal': tanggal
            })
            
            # --- BLOCK PENYIMPANAN ---
            if save_data(data):
                flash(f"Berhasil! Kendaraan {no_kendaraan} masuk.", "success")
                new_resi = no_resi # Kirim ke template utk ditampilkan
            else:
                flash("Gagal menyimpan data ke database. Coba lagi.", "danger")

        except ValueError as ve:
            # Error Validasi (Input user salah)
            flash(str(ve), "warning")
            
        except Exception as e:
            # Error Tidak Terduga (Bug coding / Server error)
            print(f"[CRITICAL ERROR] di route /masuk: {e}") # Print ke terminal utk developer lihat
            flash("Terjadi kesalahan sistem. Hubungi admin.", "danger")

    return render_template('masuk.html', new_resi=new_resi, jam_sekarang=sekarang.hour, menit_sekarang=sekarang.minute)

@app.route('/keluar', methods=['GET', 'POST'])
def parkir_keluar():
    data = load_data()
    currentTicket = None
    currentJam = 0
    currentMenit = 0
    isConfirmed = '0'
    totalBiaya = 0
    totalDurasi = 0
    
    if request.method == 'POST':
        try:
            isConfirmed = request.form.get('is_confirm')

            if isConfirmed == '0':
              no_resi = request.form.get('no_resi', '')
              tanggal = request.form.get('tanggal', '')

              if not no_resi:
                  raise ValueError("Mohon lengkapi Nomor Resi.")
              
              if not tanggal:
                  raise ValueError("Mohon lengkapi Tanggal.")
              
              try:
                  jam_keluar = int(request.form.get('jam', ''))
                  menit_keluar = int(request.form.get('menit', ''))
              except ValueError:
                  raise ValueError("Jam dan Menit harus berupa angka.")
              
              if not (0 <= jam_keluar <= 23) or not (0 <= menit_keluar <= 59):
                  raise ValueError("Format waktu tidak valid.")
              
              if not currentTicket:
                for tiket_aktif in data['tiket_aktif']:
                    if tiket_aktif['no_resi'] == no_resi:
                        totalBiaya, totalDurasi = calculate_parking_fee(tiket_aktif, tanggal, jam_keluar, menit_keluar)

                        if totalDurasi < 1:
                          raise ValueError("Waktu keluar kurang dari Waktu Masuk.")
                        else:
                          currentTicket = tiket_aktif
                          currentJam = jam_keluar
                          currentMenit = menit_keluar
            else:
                no_resi = request.form.get('no_resi')
                currentJam = request.form.get('currentJam')
                currentMenit = request.form.get('currentMenit')
                totalDurasi = request.form.get('totalDurasi')
                total_bayar = request.form.get('totalBiaya')

                for tiket_aktif in data['tiket_aktif']:
                    if tiket_aktif['no_resi'] == no_resi:
                        currentTicket = tiket_aktif

                data['riwayat_transaksi'].append({
                  "no_resi": currentTicket['no_resi'],
                  "no_kendaraan": currentTicket['no_kendaraan'],
                  "jenis_kendaraan": currentTicket['jenis_kendaraan'],
                  "waktu_masuk": currentTicket['waktu_masuk_str'],
                  "waktu_keluar": f"{currentJam}:{currentMenit}",
                  "durasi": f"{totalDurasi} Jam",
                  "total_bayar": total_bayar,
                  "is_member": currentTicket['is_member']
                })
                data['tiket_aktif'].remove(currentTicket)       
                save_data(data)

        except ValueError as ve:
            # Error Validasi (Input user salah)
            flash(str(ve), "warning")
            
        except Exception as e:
            # Error Tidak Terduga (Bug coding / Server error)
            print(f"[CRITICAL ERROR] di route /keluar: {e}") # Print ke terminal utk developer lihat
            flash("Terjadi kesalahan sistem. Hubungi admin.", "danger")

    return render_template('keluar.html', tiket_aktif=data["tiket_aktif"], currentTicket=currentTicket, totalBiaya=format(totalBiaya, ',').replace(',', '.'), totalDurasi=totalDurasi, currentJam=currentJam, currentMenit=currentMenit, isConfirmed=isConfirmed)
# @app.route('/aktif')
# def lihat_aktif():
#     data = load_data()
#     return render_template('aktif.html', tiket_aktif=data["tiket_aktif"])

if __name__ == '__main__':
    app.run(debug=True)