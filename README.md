# Bakekok - Dokumentasi Sistem Game Tahap 3

> **Tugas Besar Mata Kuliah Kecerdasan Buatan**  
> Program Studi Ilmu Komputer — Universitas Pendidikan Indonesia  
> **Kelompok 7**

---

## 1. Identitas Anggota Kelompok 7
1. **Muhammad Hanif Muyassar**
2. **Moch Fadillah Pratama**
3. **Muhammad Zidan Mirza Fedrieka**
---

## 2. Panduan Menjalankan Game

### 1. Prasyarat Sistem
* **Python**: Versi `3.10` atau lebih baru (direkomendasikan `3.11` / `3.12` / `3.14`).
* **Sistem Operasi**: Windows, macOS, atau Linux.

### 2. Instalasi Dependensi
Buka terminal/PowerShell pada folder proyek `Game-AI`, lalu jalankan:

```bash
pip install -r requirements.txt
```
*(Dependensi utama hanyalah `pygame-ce >= 2.5.0`)*

### 3. Menjalankan Permainan
```bash
python main.py
```

---

## 3. Skenario Panduan Fitur AI 

```mermaid
flowchart LR
    A["1. Eksplorasi & Pathfinding<br/>(UCS / A*)"] --> B["2. Buka Peti Item<br/>(Gacha Roulette)"]
    B --> C["3. Dekati NPC / Tekan B<br/>(Masuk Pre-Battle)"]
    C --> D["4. Tekan I: Inspeksi AI<br/>(Pohon CSP & Local Search)"]
    D --> E["5. Tekan Spasi: Masuk Battle<br/>(Tag-Team & Alpha-Beta)"]
```

### Langkah 1: Eksplorasi Peta & Pathfinding (Materi Tahap 1)
* Gerakkan karakter utama (**Bolu**) menggunakan tombol **`W, A, S, D`** atau **Tombol Panah**.
* Tekan tombol **`[Spasi]`** untuk memanggil NPC.
* Tekan tombol **`[Ctrl]`** untuk menampilkan **Debug Overlay Pathfinding**:
  * Anda akan melihat visualisasi petak yang di-expand (*closed set*), jalur terpendek (*path*), metrik waktu eksekusi (ms), serta perbandingan algoritma **Uniform Cost Search (UCS)** vs **A\*** dengan berbagai heuristik (*Manhattan*, *Euclidean*, *Chebyshev*).

### Langkah 2: Interaksi Item & Mini-Game Gacha
* Dekati salah satu peti harta karun di peta (berjarak <= 1 langkah ubin), lalu tekan **`[E]`**.
* Akan muncul roda *roulette* gacha item yang memberikan buff serangan (**ATK**), pertahanan (**DEF**), atau ramuan (**Potion**) kepada Bolu. Buff ini nantinya akan memicu sistem **Dynamic Difficulty Adjustment (DDA)** saat skuad musuh dibentuk!

### Langkah 3: Masuk ke Fase Pre-Battle (Materi Tahap 3)
* Tabrak / dekati NPC musuh atau tekan tombol **`[B]`** dari mana saja untuk langsung memicu fase **Pre-Battle**.
* Di fase ini, sistem AI di balik layar secara otomatis menjalankan:
  1. **CSP Solver (Backtracking + MRV + LCV + AC-3)** untuk memastikan komposisi tim musuh mematuhi 8 batasan legalitas (C1 - C8).
  2. **Local Search Optimizer** untuk menyesuaikan tingkat kesulitan skuad musuh agar seimbang dengan status Bolu (Target Difficulty sekitar 0.55).
* Anda dapat mencoba mengganti algoritma optimasi secara instan dengan menekan tombol angka **`[1]` s/d `[5]`**:
  * `[1]`: *Hill Climbing (Steepest-Ascent)*
  * `[2]`: *Hill Climbing with Sideways Move* (mengatasi Plateau)
  * `[3]`: *Random Restart Hill Climbing* (mengatasi Local Maximum)
  * `[4]`: *Simulated Annealing* (probabilitas langkah downhill exp(delta / T))
  * `[5]`: *Genetic Algorithm* (crossover skuad & mutasi)
