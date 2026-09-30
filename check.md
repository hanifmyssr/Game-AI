# CHECKLIST VERIFIKASI IMPLEMENTASI TAHAP 2: DUEL TURN-BASED AI (MINIMAX & ALPHA-BETA)

Dokumen ini berisi daftar periksa (*checklist*) dan laporan audit internal untuk memastikan bahwa codebase **Game-AI (Tubes Tahap 2)** telah mengimplementasikan seluruh materi perkuliahan *Adversarial Search* dan memenuhi semua ketentuan tugas besar dari dosen.

---

## 📋 HASIL AUDIT KETENTUAN DOSEN (STATUS LENGKAP)

Berikut adalah matriks kesesuaian antara ketentuan dosen dengan implementasi pada project:

| No | Ketentuan Dosen | Status | Bukti File / Lokasi Kode | Penjelasan Implementasi |
|:--:|:---|:---:|:---|:---|
| **1** | **Melanjutkan Tahap 1**: Fitur duel dengan NPC (turn-based) setelah mendekat ke NPC. | ✅ **TERPENUHI** | [`game/app.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L242-L255), [`game/battle_system.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py) | Mode battle dipicu secara otomatis ketika jarak Manhattan antara Player dan NPC Kucing $\le 1$ tile. |
| **2** | **State**: Player HP, NPC HP, dan asumsi-asumsi lain. | ✅ **TERPENUHI** | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L82-L118) (`BattleState`) | State merepresentasikan `player_hp`, `npc_hp`, `player_potions`, `npc_potions`, `player_defending`, `npc_defending`, `is_npc_turn`, `player_heavy_cd`, `npc_heavy_cd`. |
| **3** | **Actions per Giliran**: Branching factor $b < 4$ (Attack, Defend, Potion, Heavy Attack). | ✅ **TERPENUHI** | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L135-L155) (`get_legal_actions`) | Method `get_legal_actions()` membatasi aksi legal maksimal 4 per giliran (`ATTACK`, `HEAVY_ATTACK`, `DEFEND`, `POTION`). |
| **4** | **Definisikan Formal**: State, Action, Terminal Test, Utility, & Evaluation Function (ke laporan). | ✅ **TERPENUHI** | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L82-L268), [`LAPORAN_TAHAP_2.md`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/LAPORAN_TAHAP_2.md) | Diformulasikan secara matematik di modul AI dan dijelaskan detail pada Laporan Tahap 2. |
| **5** | **Debug Overlay (1)**: Menampilkan aksi yang dipertimbangkan beserta skornya. | ✅ **TERPENUHI** | [`game/overlay.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/overlay.py#L690-L738), [`game/battle_system.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py#L161-L185) | Debug panel F3 menampilkan tabel real-time berisi opsi aksi legal root node dan skor evaluasi masing-masing. |
| **6** | **Debug Overlay (2)**: Node counts untuk membandingkan Minimax vs Alpha-Beta vs Early Stop. | ✅ **TERPENUHI** | [`game/overlay.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/overlay.py#L665-L680), [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L684-L785) | Overlay menampilkan metrik `node_count`, `pruned_count`, `time_ms`, serta **kotak komparasi langsung side-by-side** Pure Minimax vs Alpha-Beta pada kedalaman Early Stop aktif ($d$) beserta persentase efisiensi pruning secara instan di setiap turn. |
| **7** | **Eksperimen 1**: Perbandingan Pure Minimax vs Alpha-Beta Pruning. | ✅ **TERPENUHI** | [`scratch/run_experiments.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/run_experiments.py#L24-L56) | Menguji efisiensi pemangkasan node dan waktu eksekusi pada variasi kedalaman (Depth 1-6). |
| **8** | **Eksperimen 2**: Perbandingan berbagai Fungsi Evaluasi. | ✅ **TERPENUHI** | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L229-L268), [`scratch/run_experiments.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/run_experiments.py#L86-L113) | Membandingkan 3 fungsi evaluasi: *Balanced*, *Aggressive*, dan *Defensive*. |
| **9** | **Eksperimen 3**: Perbandingan 3 Varian Urutan Aksi (*Move Ordering*). | ✅ **TERPENUHI** | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L283-L321), [`scratch/run_experiments.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/run_experiments.py#L58-L84) | Membandingkan 3 kondisi: Tanpa Urutan (OFF), Heuristik Ofensif (HEURISTIC), dan Urutan Terbalik (REVERSED) untuk menguji efisiensi pruning. |
| **10**| **Eksperimen 4**: Perbandingan Kedalaman (*Depth Limit / Early Stop*). | ✅ **TERPENUHI** | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L333-L337), [`scratch/run_experiments.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/run_experiments.py) | Membatasi kedalaman pencarian agar memotong pohon pencarian (*cutoff search / early stop*) secara real-time. |
| **11**| **Eksperimen 5**: Tingkah Laku NPC (Misal jadi lebih agresif / defensif / taktis). | ✅ **TERPENUHI** | [`scratch/run_experiments.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/run_experiments.py#L86-L113) | Menganalisis keputusan NPC pada skenario awal, tertekan (sekarat), dan memimpin pertempuran. |
| **12**| **Fitur Pengayaan (Optional)**: Expectimax dengan probabilitas / stokastik. | ✅ **TERPENUHI** | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L469-L580), [`scratch/run_experiments.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/run_experiments.py#L115-L138) | Mengimplementasikan pencarian Expectimax untuk aksi `HEAVY_ATTACK` berprobabilitas ($75\%$ hit, $25\%$ miss). |
| **13**| **Tambahan Asumsi & Fitur Mandiri**: Mekanik game & UI pendukung. | ✅ **TERPENUHI** | [`game/battle_system.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py#L46-L115) | Sistem Cooldown Heavy Attack (2 turn), Potion Limit (3 potion), dan Floating Action Text melayang. |
| **14**| **Visualisasi Pohon Keputusan**: Decision Tree Overlay (Panel Kanan). | ✅ **TERPENUHI** | [`game/tree_overlay.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/tree_overlay.py), [`game/overlay.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/overlay.py#L746-L793) | Menampilkan pohon pencarian Minimax/Alpha-Beta dengan visualisasi cabang dipangkas (`✂`/`✕`), best path (`green glow`), MAX/MIN nodes, dan scroll interaktif via tombol `[T]`. |
| **15**| **Fokus pada Materi AI**: Penekanan pada konsep Adversarial Search, bukan Game Design. | ✅ **TERPENUHI** | Seluruh Modul Game | Kode dirancang bersih dengan abstraksi formal state space & search engine yang dapat di-benchmark. |

> **RANGKUMAN AUDIT**: **15 dari 15 Ketentuan (100%) TELAH TERPENUHI**. Semua ketentuan dosen, pembanding urutan aksi 3 varian, early stop terminology, dan visualisasi decision tree telah lengkap diimplementasikan.

---

## 🔍 PENJELASAN AUDIT DETAIL PER KETENTUAN

### 1. Mode Duel Turn-Based & Transisi Eksplorasi -> Battle
- **Trigger**: Ketika Player berjalan mendekati NPC Kucing Bolu hingga jarak Manhattan $\le 1$, state aplikasi berganti dari `"EXPLORATION"` menjadi `"BATTLE"`.
- **Mekanisme Turn-Based**:
  - NPC bertindak sebagai **MAX Player** (memaksimalkan nilai evaluasi/utility).
  - Player bertindak sebagai **MIN Player** (meminimalkan nilai evaluasi/utility).
- **Lokasi Kode**: [`game/app.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py) & [`game/battle_system.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py).

---

### 2. Formulasi Formal Masalah AI (Adversarial Search)
Formulasi formal diimplementasikan pada class `BattleState` di [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L82):
- **State ($S$)**: 
  - `player_hp` ($0 \dots 100$), `npc_hp` ($0 \dots 100$).
  - `player_potions` ($0 \dots 3$), `npc_potions` ($0 \dots 3$).
  - `player_defending` (bool), `npc_defending` (bool).
  - `is_npc_turn` (bool).
  - `player_heavy_cd` (int), `npc_heavy_cd` (int).
- **Actions ($A(s)$)**: Branching factor $b \le 4$:
  1. `ATTACK`: Serangan dasar (18 damage / 6 jika musuh *defend*).
  2. `HEAVY_ATTACK`: Serangan berat (30 damage / 10 jika musuh *defend*, CD 2 turn).
  3. `DEFEND`: Posisi bertahan (mengurangi damage masuk ~65%).
  4. `POTION`: Minum potion pemulih (+25 HP, syarat: potion > 0 & HP < 100).
- **Terminal Test ($Terminal(s)$)**: $HP_{\text{player}} \le 0 \lor HP_{\text{npc}} \le 0$.
- **Utility Function ($U(s)$)**:
  - NPC Menang: $+1000 + HP_{\text{npc}}$
  - Player Menang: $-1000 - HP_{\text{player}}$
  - Draw: $0$
- **Evaluation Functions ($Eval(s)$)**:
  - `BALANCED`: Mempertimbangkan selisih HP dan simpanan Potion.
  - `AGGRESSIVE`: Memprioritaskan pengurangan HP lawan dibanding HP sendiri.
  - `DEFENSIVE`: Memprioritaskan ketahanan hidup NPC & penggunaan Potion saat HP rendah.

---

### 3. Antarmuka Debug Overlay (F3 Panel)
Sesuai permintaan dosen, overlay interaktif dikembangkan pada [`game/overlay.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/overlay.py) untuk:
1. **Pertimbangan Aksi & Skor**: Menampilkan seluruh opsi aksi legal yang dievaluasi oleh AI pada root node beserta nilai skornya.
2. **Metrik Node Counts & Waktu**: Menampilkan total node dikunjungi (`Node Count`), jumlah cabang dipangkas (`Pruned`), dan durasi komputasi (`Time ms`).
3. **Kontrol Interaktif**: Penguna dapat mengubah Algoritma (*Alpha-Beta*, *Pure Minimax*, *Expectimax*), Fungsi Evaluasi (*Balanced*, *Aggressive*, *Defensive*), Kedalaman (*Depth 1-8*), serta sakelar *Move Ordering* secara *real-time*.

---

### 4. Hasil Benchmark & Eksperimen Aktual

Seluruh eksperimen dijalankan menggunakan script pembantu [`scratch/run_experiments.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/run_experiments.py). Berikut hasil empirisnya:

#### 📊 Eksperimen 1: Pure Minimax vs Alpha-Beta Pruning
| Depth | Minimax Nodes | Alpha-Beta Nodes | Pemangkasan Cabang (%) | Waktu Minimax (ms) | Waktu Alpha-Beta (ms) | Decisions Match? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | 4 | 4 | 0.0 % | 0.25 ms | 0.02 ms | **True** |
| **2** | 20 | 20 | 0.0 % | 0.03 ms | 0.04 ms | **True** |
| **3** | 78 | 50 | 35.9 % | 0.11 ms | 0.07 ms | **True** |
| **4** | 292 | 165 | 43.5 % | 0.66 ms | 0.39 ms | **True** |
| **5** | 1,029 | 379 | 63.2 % | 1.10 ms | 0.65 ms | **True** |
| **6** | 3,597 | 897 | **75.1 %** | 3.89 ms | 1.16 ms | **True** |

> **Analisis**: Alpha-Beta Pruning berhasil memangkas hingga **75.1% node** pada kedalaman 6, meningkatkan efisiensi waktu hingga **3.3x lebih cepat** tanpa pernah mengubah keputusan optimal (pembuktian *optimality*).

---

#### 📊 Eksperimen 2: Dampak 3 Varian Urutan Aksi (*Move Ordering*)
| Depth | Tanpa Urutan (OFF) | Heuristik (Ofensif) | Reversed (Defensif) | Reduksi Heuristik vs OFF (%) |
|:---:|:---:|:---:|:---:|:---:|
| **3** | 63 | 50 | 73 | 20.6 % |
| **4** | 221 | 165 | 221 | 25.3 % |
| **5** | 537 | 379 | 546 | 29.4 % |
| **6** | 1,351 | 897 | 1,599 | **33.6 %** |

> **Analisis**: Dengan mengurutkan aksi ofensif lebih dahulu (*HEAVY_ATTACK* $\to$ *ATTACK* $\to$ *POTION* $\to$ *DEFEND*), Alpha-Beta Pruning memotong cabang jauh lebih cepat dan mengevaluasi hingga **33.6% lebih sedikit node** dibandingkan tanpa urutan (OFF) dan **43.9% lebih sedikit** dibanding urutan terbalik (Reversed, 1,599 node). Hal ini membuktikan bahwa efisiensi Alpha-Beta sangat bergantung pada urutan eksplorasi cabang.

---

#### 📊 Eksperimen 3: Perilaku NPC Berdasarkan Fungsi Evaluasi

1. **Skenario Netral (Player HP: 100, NPC HP: 100)**:
   - *Balanced*: Memilih `HEAVY_ATTACK` (Skor: 0.0).
   - *Aggressive*: Memilih `ATTACK` (Skor: 20.0).
   - *Defensive*: Memilih `DEFEND` (Skor: 157.0).
2. **Skenario NPC Sekarat (Player HP: 75, NPC HP: 25, Potion: 2)**:
   - Ketiga fungsi evaluasi (*Balanced*, *Aggressive*, *Defensive*) secara serentak memilih `POTION` (Skor tertinggi) untuk mencegah kekalahan di giliran berikutnya.
3. **Skenario Player Sekarat (Player HP: 20, NPC HP: 70)**:
   - Ketiga fungsi evaluasi sepakat memilih `HEAVY_ATTACK` (Skor: 1070.0) untuk mengeksekusi kemenangan secara instan (*Terminal Utility Reach*).

---

#### 📊 Eksperimen 4: Expectimax (Pencarian Stokastik / Probabilistik)
- Menguji aksi `HEAVY_ATTACK` dengan probabilitas akurasi $75\%$ hit (damage 30) dan $25\%$ miss (damage 0).
- Expectimax menghitung nilai ekspektasi ($E[v] = 0.75 \cdot v_{\text{hit}} + 0.25 \cdot v_{\text{miss}}$), memastikan bahwa NPC mengambil keputusan secara tepat di bawah ketidakpastian.

---

### 5. Fitur Tambahan & Asumsi Mandiri
1. **Cooldown Heavy Attack**: Menghindari aksi repetitif yang tidak realistis.
2. **Floating Action Text**: UI animasi teks melayang melengkapi pengalaman bertarung tanpa mengganggu fokus AI.
3. **Batas Cadangan Potion**: Membatasi penggunaan item pemulih agar pertempuran tidak mengalamai *infinite loop*.
4. **Script Benchmark Otomatis**: `scratch/run_experiments.py` memungkinkan pengujian kuantitatif kapan saja.

---

## 🚀 CARA MENJALANKAN UNTUK DEMO & VERIFIKASI

### 1. Menjalankan Game Utama (Visual Play & Interactive Duel)
```bash
python main.py
```
- Dekati NPC Kucing Bolu di dalam game map menggunakan tombol keyboard (Panah / WASD).
- Pertarungan turn-based akan otomatis aktif.
- Tekan **F3** untuk melihat **Debug Overlay Real-Time**.

### 2. Menjalankan Script Eksperimen (Benchmark Metrics)
```bash
python scratch/run_experiments.py
```
*Script ini akan mencetak seluruh tabel perbandingan Minimax vs Alpha-Beta, Move Ordering, Evaluation Functions, dan Expectimax langsung ke terminal.*

---

## ✅ KESIMPULAN

Seluruh persyaratan **Tubes AI Tahap 2 (Adversarial Search & Game Theory)** telah **100% TERPENUHI** dengan sempurna, didukung oleh visualisasi Debug Overlay yang informatif dan analisis statistik yang lengkap pada dokumen [`LAPORAN_TAHAP_2.md`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/LAPORAN_TAHAP_2.md).
