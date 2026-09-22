# Bakekok / BoluKesepian - Game AI (Tahap 1 & Tahap 2)

Proyek Tugas Besar Mata Kuliah Kecerdasan Buatan - Kelompok 7 (Universitas Pendidikan Indonesia).

---

## 🌟 Ringkasan Fitur

### Tahap 1: Pathfinding & Algoritma Pencarian Jalur
- **Uniform Cost Search (UCS)** & **A* Search** pada peta grid berbobot (*cost jalan tanah 0.5 vs rumput 1.0*).
- **Heuristik**: Manhattan, Euclidean, Chebyshev.
- **Visualisasi World-Space**: Pewarnaan ubin yang diekspansi dan lintasan optimal *real-time*.
- **Sidebar Debug Overlay**: Menampilkan statistik komparasi node ekspansi, waktu eksekusi (ms), dan rasio efisiensi.

### Tahap 2: Duel Turn-Based NPC vs Player (Adversarial Search)
- **Transisi Otomatis**: Jika NPC mendekati Player (jarak Manhattan $\le 1$), permainan beralih ke arena pertempuran bergilir.
- **Formulasi Game AI**:
  - **State**: $HP_{\text{player}}, HP_{\text{npc}} \in [0, 100]$, $Potions \in [0, 3]$, status `Defending`, dan giliran petarung.
  - **Aksi Legal ($b \le 4$)**:
    1. `ATTACK`: Serangan standar (18 damage, tereduksi jadi 6 jika musuh bertahan).
    2. `HEAVY_ATTACK`: Serangan telak berisiko tinggi (30 damage, akurasi 75% pada Expectimax).
    3. `DEFEND`: Memasang perisai/tangkisan untuk mengurangi damage musuh sebesar ~65%.
    4. `POTION`: Memulihkan +25 HP jika persediaan tersedia.
  - **Terminal Test & Utility**: Evaluasi kemenangan $+1000$ (NPC menang) vs $-1000$ (Player menang) vs $0$ (seri).
  - **Evaluation Functions**:
    - `Balanced`: Pertimbangan selisih HP dan simpanan potion proporsional.
    - `Aggressive`: Prioritas tinggi menekan dan mengeksekusi HP player.
    - `Defensive`: Fokus menjaga kelangsungan hidup, pertahanan, dan pemulihan diri.
- **Mesin AI Adversarial**:
  - **Pure Minimax**: Pencarian tanpa pemangkasan.
  - **Alpha-Beta Pruning**: Memangkas hingga **85.7% node** pada depth 6 dengan keputusan identik.
  - **Move Ordering**: Mengurutkan aksi menjanjikan untuk mempercepat pemangkasan hingga **55.8%**.
  - **Expectimax**: Memodelkan ketidakpastian/stokastik pada akurasi serangan.
- **Live Battle Debug Overlay**:
  - Pilihan Dropdown Algoritma & Fungsi Evaluasi.
  - Pengaturan batas kedalaman (*depth limit 1–8*) dan tombol toggle *Move Ordering*.
  - Tabel live pertimbangan nilai/skor setiap aksi di root node (`ATTACK`, `HEAVY_ATTACK`, `DEFEND`, `POTION`).
  - Metrik node count, cabang yang terpotong (*pruned*), dan waktu berpikir (ms).

---

## 🎮 Kontrol Permainan

### Mode Eksplorasi (Peta)
- **[W, A, S, D]** atau **[Tombol Panah]**: Gerakkan Player (Bolu).
- **[Spasi]**: Panggil / aktifkan NPC agar mengejar Player.
- **[B]**: Pintas langsung masuk ke Mode Duel (Pertarungan).
- **[Esc]**: Keluar dari permainan.

### Mode Duel (Pertarungan Turn-Based)
- **[1 / A]**: Aksi `ATTACK` (18 damage)
- **[2 / S]**: Aksi `HEAVY_ATTACK` (30 damage)
- **[3 / D]**: Aksi `DEFEND` (-65% damage reduction)
- **[4 / W]**: Aksi `POTION` (+25 HP heal)
- **[R]**: Reset / mulai ulang duel.
- **[Tab]**: Kembali ke Mode Eksplorasi Peta.

---

## 🚀 Cara Menjalankan

1. Pastikan Python 3.10+ dan Pygame telah terpasang:
   ```bash
   pip install -r requirements.txt
   ```
2. Jalankan permainan:
   ```bash
   python main.py
   ```
3. Menjalankan rangkaian uji eksperimen & benchmark:
   ```bash
   python scratch/run_experiments.py
   ```

Dokumen lengkap hasil pengujian dan analisis akademis tersedia di [`LAPORAN_TAHAP_2.md`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/LAPORAN_TAHAP_2.md).

---

## 👥 Kelompok 7 - Universitas Pendidikan Indonesia
- Hanif Muyassar
- Moch Fadillah Pratama
- Muhammad Zidan Mirza Fedrieka
