# LAPORAN TAHAP-2: DUEL TURN-BASED AI MENGGUNAKAN MINIMAX, ALPHA-BETA PRUNING, DAN EXPECTIMAX PADA GAME "BAKEKOK"

**Mata Kuliah:** Kecerdasan Buatan  
**Kelompok 7:**
- Hanif Muyassar
- Moch Fadillah Pratama
- Muhammad Zidan Mirza Fedrieka  

**Program Studi:** Ilmu Komputer — Universitas Pendidikan Indonesia

---

## 0. Gambaran Umum Proyek

### 0.1 Deskripsi Game
Game **Bakekok** adalah permainan 2D berbasis grid (top-down) di mana pemain mengendalikan karakter **Bolu** yang harus menghindari atau mengalahkan musuh **Kucing Hitam** (NPC). Game ini merupakan *port* dari proyek berbasis Godot Engine ke Python menggunakan library `pygame-ce`.

Game memiliki dua mode utama:
1. **Mode Eksplorasi (Map Grid):** Player bergerak bebas di peta 2D, NPC melakukan *pathfinding* secara real-time menggunakan UCS atau A* untuk mengejar Player.
2. **Mode Duel (Battle Turn-Based):** Dipicu otomatis ketika NPC berhasil mendekati Player (jarak Manhattan $\le 1$). Pertarungan gilir-giliran menggunakan AI berbasis Minimax/Alpha-Beta/Expectimax.

### 0.2 Teknologi yang Digunakan
- **Bahasa:** Python 3.10+
- **Library:** `pygame-ce` (Community Edition)
- **Algoritma Tahap 1:** Uniform Cost Search (UCS), A\* Search (Manhattan, Euclidean, Chebyshev)
- **Algoritma Tahap 2:** Pure Minimax, Alpha-Beta Pruning, Expectimax

### 0.3 Struktur Kode

```
Game-AI/
├── main.py                    # Entry point aplikasi
├── requirements.txt           # Dependensi: pygame-ce
├── data/
│   └── map_tubes.json         # Data peta: ground, decorations, obstacles, water
├── game/
│   ├── app.py                 # Main loop, input handler, kamera, state manager
│   ├── battle_ai.py           # Engine AI: BattleState, BattleAISolver
│   ├── battle_system.py       # Manajer duel: eksekusi aksi, log pertarungan
│   ├── config.py              # Konstanta visual, warna, skala, path aset
│   ├── mapdata.py             # Parser JSON peta, sistem koordinat, step cost
│   ├── npc.py                 # Entitas NPC: pathfinding real-time, pemicu duel
│   ├── overlay.py             # Render debug overlay
│   ├── player.py              # Entitas Player (Bolu)
│   └── search.py              # Engine pencarian: UCS, A*, PathNode, GridManager
└── scratch/
    └── run_experiments.py     # Skrip benchmark otomatis AI
```

### 0.4 Alur Sistem (System Flow)
1. `main.py` → `App.__init__()` → Load `MapData` (parse JSON peta) → Spawn Player & NPC
2. `App.run()` (game loop 60 FPS) → Handle input → `NPC.update()` → Jalankan UCS/A\* → Render
3. Jika jarak Player-NPC $\le 1$ → Trigger `BattleSystem` → Switch ke Mode Duel
4. Mode Duel: giliran Player (input keyboard) / giliran NPC (`BattleAISolver.select_best_action()`)
5. Debug overlay dirender setiap frame di panel kiri layar

---

## A. TAHAP 1 — Pathfinding & Algoritma Pencarian Jalur

### A.1 Representasi Peta Grid
Peta permainan direpresentasikan sebagai grid 2D $N \times M$ dengan ukuran sel $16 \times 16$ piksel. Data peta dibaca dari `data/map_tubes.json` yang memiliki empat layer:

| Layer | Isi | Keterangan |
|:------|:----|:-----------|
| `ground` | Ubin tanah/rumput dasar | Basis sel yang bisa diinjak |
| `decorations` | Jalan tanah, jembatan kayu | Dirender di atas `ground`; mempengaruhi step cost |
| `obstacles` | Bangunan, tembok, pohon | Menghalangi pergerakan (non-walkable) |
| `water` | Air | Non-walkable |

**Definisi sel walkable:** `ground` $-$ `obstacles` $-$ `water`

### A.2 Sistem Bobot Medan (Weighted Terrain Cost)
Setiap sel walkable memiliki biaya langkah $c(n)$ berdasarkan tipe medannya:

