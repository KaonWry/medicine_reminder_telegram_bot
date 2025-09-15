# Bot Pengingat Telegram

## Deskripsi

Bot ini membantu pengguna Telegram untuk mengatur dan menerima pengingat secara otomatis sesuai jadwal yang diinginkan. Bot dirancang agar mudah digunakan, fleksibel, dan dapat diandalkan, terutama bagi pengguna yang memiliki jadwal rutin setiap hari.

## Fitur Utama

- **Tambah Pengingat**: Pengguna dapat menambah pengingat dengan format waktu jam dan menit, baik menggunakan titik dua (08:00) maupun titik (08.00). Nama pengingat dapat ditulis bebas sesuai kebutuhan.
- **Daftar Pengingat**: Melihat semua pengingat yang sudah dibuat, lengkap dengan penomoran agar mudah dihapus.
- **Hapus Pengingat**: Menghapus pengingat berdasarkan nomor yang muncul di daftar, baik secara langsung maupun melalui percakapan interaktif.
- **Notifikasi Otomatis**: Bot akan mengirim pesan pengingat secara otomatis pada waktu yang sudah ditentukan setiap hari.
- **Percakapan Interaktif**: Jika pengguna tidak memberikan argumen lengkap, bot akan memandu pengguna secara bertahap untuk menambah atau menghapus pengingat.
- **Ketahanan Downtime**: Jika bot sempat offline, pengingat yang terlewat tetap akan dikirim saat bot kembali aktif.

## Cara Penggunaan

1. **/start**: Menampilkan petunjuk penggunaan dan daftar fitur bot.
2. **/add [waktu] [nama pengingat]**: Menambah pengingat baru. Contoh: `/add 08:00 Minum Obat Pagi` atau `/add 08.00 Minum Obat Pagi`.
3. **/list**: Melihat daftar semua pengingat yang sudah dibuat.
4. **/delete [nomor]**: Menghapus pengingat berdasarkan nomor di daftar. Contoh: `/delete 1`.

Jika perintah /add atau /delete tidak diberikan argumen lengkap, bot akan memulai percakapan interaktif untuk membantu pengguna.

## Cara Deploy dan Menjalankan Bot

1. **Persiapan Environment**
   - Pastikan Python sudah terinstal.
   - Buat virtual environment dan aktifkan.
   - Install semua dependensi dengan perintah:

     ```cmd
     pip install -r requirements.txt
     ```

2. **Konfigurasi Token**
   - Buat file `.env` di folder utama.
   - Tambahkan baris berikut dengan token bot Telegram Anda:

     ```txt
     BOT_TOKEN=token_anda
     ```

3. **Inisialisasi Database**
   - Jalankan file `init_db.py` untuk membuat database pengingat:

     ```cmd
     python src/init_db.py
     ```

4. **Menjalankan Bot**
   - Untuk Windows, jalankan:

     ```cmd
     start.bat
     ```

   - Untuk Linux, jalankan:

     ```bash
     ./start.sh
     ```

   - Bot akan berjalan dan siap menerima perintah di Telegram.
5. **Menghentikan Bot**
   - Gunakan `stop.bat` (Windows) atau `stop.sh` (Linux) untuk menghentikan bot.

## Struktur Proyek

- `.env` : File token bot Telegram.
- `requirements.txt` : Daftar dependensi Python.
- `start.bat` / `start.sh` : Script untuk menjalankan bot.
- `stop.bat` / `stop.sh` : Script untuk menghentikan bot.
- `src/bot.py` : Entry point utama, mendaftarkan semua handler dan scheduler.
- `src/init_db.py` : Inisialisasi database SQLite.
- `src/reminders.db` : File database pengingat.
- `src/helpers.py` : Fungsi utilitas untuk ekstraksi data dan validasi.
- `src/add.py` : Logika penambahan pengingat.
- `src/delete.py` : Logika penghapusan pengingat.
- `src/notify.py` : Logika notifikasi dan penjadwalan.

## Catatan

- Bot ini hanya menyimpan data pengingat untuk masing-masing pengguna secara privat.
- Semua pengingat akan dikirim sesuai waktu yang diatur, dan tidak akan terlewat meskipun bot sempat offline.
- Struktur kode yang modular memudahkan pengembangan dan pemeliharaan.

---
Dibuat untuk membantu pengguna Telegram lebih disiplin dan tepat waktu dalam menjalankan kebiasaan setiap hari.