* Tekan **`[R]`** untuk me-*reroll* skuad dengan seed acak baru.

### Langkah 4: Buka Inspeksi Visualizer AI Pre-Battle (Pohon CSP & Grafik)
* Pada layar Pre-Battle, klik tombol **`[INSPEKSI AI]`** atau tekan tombol **`[I]`**.
* Jendela visualizer interaktif akan terbuka dengan dua tab utama:
  * **Tab 1: Pohon CSP & Pruning**:
    * Menampilkan pohon pencarian Backtracking CSP secara 2D.
    * Gunakan tombol kontrol bawah (**Play, Step Next, Step Back, Reset, Speed**) atau geser *scrubber slider* untuk melihat jalannya pembentukan skuad langkah demi langkah.
    * Klik simpul mana saja pada pohon untuk melihat detail di kolom samping kanan: **Mengapa anakan ini dipilih (MRV & LCV)** dan **Mengapa anakan lain dipangkas/di-prune (Forward Checking)**.
    * Klik tombol **`[?] Aturan C1-C8`** di samping tab atas untuk melihat modal ringkasan seluruh aturan konsistensi.
    * Kanvas pohon dapat di-*pan* (klik-tahan & geser mouse) dan di-*zoom* (**`+` / `-` / Reset**).
  * **Tab 2: Optimasi Local Search**:
    * Menampilkan grafik konvergensi 2D hubungan antara iterasi vs Difficulty / Fitness.
    * Panel kanan menampilkan evaluasi detail setiap transisi langkah (*Move*, *Sideways*, *Restart*, *Cooling*, dll).

### Langkah 5: Masuk ke Arena Duel Tag-Team (Materi Tahap 2)
* Tekan **`[Spasi]`** atau **`[Enter]`** untuk masuk ke arena pertarungan turn-based.
* Pilih aksi bertarung Anda:
  * `[1 / A]`: Serangan biasa (*Attack*).
  * `[2 / S]`: Serangan kuat (*Heavy Attack*).
  * `[3 / D]`: Bertahan dengan perisai (*Defend*, reduksi damage 65%).
  * `[4 / W]`: Minum ramuan (*Potion*).
* Giliran musuh dikendalikan oleh **Adversarial Search (Minimax / Alpha-Beta Pruning / Expectimax)**.
* Tekan tombol **`[T]`** saat giliran NPC untuk membuka **Decision Tree Modal Overlay**, yang memperlihatkan cabang evaluasi nilai utilitas *minimax* dan pemangkasan cabang *alpha-beta*.
* Jika frontline musuh gugur, anggota cadangan (*bench*) akan maju secara otomatis via sistem **Tag-Team Battle**.

---

## 4. Ringkasan Kontrol Permainan (Keybindings Cheat-Sheet)