$$c(n) = \begin{cases} 
1.0, & \text{Jalan Tanah (Dirt Road) / Jembatan Kayu} \\
2.0, & \text{Rumput / Medan Umum (Grass)} \\
\infty, & \text{Rintangan / Non-walkable}
\end{cases}$$

**Implementasi di `mapdata.py`** — Fungsi `_is_dirt_road_cell(cell_info)` mengidentifikasi jalan tanah berdasarkan nama sumber aset dan koordinat atlas tile:
- Tile dari atlas `"Wood Bridge"` → Jalan Tanah (cost **1.0**)
- Tile dari atlas `"Ext_10a_DEMO"` dengan koordinat `(11, 12)` atau baris atlas `2 ≤ ay ≤ 4` → Jalan Tanah (cost **1.0**)
- Semua tile lainnya → Rumput/Medan (cost **2.0**)

```python
# game/mapdata.py — get_step_cost()
def get_step_cost(self, pos):
    pos = tuple(pos)
    if pos in self.decorations and _is_dirt_road_cell(self.decorations[pos]):
        return 1.0   # Jalan Tanah di layer decorations
    if pos in self.ground and _is_dirt_road_cell(self.ground[pos]):
        return 1.0   # Jalan Tanah di layer ground
    return 2.0       # Default: Rumput/Medan
```

### A.3 Fungsi Heuristik $h(n)$ untuk A\*
Memperkirakan jarak dari posisi saat ini $a = (x_a, y_a)$ ke target $b = (x_b, y_b)$:

| Heuristik | Formula | Properti |
|:----------|:--------|:---------|
| **Manhattan** | $h = |x_a-x_b| + |y_a-y_b|$ | Admissible untuk gerakan 4-arah |
| **Euclidean** | $h = \sqrt{(x_a-x_b)^2 + (y_a-y_b)^2}$ | Admissible; lebih longgar |
| **Chebyshev** | $h = \max(|x_a-x_b|, |y_a-y_b|)$ | Admissible untuk gerakan 8-arah |

### A.4 Algoritma Pencarian Jalur

#### A.4.1 Uniform Cost Search (UCS)
Algoritma pencarian tak terinformasi (*uninformed search*) yang mengekspansi node berdasarkan akumulasi biaya $g(n)$ terkecil. Tidak ada heuristik: $h(n) = 0$.

$$f(n) = g(n), \quad g(n) = g(\text{parent}(n)) + c(n)$$

**Properti:** Complete ✓, Optimal ✓ (cost $\ge 0$), Time $O(b^{1+\lfloor C^*/\varepsilon \rfloor})$

#### A.4.2 A\* Search
Algoritma pencarian terinformasi (*informed search*) yang menggabungkan biaya riwayat $g(n)$ dengan estimasi heuristik $h(n)$:

$$f(n) = g(n) + h(n)$$

*Tie-breaking*: Jika dua node memiliki $f(n)$ identik, node dengan $h(n)$ lebih kecil diprioritaskan.

Implementasi: `open_list.sort(key=lambda n: (n.f, n.h))`

**Properti:** Complete ✓, Optimal ✓ (h admissible), Time $O(b^d)$ terburuk — jauh lebih cepat praktiknya.

### A.5 Mengapa Semua Algoritma Menghasilkan Jalur yang Sama?
Pada pengujian, UCS dan semua varian A\* menghasilkan jalur **identik** dengan total cost yang **sama**. Ini benar dan normal karena:
- Semua algoritma **optimal** — dijamin menemukan jalur berbiaya minimum.
- Pada peta dengan weighted terrain yang sama, terdapat **satu jalur optimal tunggal** yang akan ditemukan oleh semua algoritma optimal.
- Perbedaan nyata ada pada **jumlah node yang diekspansi** — A\* lebih efisien karena heuristik mengarahkan pencarian menuju target, sedangkan UCS mengekspansi ke semua arah secara merata.

---

## 1. TAHAP 2 — Formulasi Masalah AI Adversarial (Duel Turn-Based)

### 1.1 Pemicu Transisi ke Mode Duel
Pertarungan dipicu otomatis oleh `npc.py` ketika jarak Manhattan antara Player dan NPC $\le 1$:
$$d_{\text{Manhattan}}(\text{Player}, \text{NPC}) = |x_p - x_n| + |y_p - y_n| \le 1$$

Pencarian keputusan NPC dimodelkan menggunakan kerangka kerja **Adversarial Search (Game Theory)** dengan formulasi formal berikut:

