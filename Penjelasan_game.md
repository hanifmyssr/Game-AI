# 🎮 Penjelasan Alur Game Bakekok: Implementasi CSP & Local Search

Dokumen ini disusun untuk memberikan gambaran komprehensif, terstruktur, dan mudah dipahami mengenai penambahan materi **Tubes Tahap 3 (Local Search)** dan **Tahap 4 (Constraint Satisfaction Problem / CSP)** ke dalam proyek game *Bakekok*.

---

## 1. Latar Belakang & Masalah Saat Ini

Pada game *Bakekok* versi saat ini:
* Setiap kali pemain berpapasan dengan NPC di peta, pertarungan yang terjadi selalu **1 lawan 1 dengan kondisi statis**.
* Status musuh selalu sama di setiap pertempuran (HP = 100, Potion = 2, aksi standar).
* **Tantangan tugas baru kita:** Sebelum NPC menyerang, sistem AI harus mampu **meracik komposisi lawan secara otomatis dan dinamis** (berapa jumlah NPC yang menyerang, apa kelas/karakternya, serta item/potion apa yang mereka bawa) dengan target:
  > **"Tidak terlalu gampang (agar pemain tidak bosan) dan tidak terlalu sulit (agar pemain tidak frustasi)."**

---

## 2. Gambaran Rangkaian Alur Permainan (Gameplay Loop)

Ketika game dimainkan secara penuh, alur eksekusi permainannya adalah sebagai berikut:

```
[1. EKSPLORASI MAP]
Player berjalan di grid ──> Dikejar NPC (Pathfinding A* / UCS)
         │
         │ (NPC berhasil menabrak Player!)
         ▼
[2. FASE BARU: PRE-BATTLE OVERLAY] 🌟 <--- INTI PENAMBAHAN TUGAS KITA!
Sistem AI bekerja di balik layar (hitungan milidetik):
  a. CSP          : Menyaring kombinasi squad yang LEGAL & SESUAI ATURAN.
  b. Local Search : Memilih kombinasi yang TINGKAT KESULITANNYA PALING IDEAL.
  c. Layar Pratinjau : Muncul UI kartu squad lawan (Kelas, HP, Item, & Visualisasi AI).
         │
         │ (Player menekan tombol "Mulai Battle")
         ▼
[3. ARENA BATTLE TURN-BASED]
Player duel melawan squad NPC secara berurutan (Tag-Team).
NPC memilih jurus serang/potion menggunakan Minimax / Alpha-Beta / Expectimax.
         │
         │ (Pertarungan selesai)
         ▼
[4. KEMBALI KE MAP]
Menang ──> Kembali ke map, NPC yang dikalahkan hilang.
Kalah  ──> Tampil layar Game Over / Respawn.
```

---

## 3. Di Mana Letak CSP dan Apa Fungsinya?

### 📌 Letak Eksekusi:
Berjalan pada **Fase Pre-Battle** (tepat saat transisi dari Eksplorasi menuju Battle) di dalam modul `game/npc_config_csp.py`.

### 📌 Peran: **"Wasit / Penjaga Legalitas Aturan Permainan"**
Jika game memilih kombinasi musuh secara acak tanpa aturan, bisa terjadi komposisi yang curang atau merusak logika game (misal: musuh membawa 99 potion, total HP musuh 9999, atau 3 mage sakti sekaligus yang membuat player langsung kalah dalam 1 giliran).

**CSP (Constraint Satisfaction Problem)** bertugas memastikan semua variabel musuh mematuhi batasan (*constraints*):

1. **Variabel yang Diatur:**
   * Jumlah NPC penyerang ($1$ sampai $3$ karakter).
   * Tipe kelas tiap NPC (*Warrior*, *Mage*, atau *Ranger*).
   * Alokasi HP masing-masing NPC.
   * Jumlah Potion masing-masing.
   * Item peralatan yang dibawa (Pedang / Tameng / Sepatu).