| Mode Permainan | Tombol Keyboard | Aksi / Fungsi |
|:---|:---|:---|
| **Eksplorasi (Peta)** | `W, A, S, D` / `Panah` | Menggerakkan Player (Bolu) pada grid ubin |
| | `E` | Membuka peti harta karun terdekat (Gacha Item) |
| | `Spasi` | Memanggil NPC Oyen melacak Bolu via pathfinding |
| | `Ctrl` | Membuka/menutup Debug Overlay Pathfinding |
| | `B` | Masuk ke fase Pre-Battle |
| | `Esc` | Keluar dari aplikasi |
| **Fase Pre-Battle** | `1, 2, 3, 4, 5` | Mengganti algoritma Local Search |
| | `R` | Re-roll / optimasi ulang skuad musuh |
| | `I` / Klik Tombol | **Membuka Inspeksi Visualizer AI Pre-Battle** |
| | `Spasi` / `Enter` | Memulai duel turn-based |
| | `Tab` / `Esc` | Kembali ke mode eksplorasi peta |
| **Visualizer Pre-Battle** | Klik Tab Atas | Beralih antara **Tab 1 (CSP Tree)** & **Tab 2 (Local Search)** |
| | Klik `[?] Aturan C1-C8` | Menampilkan popup dialog ringkasan 8 aturan konsistensi |
| | Drag Mouse / Tombol Zoom | Menggeser (*pan*) dan memperbesar/memperkecil kanvas pohon |
| | Play / Step / Scrubber | Mengendalikan simulasi langkah algoritma |
| | Scroll Mouse di Panel | Menggulir teks penjelasan teori & analisis simpul |
| | `X` / `Esc` | Menutup jendela visualizer |
| **Arena Pertarungan** | `1` / `A` | Serangan Biasa (*Attack*) |
| | `2` / `S` | Serangan Kuat (*Heavy Attack*) |
| | `3` / `D` | Bertahan (*Defend*) |
| | `4` / `W` | Menggunakan Potion |
| | `T` | **Membuka Fullscreen Decision Tree Modal AI Battle** |
| | `R` | Reset duel dari awal |
| | `Tab` | Menyerah dan kembali ke peta |

---

## 5. Arsitektur Sistem & Struktur Direktori

Kode program dibangun secara modular menggunakan Python 3.10+ berbasis pustaka `pygame-ce`:

```
Game-AI/
├── main.py                     # Entry point utama aplikasi
├── requirements.txt            # Dependensi pustaka (pygame-ce)
├── README.md                   # Dokumentasi teknis & panduan permainan
├── assets/                     # Spritesheet karakter, potret NPC, dan atlas ubin
├── data/
│   └── map_tubes.json          # Peta ubin 2D, koordinat, layer medan, dan collision
├── game/
│   ├── __init__.py             # Inisialisasi package
│   ├── app.py                  # Loop utama, event loop, kamera, state machine (Explore/Pre-Battle/Battle)
│   ├── config.py               # Konstanta global, palet warna antislop, domain stat, budget CSP
│   ├── events.py               # Event dispatcher & sinyal komunikasi antar-modul
│   ├── mapdata.py              # Parser ubin peta, terrain cost (jalan tanah vs rumput), koordinat grid
│   ├── player.py               # Karakter pemain (Bolu), inventaris item, status HP/potion
│   ├── npc.py                  # Karakter NPC di peta, waypoint patroli, palette swap tint
│   ├── npc_squad.py            # Model skuad musuh (frontline aktif, bench cadangan, rotasi tag-team)
│   ├── search.py               # Modul Tahap 1: PathNode, UCS, A*, heuristik (Manhattan, Euclidean, Chebyshev)
│   ├── battle_ai.py            # Modul Tahap 2: Minimax, Alpha-Beta Pruning, Expectimax, BattleState
│   ├── battle_system.py        # Logika duel turn-based, giliran, kalkulasi damage, logging aksi
│   ├── battle_vfx.py           # Efek visual animasi prosedural (pedang berayun, perisai, hit shake)
│   ├── difficulty.py           # Rumus evaluasi tingkat kesulitan dan fungsi fitness DDA
│   ├── npc_config_csp.py       # Modul Tahap 4: CSP Solver, Backtracking, MRV, LCV, AC-3, Constraint C1-C8
│   ├── npc_config_optimizer.py # Modul Tahap 3: Local Search Engine (5 algoritma optimasi difficulty)
│   ├── pre_battle_visualizer.py# Visualizer Akademis Interaktif Pre-Battle (Pohon CSP & Grafik Konvergensi)
│   ├── tree_overlay.py         # Visualizer Decision Tree Minimax/Alpha-Beta Battle
│   └── overlay.py              # In-game HUD & Debug Overlay Pathfinding / Battle
└── scratch/
    ├── benchmark_csp_mrv_lcv.py  # Skrip benchmark komparatif CSP (30 run dengan & tanpa MRV/LCV)
    ├── run_tahap3_experiments.py # Skrip benchmark otomatis CSP Solver & 5 Algoritma Local Search
    ├── run_experiments.py        # Skrip benchmark otomatis Minimax, Alpha-Beta, & Expectimax
    ├── test_app_integration.py   # Headless end-to-end integration test
    ├── test_csp.py               # Unit test kepatuhan constraint CSP Solver
    └── test_optimizer.py         # Unit test 5 algoritma Local Search
```

