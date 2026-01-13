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
                return {
                    "tiket_aktif": data.get("tiket_aktif", []),
                    "riwayat_transaksi": data.get("riwayat_transaksi", []),
                    "member": data.get("member", [])
                }
    except (json.JSONDecodeError, PermissionError) as e:
        print(f"Error loading JSON: {e}")
        return {"tiket_aktif": [], "riwayat_transaksi": [], "member": []}
    except Exception as e:
        print(f"Unknown Error loading data: {e}")
        return {"tiket_aktif": [], "riwayat_transaksi": [], "member": []}

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

def calculate_parking_fee(ticket, tanggal_keluar, jam_keluar, menit_keluar):
    masuk = datetime.strptime(
        f"{ticket['tanggal']} {ticket['jam_masuk']}:{ticket['menit_masuk']}",
        "%Y-%m-%d %H:%M"
    )
    
    keluar = datetime.strptime(
        f"{tanggal_keluar} {jam_keluar}:{menit_keluar}",
        "%Y-%m-%d %H:%M"
    )

    duration_minutes = (keluar - masuk).total_seconds() / 60

    if duration_minutes <= 0:
        raise ValueError("Waktu keluar tidak valid (kurang dari waktu masuk)")

    billable_hours = math.ceil(duration_minutes / 60)

    if ticket["is_member"]:
        # Hitung durasi dalam satuan 'hari' (blok 24 jam)
        # math.ceil akan membulatkan ke atas.
        # Contoh: 100 menit / 1440 = 0.06 -> dibulatkan jadi 1 hari
        jumlah_hari = math.ceil(duration_minutes / (24 * 60))
        
        # Tarif flat Rp 5.000 per 24 jam
        total_biaya = jumlah_hari * 5000
        
        # Kembalikan dua nilai: biaya dan durasi jam
        return total_biaya, billable_hours

    if ticket["jenis_kendaraan"].lower() == "motor":
        rate = 3000
    elif ticket["jenis_kendaraan"].lower() == "mobil":
        rate = 5000
    else:
        raise ValueError("Jenis kendaraan tidak dikenal")

    return billable_hours * rate, billable_hours

# ==================== ROUTES ====================
@app.route('/')
def dashboard():
    data = load_data()
    tiket_aktif = data["tiket_aktif"]
    
    jml_mobil = 0
    jml_motor = 0
    
    for tiket in tiket_aktif:
        if tiket['jenis_kendaraan'] == 'Mobil':
            jml_mobil += 1
        elif tiket['jenis_kendaraan'] == 'Motor':
            jml_motor += 1
            
    jml_aktif = jml_mobil + jml_motor 
    
    jml_member = len(data["member"])
    jml_transaksi = len(data.get("riwayat_transaksi", []))
    total_pendapatan = sum(int(str(t['total_bayar']).replace('.', '')) for t in data.get("riwayat_transaksi", []))

    return render_template('dashboard.html', 
                           tiket_aktif=tiket_aktif,
                           jml_aktif=jml_aktif,
                           jml_mobil=jml_mobil,   
                           jml_motor=jml_motor,   
                           jml_member=jml_member,
                           jml_transaksi=jml_transaksi,
                           total_pendapatan=total_pendapatan)