2. **Batasan (Constraints):**
   * *Budget HP Total:* Total HP seluruh squad tidak boleh melebihi batas wajar (misal maksimal 220 HP).
   * *Budget Potion:* Total potion satu tim tidak boleh lebih dari 3 buah.
   * *Aturan Job:* Mage tidak boleh memakai tameng besi berat; Warrior tidak boleh memakai item sihir berlebih.
   * *Konsistensi Role:* Karakter tangguh harus dipasangkan dengan profil evaluasi bertahan (*Defensive*), dsb.
3. **Teknik yang Digunakan:**
   * **Backtracking Search**: Menelusuri kemungkinan konfigurasi secara sistematis.
   * **MRV (Minimum Remaining Values)**: Memilih variabel dengan opsi paling terbatas terlebih dahulu agar pencarian efisien.
   * **LCV (Least Constraining Value)**: Memilih nilai yang paling sedikit membatasi pilihan variabel lain.
   * **AC-3 (Arc Consistency)**: Memangkas (*pruning*) nilai-nilai domain yang tidak mungkin valid sejak awal.

> **Kesimpulan CSP:** Menjamin squad musuh **VALID, LOGIS, dan MEMATUHI ATURAN**.

---

## 4. Di Mana Letak Local Search dan Apa Fungsinya?

### 📌 Letak Eksekusi:
Bekerja berdampingan dengan CSP pada **Fase Pre-Battle** di dalam modul `game/npc_config_optimizer.py`.

### 📌 Peran: **"Penyeimbang Tingkat Kesulitan (Difficulty Balancer)"**
Setelah CSP memastikan opsi squad yang ada itu sah/legal, AI harus memilih: **mana konfigurasi yang tingkat kesulitannya paling pas untuk kondisi pemain saat ini?**

Jika pemain sedang sekarat (sisa HP 25 dan tanpa potion), memunculkan 3 musuh tangguh akan membuat pemain frustasi. Sebaliknya, jika pemain masih segar bugar dengan potion penuh, melawan 1 musuh lemah akan membosankan.

**Local Search** mengoptimasi masalah ini dengan cara:

1. **Fungsi Objektif ($f(s)$ / Skor Kesulitan):**
   * Menghitung nilai kesulitan dari $0.0$ (sangat mudah) hingga $1.0$ (hampir mustahil).
   * Menargetkan nilai ke arah **"Fun Zone" ($\approx 0.55$)**.
2. **Mekanisme Pencarian:**
   * AI memulai dari satu konfigurasi awal yang valid.
   * AI mengeksplorasi konfigurasi tetangga (*neighbor states*), misalnya: *"bagaimana jika kelas diganti Ranger?"* atau *"bagaimana jika potion dikurangi 1 dan HP ditambah 15?"*.
   * Mengambil langkah yang meminimalkan selisih jarak menuju target *Fun Zone*.
3. **Pilihan Algoritma yang Disediakan:**
   * **Hill Climbing (dengan Sideways Move & Random Restart)**: Bergerak menuju tetangga yang lebih baik.
   * **Simulated Annealing**: Mengizinkan penerimaan solusi suboptimal secara probabilistik berdasarkan temperatur untuk keluar dari *local optima*.
   * **Genetic Algorithm**: Melakukan seleksi, *crossover*, dan mutasi dari populasi kandidat squad.

> **Kesimpulan Local Search:** Menjamin pertarungan **TIDAK TERLALU GAMPANG dan TIDAK TERLALU SULIT**.

---

## 5. Hubungan Kerja Sama Keduanya (CSP + Local Search)

Analogi sederhananya adalah **Kerja Sama Koki dan Pencicip Rasa**:
* **CSP** memastikan bahan makanan halal, takaran bumbu aman, dan sesuai resep dasar.
* **Local Search** mencicipi variasi hidangan yang lolos resep tadi, lalu memilih takaran rasa yang paling pas dengan selera penikmat saat itu.

```
[Player Tersentuh NPC di Map]
              │
              ▼
  [ CSP: Backtracking + AC-3 ]
  Menghasilkan kandidat squad yang LEGAL & SESUAI ATURAN
              │
              ▼
  [ Local Search: Hill Climbing / SA / GA ]
  Mencari kombinasi dengan TINGKAT KESULITAN TERBAIK (~0.55)
              │
              ▼
  [ Squad Terbaik Terpilih! ]
  Squad musuh siap masuk ke Arena Pertarungan
```

