# CHECKLIST VERIFIKASI IMPLEMENTASI TAHAP 2: DUEL TURN-BASED AI (MINIMAX & ALPHA-BETA)

Dokumen ini berisi daftar periksa (*checklist*) dan laporan audit internal untuk memastikan bahwa codebase **Game-AI (Tubes Tahap 2)** telah mengimplementasikan seluruh materi perkuliahan *Adversarial Search* dan memenuhi semua ketentuan tugas besar.

---

## 📊 RINGKASAN STATUS IMPLEMENTASI

| No | Komponen / Ketentuan Tahap 2 | Status | File Sumber Kode | Referensi Laporan |
|:--:|:---|:---:|:---|:---|
| **1** | **Mode Duel Turn-Based dengan NPC** | ✅ TERPENUHI | [`game/app.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py), [`game/battle_system.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py) | Bagian 1.1 |
| **2** | **Representasi State ($HP_{\text{player}}, HP_{\text{npc}}$, Potion, Cooldown, Defend)** | ✅ TERPENUHI | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L36-L72) (`BattleState`) | Bagian 1.1 |
| **3** | **Branching Factor $b \le 4$ (`ATTACK`, `HEAVY`, `DEFEND`, `POTION`)** | ✅ TERPENUHI | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L89-L109) (`get_legal_actions`) | Bagian 1.2 |
| **4** | **Formulasi Formal AI (State, Action, Terminal Test, Utility, Evaluation)** | ✅ TERPENUHI | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L73-L222) | Bagian 1.1 - 1.5 |
| **5** | **Debug Overlay: Aksi NPC & Skor Pertimbangan** | ✅ TERPENUHI | [`game/overlay.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/overlay.py), [`game/battle_system.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py#L436-L447) | Bagian 3 |
| **6** | **Debug Overlay: Node Counts & Waktu Komputasi** | ✅ TERPENUHI | [`game/overlay.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/overlay.py), [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L228-L330) | Bagian 3 |
| **7** | **Eksperimen 1: Minimax vs Alpha-Beta Pruning** | ✅ TERPENUHI | [`scratch/run_experiments.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/run_experiments.py) | Bagian 2.1 |
| **8** | **Eksperimen 2: Perbandingan Fungsi Evaluasi (Balanced, Aggressive, Defensive)** | ✅ TERPENUHI | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L183-L222) | Bagian 2.3 |
| **9** | **Eksperimen 3: Perbandingan Urutan Aksi (*Move Ordering*)** | ✅ TERPENUHI | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L286-L302) | Bagian 2.2 |
| **10**| **Eksperimen 4: Perbandingan Kedalaman (*Depth Limit / Early Stop*)** | ✅ TERPENUHI | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L243-L246) | Bagian 2.1 & 2.2 |
| **11**| **Eksperimen 5: Tingkah Laku NPC Berdasarkan Pendekatan** | ✅ TERPENUHI | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L183-L222) | Bagian 2.3 |
| **12**| **Fitur Pengayaan: Expectimax Search (Stokastik/Probabilitas)** | ✅ TERPENUHI | [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L333-L379) | Bagian 2.4 |
| **13**| **Asumsi & Fitur Tambahan Mandiri (Cooldown Heavy, Floating Text UI)** | ✅ TERPENUHI | [`game/battle_system.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py#L45-L107) | Bagian 1.2 & 3 |

---

## 🔍 AUDIT DETAIL PER KETENTUAN TAHAP 2

### 1. Transisi & Mode Duel Turn-Based dengan NPC
- [x] **Pemicu Pertarungan**: Saat Player mendekati NPC Kucing Hitam (Jarak Manhattan $\le 1$), permainan otomatis berpindah dari eksplorasi map ke mode duel.
- [x] **Giliran Bergantian (Turn-based)**:
  - NPC diposisikan sebagai agen **MAX** (memaksimalkan *utility/eval*).
  - Player diposisikan sebagai agen **MIN** (meminimalkan *utility/eval*).
- [x] **Lokasi Kode**: [`game/app.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py) & [`game/battle_system.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py).

---

### 2. Formulasi Formal Masalah AI (Adversarial Search)
- [x] **State ($S$)**:
  - Class `BattleState` di [`game/battle_ai.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L36).
  - Variabel state: `player_hp`, `npc_hp`, `player_potions`, `npc_potions`, `player_defending`, `npc_defending`, `is_npc_turn`, `player_heavy_cd`, `npc_heavy_cd`.