### 1.2 Representasi State ($S$) & State Vector
State duel diimplementasikan dalam class `BattleState` di `battle_ai.py`:
$$s = \langle HP_{\text{player}}, HP_{\text{npc}}, Pot_{\text{player}}, Pot_{\text{npc}}, Def_{\text{player}}, Def_{\text{npc}}, Turn, CD_{\text{player}}, CD_{\text{npc}} \rangle$$

- $HP_{\text{player}}, HP_{\text{npc}} \in [0, 100]$: Status kesehatan masing-masing petarung.
- $Pot_{\text{player}}, Pot_{\text{npc}} \in [0, 3]$: Jumlah cadangan potion pemulih (+25 HP, stok awal 2).
- $Def_{\text{player}}, Def_{\text{npc}} \in \{\text{True}, \text{False}\}$: Status bertahan (mengurangi damage yang masuk berikutnya sebesar 65%).
- $Turn \in \{\text{MAX (NPC)}, \text{MIN (Player)}\}$: Petarung yang memegang hak giliran.
- $CD_{\text{player}}, CD_{\text{npc}} \in [0, 2]$: Sisa giliran *cooldown* serangan `HEAVY_ATTACK` (bernilai 0 jika siap digunakan, dan tereset ke 2 setelah digunakan).

### 1.3 Ruang Aksi ($A(s)$) & Branching Factor $b \le 4$
Setiap giliran, pemain aktif dapat memilih maksimal 4 aksi legal:

| Aksi | Kode | Damage / Efek | Syarat Legal |
|:-----|:-----|:-------------|:-------------|
| Serangan Biasa | `ATTACK` | 18 HP (6 HP jika musuh DEFEND) | Selalu tersedia |
| Serangan Kuat | `HEAVY_ATTACK` | 30 HP (10 HP jika musuh DEFEND) | CD == 0 |
| Bertahan | `DEFEND` | Reduksi damage 65% giliran berikutnya | Selalu tersedia |
| Minum Potion | `POTION` | Pulihkan +25 HP | Pot > 0 DAN HP < 100 |

Mekanisme cooldown Heavy Attack: setelah digunakan, $CD \leftarrow 2$ dan berkurang 1 setiap giliran sendiri.

Perhitungan damage efektif ($D_{\text{effective}}$):
$$D_{\text{effective}} = \begin{cases} 
D_{\text{base}} \times 0.35, & \text{jika target } Def = \text{True} \\
D_{\text{base}}, & \text{jika target } Def = \text{False}
\end{cases}$$

### 1.4 Terminal Test ($Terminal(s)$)
Duel berakhir jika HP salah satu atau kedua pihak $\le 0$:
$$Terminal(s) = (HP_p \le 0) \lor (HP_n \le 0)$$

### 1.5 Utility Function ($U(s)$)
Nilai utilitas mutlak pada terminal state bagi agen MAX (NPC):
$$U(s) = \begin{cases} 
+1000 + HP_n, & \text{jika } HP_p \le 0 \land HP_n > 0 \quad (\text{NPC Menang}) \\
-1000 - HP_p, & \text{jika } HP_n \le 0 \land HP_p > 0 \quad (\text{Player Menang}) \\
0, & \text{jika } HP_p \le 0 \land HP_n \le 0 \quad (\text{Seri})
\end{cases}$$

Bonus/penalti HP sisa mendorong AI mengeksekusi kemenangan secepat mungkin dan meminimalisir damage diterima.

### 1.6 Evaluation Functions ($Eval(s)$)
Digunakan saat pencarian mencapai batas kedalaman (*depth limit*). Tiga fungsi tersedia:

**1. Balanced (Seimbang — Default):**
$$Eval_{\text{bal}}(s) = 2.0(HP_n - HP_p) + 12.0(Pot_n - Pot_p) + I(Def_n \land HP_p > 20) \times 5.0$$

**2. Aggressive (Penyerang — Ofensif):**
$$Eval_{\text{agg}}(s) = 4.0(100 - HP_p) - 1.2(100 - HP_n) + 4.0 \cdot Pot_n + I(HP_p \le 30) \times 35.0$$

**3. Defensive (Bertahan — Taktis):**
$$Eval_{\text{def}}(s) = 3.0 \cdot HP_n - 1.5 \cdot HP_p + 20.0 \cdot Pot_n + I(Def_n) \times 15.0 - I(HP_n < 40 \land Pot_n > 0) \times 25.0$$