---

## 6. Fitur Baru pada Antarmuka (Pre-Battle Overlay)

Pada saat demonstrasi atau presentasi tugas, tim penilai/dosen dapat melihat secara transparan bahwa algoritma AI benar-benar berjalan melalui **Pre-Battle Overlay**:

1. **Kartu Profil Squad Musuh:**
   * Menampilkan avatar pixel-art kucing lawan (Warrior, Mage, Ranger).
   * Menampilkan bar status HP dan icon item/potion yang dibawa.
2. **Panel Visualisasi & Pembuktian AI:**
   * **Indikator CSP:** Menampilkan daftar *constraints* yang terpenuhi, domain variabel, dan waktu eksekusi.
   * **Grafik Local Search:** Menampilkan riwayat iterasi perbaikan nilai fungsi objektif dari state awal hingga solusi optimum.
   * **Kontrol Interaktif:** Terdapat *dropdown* untuk mengganti algoritma optimasi (Hill Climbing, Simulated Annealing, Genetic Algorithm) dan tombol **"Re-Optimize / Acak Ulang"** yang dapat diuji secara langsung.
3. **Tombol Konfirmasi ("Mulai Duel"):**
   * Pemain dapat menekan tombol ini untuk melangkah ke arena pertarungan turn-based.

---

## 7. Mekanisme Pendukung: Item Player, Peti Gacha di Map, dan Darah Berkelanjutan

Agar ekosistem game terasa nyata dan AI kita terlihat sangat pintar saat demo, ada beberapa mekanisme pendukung yang kita terapkan:

### A. Apakah Player Punya Item?
**Tentu punya!** Player memiliki tas bawaan:
* **Ramuan:** Health Potion (+30 HP) dan Mega Potion (+70 HP).
* **Perlengkapan Buff:** Pedang (+Serangan), Tameng (+Pertahanan), dan Sepatu (+Kecepatan).
* Status item dan HP Player inilah yang menjadi **input bagi AI** untuk menentukan seberapa kuat musuh yang harus dihadirkan.

### B. Peti Harta di Map dengan Animasi Gacha Acak (Loot Box)
* Di map eksplorasi, pemain bisa mendatangi peti (*Chest*) dan menekan tombol `[E]`.
* **Animasi Gacha / Roulette:** Akan muncul efek pop-up animasi kartu/item berputar selama 1 detik sebelum berhenti di hadiah yang didapat (misal: dapat Mega Potion langka atau Pedang).
* *Catatan Penting:* **Fitur ini sama sekali tidak melanggar ketentuan materi Tubes!** Justru fitur ini membuktikan ke dosen bahwa ketika Player mendapat item bagus dari peti, AI Local Search langsung merespons dengan menyiapkan squad lawan yang lebih tangguh.

### C. Mengapa Darah Player Bisa Berkurang Saat Masuk Battle? (Persistent HP)
* Darah Player **tidak langsung sembuh 100% otomatis** setelah menang pertarungan. Jika di duel pertama sisa HP Player tinggal 40, maka saat tertabrak musuh kedua, Player akan masuk duel dengan HP 40 tersebut.
* **Di sinilah AI kita unjuk gigi:** Mengetahui Player sedang sekarat, Local Search & CSP otomatis meracik musuh yang lebih ringan agar Player tidak langsung mati konyol (*tidak bikin frustasi*).

### D. Jumlah NPC di Map vs di Battle (Sistem 3 NPC & Opsi B)
* **Ada 3 Kucing di Map (Beda Warna / Palette Swap):**
  * **Oyen (Oranye):** Kucing utama yang sudah ada sejak Tahap 1.
  * **Kuro (Hitam) & Shiro (Abu-abu):** 2 Kucing patroli baru yang menjaga area masing-masing.