@app.route('/masuk', methods=['GET', 'POST'])
def parkir_masuk():
    data = load_data()
    
    sekarang = datetime.now()
    new_resi = None

    if request.method == 'POST':
        try:
            # --- BLOCK VALIDASI INPUT ---
            no_kendaraan = request.form.get('no_kendaraan', '').strip().upper()
            jenis_pilihan = request.form.get('jenis_kendaraan')
            tanggal = request.form.get('tanggal')
            no_kendaraan_tersedia = any(t['no_kendaraan'] == no_kendaraan for t in data['tiket_aktif'])
            
            if no_kendaraan_tersedia:
                raise ValueError(f"Kendaraan dengan nomor {no_kendaraan} sudah parkir!")
            
            if not no_kendaraan or not jenis_pilihan:
                raise ValueError("Mohon lengkapi Nomor Kendaraan dan Jenis Kendaraan.")
            
            if not (3 <= len(no_kendaraan) <= 15):
                raise ValueError("Panjang nomor kendaraan harus antara 3 sampai 15 karakter.")

            # Konversi input angka
            try:
                jam_masuk = int(request.form.get('jam', sekarang.hour))
                menit_masuk = int(request.form.get('menit', sekarang.minute))
            except ValueError:
                raise ValueError("Jam dan Menit harus berupa angka.")

            # Validasi Jam tidak boleh > 23
            if not (0 <= jam_masuk <= 23) or not (0 <= menit_masuk <= 59):
                raise ValueError("Format waktu tidak valid.")

            # --- BLOCK LOGIKA ---
            if jenis_pilihan == "1":
                jenis_kendaraan = "Mobil"
                kode_jenis = "MB"
                tarif_per_jam = 5000
            else:
                jenis_kendaraan = "Motor"
                kode_jenis = "MT"
                tarif_per_jam = 3000

            if not tanggal:
                raise ValueError("Mohon lengkapi Tanggal.")

            # Cek Member
            telp_member = request.form.get('telp_member', '').strip()
            is_member = False
            
            if telp_member:
                if not telp_member.isdigit():
                     raise ValueError("Nomor telepon member harus berupa angka.")
                if not (10 <= len(telp_member) <= 13):
                     raise ValueError("Nomor telepon member harus 10-13 digit.")

                member_found = next((m for m in data['member'] if m['telepon'] == telp_member), None)
                
                if member_found:
                    is_member = True
                    member_found["jumlah_kunjungan"] += 1
                    flash(f"Member terdeteksi: {member_found['nama']}", "success")
                else:
                    raise ValueError(f"Gagal! Nomor {telp_member} tidak terdaftar dalam sistem member.")

            no_resi = buat_no_resi(kode_jenis, jam_masuk, menit_masuk, no_kendaraan)
            
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
                "telp_member": telp_member if is_member else "",
                "waktu_masuk_str": f"{jam_masuk:02d}:{menit_masuk:02d}",
                'tanggal': tanggal
            })
            
            if save_data(data):
                flash(f"Berhasil! Kendaraan {no_kendaraan} masuk.", "success")
                new_resi = no_resi
            else:
                flash("Gagal menyimpan data ke database. Coba lagi.", "danger")

        except ValueError as ve:
            flash(str(ve), "warning")
            
        except Exception as e:
            print(f"[CRITICAL ERROR] di route /masuk: {e}")
            flash("Terjadi kesalahan sistem. Hubungi admin.", "danger")

    return render_template('masuk.html',
                            new_resi=new_resi, 
                            jam_sekarang=sekarang.hour, 
                            menit_sekarang=sekarang.minute)

@app.route('/keluar', methods=['GET', 'POST'])
def parkir_keluar():
    data = load_data()
    currentTicket = None
    currentJam = 0
    currentMenit = 0
    isConfirmed = '0'
    totalBiaya = 0
    totalDurasi = 0
    tanggal_keluar = ""
    
    if request.method == 'POST':
        try:
            isConfirmed = request.form.get('is_confirm')

            if isConfirmed == '0':
              no_resi = request.form.get('no_resi', '')
              tanggal_keluar = request.form.get('tanggal', '')

              if not no_resi:
                  raise ValueError("Mohon lengkapi Nomor Resi.")
              
              if not tanggal_keluar:
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
                        totalBiaya, totalDurasi = calculate_parking_fee(tiket_aktif, tanggal_keluar, jam_keluar, menit_keluar)

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
                tanggal_keluar = request.form.get('tanggal')

                for tiket_aktif in data['tiket_aktif']:
                    if tiket_aktif['no_resi'] == no_resi:
                        currentTicket = tiket_aktif

                data['riwayat_transaksi'].append({
                  "no_resi": currentTicket['no_resi'],
                  "no_kendaraan": currentTicket['no_kendaraan'],
                  "jenis_kendaraan": currentTicket['jenis_kendaraan'],
                  "waktu_masuk": currentTicket['waktu_masuk_str'],
                  "waktu_keluar": f"{currentJam}:{currentMenit}",
                  "tanggal_keluar": tanggal_keluar,
                  "durasi": f"{totalDurasi} Jam",
                  "total_bayar": total_bayar,
                  "is_member": currentTicket['is_member']
                })
                data['tiket_aktif'].remove(currentTicket)       
                save_data(data)

        except ValueError as ve:
            flash(str(ve), "warning")
            
        except Exception as e:
            print(f"[CRITICAL ERROR] di route /keluar: {e}")
            flash("Terjadi kesalahan sistem. Hubungi admin.", "danger")

    return render_template('keluar.html', 
                           tiket_aktif=data["tiket_aktif"], 
                           currentTicket=currentTicket, 
                           totalBiaya=format(totalBiaya, ',').replace(',', '.'), 
                           totalDurasi=totalDurasi, currentJam=currentJam, 
                           currentMenit=currentMenit, 
                           isConfirmed=isConfirmed, 
                           tanggal_keluar=tanggal_keluar)

@app.route('/member', methods=['GET', 'POST'])
def kelola_member():
    data = load_data()
    
    if request.method == 'POST':
        try:
            nama = request.form.get('nama', '').strip()
            telepon = request.form.get('telepon', '').strip()
            
            # --- VALIDASI INPUT ---
            if not nama:
                raise ValueError("Nama lengkap wajib diisi.")
            
            if not telepon.isdigit():
                raise ValueError("Nomor telepon harus berupa angka saja.")
            
            if not (10 <= len(telepon) <= 13):
                raise ValueError("Nomor telepon harus antara 10 sampai 13 digit.")
            
            already_exists = any(m['telepon'] == telepon for m in data['member'])
            if already_exists:
                raise ValueError(f"Nomor {telepon} sudah terdaftar.")
            
            # --- SIMPAN DATA ---
            new_member = {
                "nama": nama,
                "telepon": telepon,
                "tanggal_daftar": datetime.now().strftime("%Y-%m-%d"),
                "jumlah_kunjungan": 0,
            }
            
            data["member"].append(new_member)
            
            if save_data(data):
                flash(f"Berhasil! Member {nama} telah ditambahkan.", "success")
            else:
                flash("Gagal menyimpan ke database.", "danger")
                
        except ValueError as e:
            flash(str(e), "warning")
        except Exception as e:
            print(f"Error: {e}")
            flash("Terjadi kesalahan sistem.", "danger")
            
        return redirect(url_for('kelola_member'))

    return render_template('kelola_member.html',
                            members=data["member"])