- [x] **Actions ($A(s)$)**:
  - Maksimal 4 aksi legal per giliran ($b \le 4$):
    1. `ATTACK`: Serangan standar (Damage 18 / 6 jika musuh bertahan).
    2. `HEAVY_ATTACK`: Serangan kuat (Damage 30 / 10 jika musuh bertahan, Cooldown 2 giliran).
    3. `DEFEND`: Posisi bertahan (Merenduksi damage diterima ~65%).
    4. `POTION`: Minum potion pemulih (+25 HP, hanya jika sisa potion > 0 & HP < 100).
  - Method `get_legal_actions()` menjamin branching factor $\le 4$.
- [x] **Terminal Test ($Terminal(s)$)**:
  - Evaluasi kondisi akhir: $HP_{\text{player}} \le 0 \lor HP_{\text{npc}} \le 0$.
  - Method `is_terminal()` di `BattleState`.
- [x] **Utility Function ($U(s)$)**:
  - Nilai pada terminal state:
    - NPC Menang: $+1000 + HP_{\text{npc}}$
    - Player Menang: $-1000 - HP_{\text{player}}$
    - Draw: $0$
  - Method `utility()` di `BattleState`.
- [x] **Evaluation Functions ($Eval(s)$)**:
  - **Balanced**: `eval_balanced(state)` di [`game/battle_ai.py:L183`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L183).
  - **Aggressive**: `eval_aggressive(state)` di [`game/battle_ai.py:L195`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L195).
  - **Defensive**: `eval_defensive(state)` di [`game/battle_ai.py:L206`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_ai.py#L206).

---

### 3. Antarmuka Debug Overlay
- [x] **1. Pertimbangan Aksi & Skor NPC**:
  - Panel debug menampilkan tabel *real-time* berisi daftar aksi legal yang dipertimbangkan NPC beserta skor heuristiknya.
  - Aksi yang dipilih ditandai dengan ikon `▶`.
- [x] **2. Metric Node Counts & Waktu Komputasi**:
  - Menampilkan total node yang dikunjungi (`node_count`).
  - Menampilkan jumlah cabang yang di-prune (`pruned_count`).
  - Menampilkan waktu eksekusi dalam milidetik (`time_ms`).
- [x] **3. Kontrol Interaktif Real-Time**:
  - Selector Algoritma: *Alpha-Beta Pruning*, *Pure Minimax*, *Expectimax*.
  - Selector Fungsi Evaluasi: *Balanced*, *Aggressive*, *Defensive*.
  - Selector Depth Limit: Depth 1 s/d 8.
  - Toggle Move Ordering: Menyalakan/mematikan urutan aksi.
- [x] **Lokasi Kode**: [`game/overlay.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/overlay.py).

---

### 4. Hasil Eksperimen & Analisis (Termasuk di Laporan)

#### 🔹 Eksperimen 1: Pure Minimax vs Alpha-Beta Pruning
| Depth | Node Minimax | Node Alpha-Beta | Pemangkasan Cabang (%) | Waktu Minimax (ms) | Waktu Alpha-Beta (ms) | Keputusan Identik? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 4 | 4 | 0.0 % | 0.07 ms | 0.04 ms | **True** |
| 2 | 20 | 20 | 0.0 % | 0.07 ms | 0.09 ms | **True** |
| 3 | 82 | 51 | 37.8 % | 0.20 ms | 0.09 ms | **True** |
| 4 | 327 | 142 | 56.6 % | 0.38 ms | 0.21 ms | **True** |
| 5 | 1,277 | 302 | 76.4 % | 1.52 ms | 0.51 ms | **True** |
| 6 | 4,983 | 712 | **85.7 %** | 6.23 ms | 1.03 ms | **True** |

> **Kesimpulan**: Alpha-Beta Pruning menghemat hingga **85.7% node** pada Depth 6 dengan waktu **6x lebih cepat** tanpa mengubah kualitas keputusan (*optimal*).

#### 🔹 Eksperimen 2: Dampak Move Ordering (Urutan Aksi)
| Depth | Tanpa Move Ordering (Nodes) | Dengan Move Ordering (Nodes) | Reduksi Tambahan (%) |
|:---:|:---:|:---:|:---:|
| 3 | 66 | 51 | 22.7 % |
| 4 | 211 | 142 | 32.7 % |
| 5 | 592 | 302 | 49.0 % |
| 6 | 1,611 | 712 | **55.8 %** |

> **Kesimpulan**: Menempatkan aksi-aksi potensial (seperti `HEAVY_ATTACK` / `ATTACK`) di awal urutan pencarian membuat batas $\alpha$ dan $\beta$ memotong cabang jauh lebih cepat, mengurangi node yang diperiksa hingga **55.8%** tambahan.

#### 🔹 Eksperimen 3: Tingkah Laku NPC Berdasarkan Fungsi Evaluasi
1. **Kondisi Netral (HP 100 vs 100)**:
   - *Balanced*: Memilih `HEAVY_ATTACK` (Skor: 0.0).
   - *Aggressive*: Memilih `HEAVY_ATTACK` (Skor: 48.0).
   - *Defensive*: Memilih `DEFEND` (Skor: 145.0).
2. **Kondisi Tertekan (HP Player 75 vs HP NPC 25)**:
   - Ketiga fungsi evaluasi sepakat memilih `POTION` untuk mencegah kekalahan lethal di giliran berikutnya.
3. **Kondisi Menang (HP Player 20 vs HP NPC 70)**:
   - Ketiga fungsi evaluasi sepakat memilih `HEAVY_ATTACK` untuk mengeksekusi kemenangan secara instan.

#### 🔹 Eksperimen 4: Expectimax (Aksi Probabilistik / Stokastik)
- Menguji pencarian pada aksi `HEAVY_ATTACK` berprobabilitas ($75\%$ hit, $25\%$ miss).
- Skor `HEAVY_ATTACK` terkoreksi secara matematis dari $+22.0$ (deterministik) menjadi $+3.94$ (ekspektasi nilai), namun tetap menjadi aksi optimal untuk diambil NPC.

---

### 5. Fitur Tambahan Mandiri & Asumsi Permainan
1. **Sistem Cooldown Heavy Attack**:
   - Mencegah spam serangan terkuat secara tak terbatas (`HEAVY_COOLDOWN_TURNS = 2`).
2. **Floating Action Text (UI)**:
   - Menampilkan teks melayang di atas avatar petarung saat melancarkan aksi (`Menyerang! (-18 HP)`, `Minum Potion! (+25 HP)`).
3. **Batas Cadangan Potion**:
   - Setiap petarung dibatasi maksimal membawa 3 potion (`MAX_POTIONS = 3`).
4. **Modul Eksperimen Otomatis**:
   - File [`scratch/run_experiments.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/run_experiments.py) untuk mengeksekusi pengujian otomatis dan menghasilkan data statistik eksperimen.

---

## 🚀 PANDUAN CARA MENJALANKAN & VERIFIKASI

### 1. Menjalankan Game Utama
Untuk mencoba duel langsung secara visual dengan debug overlay:
```bash
python main.py
```
*Gunakan tombol keyboard panah/WASD untuk mendekati NPC Kucing Hitam, lalu lakukan pertarungan turn-based.*

### 2. Menguji Debug Overlay di Game
- Tekan **F3** untuk membuka debug overlay jika belum muncul.
- Ubah dropdown **Algorithm** (*Alpha-Beta*, *Minimax*, *Expectimax*).
- Ubah dropdown **Eval Mode** (*Balanced*, *Aggressive*, *Defensive*).
- Geser slider / tombol **Depth** (1 - 8) dan amati perubahan `Node Count` dan `Time (ms)`.

### 3. Menjalankan Script Eksperimen Otomatis
Untuk mendapatkan data benchmark secara instan:
```bash
python scratch/run_experiments.py
```

---

## 🎯 KESIMPULAN AUDIT

> **STATUS KHIR: ✅ 100% TERPENUHI & SIAP DILAPORKAN**  
> Seluruh persyaratan Tugas Besar Tahap 2 (Adversarial Search, Minimax, Alpha-Beta Pruning, Move Ordering, Evaluation Functions, Expectimax, Debug Overlay, dan Dokumen Laporan) telah terimplementasi dengan sempurna dalam codebase dan terdokumentasi pada [`LAPORAN_TAHAP_2.md`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/LAPORAN_TAHAP_2.md).