* **Mekanisme Pengejaran Cerdas (Opsi B - Anti-Clash Visual):**
  * Ketika tombol `[SPASI]` ditekan, **hanya Oyen (NPC Utama) yang mengejar Player**.
  * Dua kucing lainnya tetap santai berpatroli bolak-balik di pos mereka (Waypoint Patrol).
  * **Mengapa demikian?** Agar visualisasi garis jalur A* dan node pencarian di layar tidak saling tabrakan atau berantakan jika banyak musuh mengejar sekaligus. Tampilan layar tetap bersih dan rapi!
* **Pemicu Battle (Encounter Leader):**
  * Baik jika Oyen berhasil mengejar Player, **atau** Player tidak sengaja berpapasan dan menabrak salah satu kucing patroli saat berjalan, duel Pre-Battle tetap akan terpicu! Kucing tersebut akan memanggil bala bantuan kawanannya (**Squad 1-3 musuh**) untuk duel *tag-team*!

### E. Mode Simulator di Pre-Battle Overlay (Untuk Demo Dosen)
* Agar saat presentasi kita tidak perlu repot-repot sengaja membuat diri kita sekarat saat bermain, di Pre-Battle Overlay kita pasang slider:
  > *"Simulasikan Kondisi Player: [HP = 25, Potion = 0]"*
* Begitu diklik tombol *"Re-Optimize"*, dosen bisa langsung melihat grafik Local Search dan aturan CSP langsung berubah meracik musuh yang lebih bersahabat secara live!

### F. Tampilan Arena Battle: Sistem Tag-Team (1v1 Aktif + Cadangan di Pojok)
* **Kenapa nggak 3 musuh maju barengan?**
  * Secara teori AI, algoritma **Minimax & Alpha-Beta** dirancang untuk *2-Player Zero-Sum Game* (1 lawan 1). Duel 1v1 turn-based adalah implementasi paling sah dan murni dari Minimax.
  * Secara visual, arena jadi tidak penuh sesak. Player berdiri di kiri, 1 musuh aktif berdiri di kanan, dan sisa kawanannya mengantre rapi di pojok kanan atas dengan bar HP kecil (*bench / antrean cadangan*).
  * Begitu musuh pertama kalah, musuh cadangan berikutnya melangkah maju menggantikan!
* **Gaya Main AI Menyesuaikan Karakter:**
  * Musuh **Mage** otomatis bermain **Aggressive** (fokus damage besar).
  * Musuh **Warrior** otomatis bermain **Defensive / Balanced** (banyak menahan dan counter).

### G. Decision Tree Layar Penuh (Semi-Transparan) dengan Tombol Khusus
* **Bukan lagi kotak sempit di bawah layar:**
  * Selama duel berlangsung, area bawah arena dibuat bersih dan lapang agar pertarungan terlihat megah.
* **Tombol Pembuka Tree Pop-up:**
  * Disediakan tombol **`[🌲 Lihat Decision Tree]`** (atau tekan tombol `[T]`).
  * Saat diklik, muncul layar pop-up semi-transparan (opasitas gelap 85%) menutupi layar. Pertarungan di belakang tetap terlihat samar-samar, sementara **pohon keputusan Minimax ditampilkan secara BESAR, LEGA, dan BISA DIGESER (Pan/Zoom)**.
  * Ada tombol silang **`[✕ Tutup / ESC]`** untuk langsung kembali ke pertarungan.

---

## 8. Kesimpulan untuk Anggota Kelompok

1. **Fitur Lama Tetap Utuh 100%:**
   * Algoritma **Tahap 1 (A* / UCS)** tetap menggerakkan NPC di peta grid.
   * Algoritma **Tahap 2 (Minimax / Alpha-Beta / Expectimax)** tetap mengambil keputusan aksi serang/potion saat pertarungan turn-based berlangsung.
2. **Fokus Tambahan Kita:**
   * Menambahkan logika cerdas di **fase persiapan sebelum menyerang (Pre-Battle)**, di mana **CSP menjaga keabsahan aturan** dan **Local Search menjaga keseimbangan tingkat kesulitan permainan**.
   * Menghidupkan suasana game dengan **Peti Gacha acak**, **Persistent HP**, **Duel Tag-Team Squad**, serta **Full-Screen Decision Tree Modal** yang sangat memukau saat dipresentasikan.