@app.route('/member/view/<telepon>')
def lihat_member(telepon):
    data = load_data()
    member = next((m for m in data['member'] if m['telepon'] == telepon), None)
    
    if not member:
        flash("Member tidak ditemukan.", "warning")
        return redirect(url_for('kelola_member'))
        
    return render_template('lihat_member.html',
                            member=member)

@app.route('/member/update', methods=['POST'])
def update_member():
    data = load_data()
    
    old_telepon = request.form.get('old_telepon') 
    nama_baru = request.form.get('nama', '').strip()
    telepon_baru = request.form.get('telepon', '').strip()
    
    try:
        if not nama_baru:
            raise ValueError("Nama tidak boleh kosong.")
        if not telepon_baru.isdigit():
            raise ValueError("Nomor telepon harus angka.")
        if not (10 <= len(telepon_baru) <= 13):
            raise ValueError("Nomor telepon harus 10-13 digit.")

        member_index = next((index for (index, d) in enumerate(data['member']) if d["telepon"] == old_telepon), None)
        
        if member_index is None:
            raise ValueError("Data member tidak ditemukan.")

        if old_telepon != telepon_baru:
            exists = any(m['telepon'] == telepon_baru for m in data['member'])
            if exists:
                raise ValueError(f"Nomor {telepon_baru} sudah digunakan member lain.")

        data['member'][member_index]['nama'] = nama_baru
        data['member'][member_index]['telepon'] = telepon_baru
        
        if save_data(data):
            flash(f"Data member {nama_baru} dengan nomor telepon {telepon_baru} berhasil diperbarui.", "success")
        else:
            flash("Gagal menyimpan perubahan.", "danger")

    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        print(f"Error Update: {e}")
        flash("Terjadi kesalahan sistem.", "danger")

    return redirect(url_for('kelola_member'))

@app.route('/member/delete/<telepon>')
def hapus_member(telepon):
    data = load_data()
    
    member_to_delete = next((m for m in data['member'] if m['telepon'] == telepon), None)
    
    if member_to_delete:
        # Buat list baru yang isinya SEMUA member KECUALI yang nomornya mau dihapus
        data["member"] = [m for m in data["member"] if m['telepon'] != telepon]
        
        if save_data(data):
            flash(f"Member {member_to_delete['nama']} berhasil dihapus.", "success")
        else:
            flash("Gagal update database.", "danger")
    else:
        flash("Member tidak ditemukan.", "warning")
        
    return redirect(url_for('kelola_member'))

@app.route('/riwayat')
def riwayat_transaksi():
    data = load_data()
    transaksi = data.get("riwayat_transaksi", [])
    
    search_query = request.args.get('search', '').upper()
    filter_jenis = request.args.get('jenis', '')
    filter_status = request.args.get('status', '')

    filtered_data = []
    
    for item in transaksi:
        match_search = True
        match_jenis = True
        match_status = True
        
        if search_query:
            if (search_query not in item['no_resi'].upper()) and \
               (search_query not in item['no_kendaraan'].upper()):
                match_search = False
        
        if filter_jenis and filter_jenis != 'Semua Jenis':
            if item['jenis_kendaraan'] != filter_jenis:
                match_jenis = False
                
        if filter_status and filter_status != 'Semua Status':
            is_member_item = item.get('is_member', False)
            if filter_status == 'Member' and not is_member_item:
                match_status = False
            elif filter_status == 'Reguler' and is_member_item:
                match_status = False

        if match_search and match_jenis and match_status:
            filtered_data.append(item)

    total_transaksi = len(filtered_data)
    total_pendapatan = 0
    
    for t in filtered_data:
        bayar_str = str(t['total_bayar']).replace('.', '').replace(',', '')
        if bayar_str.isdigit():
            total_pendapatan += int(bayar_str)

    pendapatan_formatted = "{:,.0f}".format(total_pendapatan).replace(',', '.')

    return render_template('riwayat.html', 
                           transaksi=filtered_data,
                           total_transaksi=total_transaksi,
                           total_pendapatan=pendapatan_formatted,
                           search_query=search_query,
                           filter_jenis=filter_jenis,
                           filter_status=filter_status)

if __name__ == '__main__':
    app.run(debug=True)