---

## 6. Landasan Teori & Pemetaan Materi Kuliah

Sistem AI di dalam game ini mengimplementasikan 4 pilar materi perkuliahan secara terintegrasi:

### 1. Tahap 1: Informed Search & Navigasi Grid
* **Uniform Cost Search (UCS)**: Menemukan jalur terpendek berdasarkan akumulasi biaya riil `g(n)` dengan `h(n) = 0`.
* **A* Search**: Mengarahkan pencarian menggunakan fungsi evaluasi:
  ```
  f(n) = g(n) + h(n)
  ```
* **Fungsi Heuristik Terverifikasi**:
  * *Manhattan Distance* (Grid 4-connected, terbukti *admissible* & *consistent*):
    ```
    h(n) = |x_n - x_goal| + |y_n - y_goal|
    ```
  * *Euclidean Distance* (Garis lurus, *admissible*):
    ```
    h(n) = sqrt((x_n - x_goal)^2 + (y_n - y_goal)^2)
    ```
  * *Chebyshev Distance*:
    ```
    h(n) = max(|x_n - x_goal|, |y_n - y_goal|)
    ```
* **Weighted Terrain Cost**: Langkah di jalan tanah/jembatan memiliki biaya `c = 1.0`, sedangkan medan berumput berbiaya `c = 2.0`.

### 2. Tahap 2: Adversarial Search Turn-Based Battle
* **Minimax**: Mengevaluasi seluruh kemungkinan langkah pemain dan musuh untuk memaksimalkan utilitas giliran.
* **Alpha-Beta Pruning**: Memangkas cabang-cabang pohon permainan yang terbukti tidak akan dipilih oleh pemain rasional, menurunkan kompleksitas dari `O(b^d)` menjadi mendekati `O(b^(d/2))`.
* **Expectimax**: Memodelkan ketidakpastian aksi jika pemain dianggap tidak selalu bermain optimal (*bounded rationality*).
* **Tag-Team Battle**: Jika frontline NPC tumbang, sistem mengaktifkan anggota berikutnya dari *bench*, menjaga kesinambungan duel.

### 3. Tahap 3.1: Local Search
Local search mencari konfigurasi akhir optimal di mana lintasan (*path*) tidak penting dengan konsumsi memori konstan `O(1)`.
* **Fungsi Objektif (Fitness Function)**:
  ```
  Fitness(s) = -|Difficulty(s) - TargetDifficulty|
  ```
* **5 Algoritma yang Disediakan**:
  1. **Hill Climbing (Steepest-Ascent)**: Memilih tetangga dengan kenaikan fitness terbesar.
  2. **Hill Climbing with Sideways Move**: Mengizinkan transisi antar-tetangga bernilai sama hingga 15 langkah untuk melintasi area datar (*plateau* & *shoulder*).
  3. **Random Restart Hill Climbing**: Menjalankan ulang pendakian bukit dari *seed* awal legal CSP yang berbeda untuk meloloskan diri dari *local optimum*.
  4. **Simulated Annealing (SA)**: Mengadopsi prinsip termodinamika metalurgi; gerakan yang memperburuk fitness tetap dapat diterima dengan probabilitas Boltzmann:
     ```
     P(accept) = exp(delta_E / T), dengan pendinginan T = T * cooling_rate
     ```
  5. **Genetic Algorithm (GA)**: Mengoperasikan populasi konfigurasi skuad melalui seleksi turnamen, rekombinasi (*crossover*), dan mutasi acak.