di mana $I(\cdot)$ adalah fungsi indikator bernilai 1 jika kondisi terpenuhi.

---

## 2. Formulasi Algoritma AI Adversarial

### 2.1 Pure Minimax (Minimax Murni)
Algoritma adversarial dua pemain *zero-sum* berbasis DFS yang mengeksplorasi **seluruh pohon permainan** hingga terminal state atau depth limit.

**Rumus rekursif:**
$$V(s, d) = \begin{cases} 
U(s), & \text{jika } Terminal(s) \\
Eval(s), & \text{jika } d = 0 \\
\max_{a \in A(s)} V(\delta(s,a), d{-}1), & \text{jika } Turn = \text{MAX (NPC)} \\
\min_{a \in A(s)} V(\delta(s,a), d{-}1), & \text{jika } Turn = \text{MIN (Player)}
\end{cases}$$

**Kompleksitas:** Waktu $O(b^d)$, Ruang $O(b \cdot d)$

### 2.2 Alpha-Beta Pruning & Move Ordering
Optimasi Minimax yang memangkas cabang tidak relevan menggunakan batas:
- $\alpha$ = nilai terbaik yang dijamin MAX (batas bawah), awalnya $-\infty$
- $\beta$ = nilai terbaik yang dijamin MIN (batas atas), awalnya $+\infty$

**Kondisi pemangkasan (*cutoff*):**
- Pada node MIN, jika $V(s') \le \alpha$ → **$\beta$-cutoff** (MIN tidak akan memilih jalur ini)
- Pada node MAX, jika $V(s') \ge \beta$ → **$\alpha$-cutoff** (MAX tidak akan memilih jalur ini)

**Kompleksitas kasus terbaik:** $O(b^{d/2})$ — setara menggandakan kedalaman yang dapat dijangkau.

**Heuristic Move Ordering** — mengurutkan aksi paling menjanjikan lebih dahulu agar cutoff terjadi lebih awal:

| Node | Urutan Prioritas (Tertinggi ke Terendah) |
|:-----|:-----------------------------------------|
| **MAX (NPC)** | `HEAVY_ATTACK` > `ATTACK` > `POTION` > `DEFEND` |
| **MIN (Player)** | `HEAVY_ATTACK` > `ATTACK` > `DEFEND` > `POTION` |

Implementasi (`battle_ai.py`):
```python
# Node MAX: urutkan berdasarkan skor prioritas, besar ke kecil
actions.sort(
    key=lambda a: (3 if a == HEAVY else 2 if a == ATTACK else 1 if a == POTION else 0),
    reverse=True
)
```

### 2.3 Expectimax Search (Pencarian Stokastik)
Variasi Minimax untuk lingkungan probabilistik. Pada Bakekok, `HEAVY_ATTACK` memiliki:
- $P(\text{hit}) = 0.75$ → damage penuh (30 HP)
- $P(\text{miss}) = 0.25$ → tidak ada damage (0 HP)

**Formula Chance Node:**
$$V_{\text{Exp}}(s, \text{HEAVY}) = 0.75 \cdot V(\delta(s, \text{HEAVY}_{\text{hit}}), d{-}1) + 0.25 \cdot V(\delta(s, \text{HEAVY}_{\text{miss}}), d{-}1)$$

Aksi lain (`ATTACK`, `DEFEND`, `POTION`) tetap deterministik. Implementasi di `battle_ai.py`:
```python
if action == ACTION_HEAVY:
    state_hit  = state.apply_action(action, heavy_hits=True)
    state_miss = state.apply_action(action, heavy_hits=False)
    val = 0.75 * self.expectimax(state_hit, depth-1, False, eval_fn) + \
          0.25 * self.expectimax(state_miss, depth-1, False, eval_fn)
```

---

## 3. Hasil Pengujian & Eksperimen AI

Seluruh eksperimen dieksekusi secara otomatis dan diverifikasi menggunakan modul evaluasi pada `scratch/run_experiments.py`.

### 3.1 Eksperimen 1: Perbandingan Pure Minimax vs Alpha-Beta Pruning
Eksperimen ini menguji efisiensi pemangkasan cabang (*pruning*) pada variasi batas kedalaman (Depth 1 hingga 6).

| Depth | Node Minimax | Node Alpha-Beta | Pemangkasan Cabang (%) | Waktu Minimax (ms) | Waktu Alpha-Beta (ms) | Keputusan Identik? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 4 | 4 | 0.0 % | 0.07 ms | 0.04 ms | True |
| 2 | 20 | 20 | 0.0 % | 0.07 ms | 0.09 ms | True |
| 3 | 82 | 51 | 37.8 % | 0.20 ms | 0.09 ms | True |
| 4 | 327 | 142 | 56.6 % | 0.38 ms | 0.21 ms | True |
| 5 | 1,277 | 302 | 76.4 % | 1.52 ms | 0.51 ms | True |
| 6 | 4,983 | 712 | 85.7 % | 6.23 ms | 1.03 ms | True |

> **Analisis:**
> - Pada kedalaman 6, Alpha-Beta Pruning berhasil memangkas **85.7% node** dari pohon pencarian tanpa mengubah nilai keputusan ataupun aksi terbaik sama sekali (*admissible & optimal*).
> - Kecepatan eksekusi Alpha-Beta meningkat hingga **6x lipat lebih cepat** dibandingkan Minimax murni pada Depth 6 (1.03 ms vs 6.23 ms).

---

### 3.2 Eksperimen 2: Dampak Move Ordering (Urutan Aksi)
Eksperimen ini membandingkan kinerja Alpha-Beta Pruning saat cabang dievaluasi secara acak/natural vs saat cabang diurutkan (*heuristic move ordering*):

| Depth | Tanpa Move Ordering (Nodes) | Dengan Move Ordering (Nodes) | Peningkatan Reduksi Node (%) |
|:---:|:---:|:---:|:---:|
| 3 | 66 | 51 | 22.7 % |
| 4 | 211 | 142 | 32.7 % |
| 5 | 592 | 302 | 49.0 % |
| 6 | 1,611 | 712 | 55.8 % |

> **Analisis:**
> - Menempatkan aksi-aksi ofensif/kritis terlebih dahulu di pohon pencarian memungkinkan nilai $\alpha$ dan $\beta$ terdorong ke nilai ekstrem lebih awal.
> - Hal ini menghasilkan kondisi *cutoff* ($\beta \le \alpha$) yang jauh lebih cepat, memangkas tambahan **55.8% node** pada Depth 6.

---

### 3.3 Eksperimen 3: Perilaku NPC Berdasarkan Fungsi Evaluasi
Depth 4 + Alpha-Beta Pruning. Tiga skenario kondisi duel:

#### Skenario A: Kondisi Awal Netral ($HP_p=100, HP_n=100$)
| Evaluasi | Aksi Terpilih | Skor | Interpretasi |
|:---------|:-------------|:-----|:-------------|
| Balanced | HEAVY_ATTACK | 0.0 | Inisiatif ofensif terukur |
| Aggressive | HEAVY_ATTACK | 48.0 | Menekan lawan sedini mungkin |
| Defensive | DEFEND | 145.0 | Utamakan pertahanan sebelum aksi berisiko |

#### Skenario B: NPC Tertekan ($HP_p=75, HP_n=25$)
| Evaluasi | Aksi Terpilih | Alasan |
|:---------|:-------------|:-------|
| Semua (3 fungsi) | POTION | Satu-satunya aksi yang mencegah kekalahan terminal di giliran berikutnya |

Pada skenario ini, aksi serangan apapun memungkinkan Player membalas dan membunuh NPC ber-HP 25. Pencarian di kedalaman berikutnya menemukan kekalahan terminal tersebut, sehingga ketiga evaluasi bersepakat memilih `POTION` sebagai satu-satunya pilihan rasional.

#### Skenario C: Kondisi Eksekusi ($HP_p=20, HP_n=70$)
| Evaluasi | Aksi Terpilih | Skor Utility |
|:---------|:-------------|:-------------|
| Semua (3 fungsi) | HEAVY_ATTACK | +1070.0 |

`HEAVY_ATTACK` (30 damage) langsung mengeksekusi kemenangan — $HP_p: 20 \rightarrow 0$. Skor $+1070 = +1000 \text{ (kemenangan)} + 70 \text{ (sisa HP NPC)}$.

---

### 3.4 Eksperimen 4: Analisis Expectimax (Stokastik & Probabilitas)
Pada varian ini, aksi `HEAVY_ATTACK` memiliki elemen peluang (*chance node*): $75\%$ akurasi mendarat (30 damage) dan $25\%$ meleset (0 damage).

| Aksi | Skor Deterministik (Alpha-Beta) | Skor Probabilistik (Expectimax) |
|:---|:---:|:---:|
| `ATTACK` (Pasti) | -46.0 | -14.25 |
| `HEAVY_ATTACK` (75% Chance) | 22.0 | 3.94 |
| `DEFEND` | -38.0 | -38.0 |
| `POTION` | -22.0 | -7.0 |

> **Analisis:**
> - Pada Expectimax, skor ekspektasi `HEAVY_ATTACK` terkoreksi turun dari $+22.0$ menjadi $+3.94$ akibat penalti 25% kemungkinan serangan meleset.
> - Meskipun terkoreksi, nilai ekspektasi secara matematis tetap positif dan tetap menjadi aksi rasional terbaik bagi NPC pada kondisi tersebut.

---

## 4. Fitur Interactive Debug Overlay

### 4.1 Mode Eksplorasi (Pathfinding Overlay)
- **Dropdown Algoritma:** UCS, A\* Manhattan, A\* Euclidean, A\* Chebyshev
- **Toggle Cost Display:** Tampilkan/sembunyikan bobot biaya setiap sel di peta
- **Statistik Real-Time:** Jumlah node diekspansi, panjang jalur, total cost, waktu eksekusi (ms)
- **Off-Screen NPC Indicator:** Panah pulsing di tepi layar menunjukkan arah NPC saat di luar viewport kamera

### 4.2 Mode Duel (Battle Overlay)
- **Dropdown Algoritma AI:** Pilih Alpha-Beta Pruning, Pure Minimax, atau Expectimax
- **Dropdown Evaluasi NPC:** Pilih Balanced, Aggressive, atau Defensive
- **Selector Depth Limit:** Kedalaman pencarian dinamis (Depth 1 s/d 8)
- **Toggle Move Ordering:** Aktifkan/nonaktifkan optimasi pengurutan aksi
- **Live Action Scoring Table:** Skor heuristik per aksi legal dengan tanda `▶` untuk aksi terpilih
- **Live Statistics:** Jumlah node dikunjungi, branch di-prune, waktu berpikir AI (ms)
- **Battle Log:** 8 baris terakhir log duel (siapa melakukan aksi apa, berapa damage)

---

## 5. Kesimpulan

1. **Kebenaran Pathfinding:** UCS dan A\* (tiga heuristik) menghasilkan jalur identik dan optimal. Perbedaan hanya pada efisiensi — A\* lebih efisien berkat panduan heuristik.

2. **Kebenaran Weighted Terrain:** Jalan tanah (1.0) dan rumput (2.0) diimplementasikan benar melalui identifikasi tipe tile berbasis nama aset dan koordinat atlas di `mapdata.py`.

3. **Optimalitas Alpha-Beta:** Menghasilkan keputusan identik dengan Pure Minimax sambil memangkas **85.7% node** pada Depth 6 — membuktikan properti *admissibility* dan *soundness*.

4. **Efektivitas Move Ordering:** Pengurutan aksi ofensif lebih dahulu meningkatkan efisiensi pruning tambahan **55.8%** pada Depth 6.

5. **Differensiasi Evaluasi:** Ketiga fungsi evaluasi menghasilkan perilaku strategis berbeda pada kondisi netral, namun sepakat pada kondisi kritis di mana pilihan optimal sudah jelas.

6. **Expectimax vs Deterministik:** Expectimax memberi skor ekspektasi lebih realistis untuk `HEAVY_ATTACK` probabilistik, namun pada banyak skenario pilihan akhir tetap sama karena *expected value*-nya masih tertinggi.

---

## Lampiran: Cara Menjalankan

```bash
# Instalasi dependensi
pip install -r requirements.txt

# Jalankan game utama
python main.py

# Jalankan benchmark eksperimen AI
python scratch/run_experiments.py
```

**Kontrol Mode Eksplorasi:**
- `[W/A/S/D]` atau `[Arrow]`: Gerakkan Player
- `[Space]`: Panggil NPC mengejar Player
- `[B]`: Masuk ke Mode Duel langsung
- `[Esc]`: Keluar dari permainan

**Kontrol Mode Duel:**
- `[1]` / `[A]`: ATTACK (18 damage)
- `[2]` / `[S]`: HEAVY_ATTACK (30 damage)
- `[3]` / `[D]`: DEFEND (reduksi damage 65%)
- `[4]` / `[W]`: POTION (+25 HP)
- `[R]`: Reset / mulai ulang duel
- `[Tab]`: Kembali ke Mode Eksplorasi Peta