### 4. Tahap 3.2: Constraint Satisfaction Problem (CSP)
CSP merumuskan pembentukan skuad sebagai masalah kepatuhan batasan formal:
* **Himpunan Variabel (X)**: $6 \times N$ atribut untuk $N$ anggota skuad ($N \in \{1, 2, 3\}$):
  * `char_type_i`: Kelas karakter NPC ke-$i$.
  * `hp_i`: Poin darah maksimal.
  * `potions_i`: Jumlah ramuan pemulihan.
  * `atk_bonus_i`: Bonus serangan flat.
  * `def_bonus_i`: Bonus pertahanan flat (reduksi damage).
  * `eval_profile_i`: Karakteristik fungsi evaluasi AI minimax.
* **Himpunan Domain Diskret (D)**:
  * `char_type` $\in$ `{"warrior", "ranger", "mage", "assassin"}`
  * `hp` $\in$ `{60, 70, 80, 90, 100, 110, 120}`
  * `potions` $\in$ `{0, 1, 2, 3}`
  * `atk_bonus` $\in$ `{0, 5, 10, 15}`
  * `def_bonus` $\in$ `{0, 2, 4, 6}`
  * `eval_profile` $\in$ `{"BALANCED", "AGGRESSIVE", "DEFENSIVE"}`
* **8 Batasan Konsistensi (C1 - C8)**:
  * **C1 (Budget HP)**: Total HP seluruh anggota skuad $\le 250$.
  * **C2 (Budget Potion)**: Total Potion seluruh anggota skuad $\le 5$.
  * **C3 (Syarat Tank)**: Jika `char_type = "tank"`, maka $HP \ge 90$.
  * **C4 (Syarat Ranger)**: Jika `char_type = "ranger"`, maka $ATK \ge 5$.
  * **C5 (Keunikan Role)**: Tidak boleh ada role kembar jika jumlah anggota skuad $\ge 2$.
  * **C6 (Mage Glass Cannon)**: Jika `char_type = "mage"`, maka $HP \le 90$ dan profil AI $\in$ `{"BALANCED", "AGGRESSIVE"}`.
  * **C7 (Tank Sinergi)**: Jika `char_type = "tank"`, maka profil AI $\in$ `{"BALANCED", "DEFENSIVE"}`.
  * **C8 (Assassin Burst & Budget ATK)**: Total akumulasi $ATK \le 25$; jika `char_type = "assassin"`, maka $ATK \ge 10$, $HP \le 90$, dan profil AI $\in$ `{"BALANCED", "AGGRESSIVE"}`.
* **Mekanisme Penyelesaian**:
  * **AC-3 Filtering**: Menyaring domain *unary* sebelum pencarian dimulai.
  * **MRV (Minimum Remaining Values)**: Memilih variabel paling kritis (*fail-first*) yang memiliki sisa domain tersedikit.
  * **LCV (Least Constraining Value)**: Memprioritaskan nilai yang paling ramah dan tidak mematikan domain variabel lain (*succeed-first*).
  * **Forward Checking**: Langsung memangkas cabang simpul jika terdeteksi melanggar batasan konsistensi.

---

## 7. Hasil Eksperimen & Analisis Benchmark

Seluruh eksperimen dapat direproduksi secara instan menggunakan skrip di folder `scratch/`.

### 1. Kinerja CSP Solver (`scratch/run_tahap3_experiments.py`)

| Metrik Evaluasi CSP | Hasil Pengukuran | Keterangan |
|:---|:---:|:---|
| **Waktu AC-3 Preprocessing** | **0.005 ms** | Pemangkasan apriori berlangsung sub-milidetik |
| **Waktu Solve 2 Anggota NPC** | **0.175 ms** | Backtracking + MRV + LCV |
| **Waktu Solve 3 Anggota NPC** | **0.299 ms** | Menemukan solusi lengkap instan |
| **Tingkat Kepatuhan Aturan C1 - C8** | **100% (0 Pelanggaran)** | Seluruh solusi terbukti konsisten |
| **Komposisi Default 3 NPC** | Warrior + Ranger + Mage | Komposisi kelas sinergis dan seimbang |

### 2. Perbandingan 5 Algoritma Local Search (Target Difficulty = 0.55)

| Algoritma Local Search | Waktu Eksekusi (ms) | Rata-rata Iterasi | Nilai Fitness | Difficulty Dicapai | Kepatuhan Legalitas CSP |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Hill Climbing (HC)** | 3.93 ms | 5.0 | -0.0028 | 0.5528 | **100% Valid** |
| **HC with Sideways Move** | **2.84 ms** | 5.0 | -0.0028 | 0.5528 | **100% Valid** |
| **Random Restart HC** | 11.98 ms | 5.6 | **-0.0016** | **0.5516** | **100% Valid** |
| **Simulated Annealing (SA)** | 29.97 ms | 136.0 | -0.0072 | 0.5572 | **100% Valid** |
| **Genetic Algorithm (GA)** | 65.30 ms | 30.0 gen | -0.0025 | 0.5480 | **100% Valid** |

> **Temuan Kunci:**
> * **HC with Sideways Move** adalah algoritma tercepat (**2.84 ms**), sangat ideal untuk transisi *gameplay* waktu nyata tanpa jeda.
> * **Random Restart HC** menghasilkan solusi paling presisi mendekati target ($0.5516$, deviasi hanya $0.0016$).
> * Integrasi CSP sebagai validator menghasilkan tingkat kepatuhan **100% legal** pada seluruh algoritma.

### 3. Adaptabilitas Dinamis Skuad terhadap Kondisi Pemain (DDA)

Sistem secara otomatis menyesuaikan *target difficulty* berdasarkan inventaris item, status HP pemain, dan buff gacha peti harta karun:

| Skenario Pengujian | Kondisi Pemain (Bolu) | Target Difficulty | Difficulty Tercapai | Deviasi | Komposisi Skuad Musuh yang Dihasilkan |
|:---|:---|:---:|:---:|:---:|:---|
| **Skenario A (Standar)** | HP 100, Potion 2, ATK +0, DEF +0 | 0.5500 | 0.5472 | 0.0028 | Assassin (BAL) + Ranger (BAL) + Mage (BAL) |
| **Skenario B (Terluka)** | HP 35, Potion 0, ATK +0, DEF +0 | 0.4000 | 0.3972 | 0.0028 | Warrior (BAL) + Ranger (BAL) + Mage (BAL) |
| **Skenario C (Buff Peti)**| HP 100, Potion 4, ATK +6, DEF +4 | 0.6500 | 0.6500 | **0.0000** | Ranger (BAL) + Mage (AGG) + Assassin (BAL) |

---

## 8. Skrip Pengujian Otomatis & Benchmark

Anda dapat menjalankan skrip pengujian mandiri tanpa membuka jendela grafis game:

1. **Benchmark Lengkap Tahap 3 (CSP + 5 Local Search + DDA)**:
   ```bash
   python scratch/run_tahap3_experiments.py
   ```
2. **Benchmark Komparasi Heuristik CSP (30 Run dengan & tanpa MRV/LCV)**:
   ```bash
   python scratch/benchmark_csp_mrv_lcv.py
   ```
3. **Benchmark AI Battle Tahap 2 (Minimax vs Alpha-Beta vs Expectimax)**:
   ```bash
   python scratch/run_experiments.py
   ```
4. **Pengujian Integrasi End-to-End Game Loop (Headless)**:
   ```bash
   python scratch/test_app_integration.py
   ```
5. **Unit Test Aturan CSP & Validator**:
   ```bash
   python scratch/test_csp.py
   ```
6. **Unit Test Local Search Optimizer**:
   ```bash
   python scratch/test_optimizer.py
   ```

---