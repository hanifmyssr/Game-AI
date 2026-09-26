# Bakekok - Dokumentasi Teknis & Game AI (Tahap 1 & Tahap 2)

Proyek Tugas Besar Mata Kuliah Kecerdasan Buatan - Kelompok 7 (Universitas Pendidikan Indonesia)  
Program Studi Ilmu Komputer, Universitas Pendidikan Indonesia.

---

## 1. Identitas Proyek & Anggota Kelompok

- **Nama Game**: Bakekok
- **Mata Kuliah**: Kecerdasan Buatan
- **Kelompok**: 7 (Tubes AI)
- **Anggota Kelompok**:
  - Hanif Muyassar
  - Moch Fadillah Pratama
  - Muhammad Zidan Mirza Fedrieka

---

## 2. Arsitektur Sistem & Struktur Kode

Sistem dikembangkan menggunakan Python 3.10+ berbasis kerangka Pygame dengan arsitektur modular yang memisahkan komponen *rendering*, *game loop*, *pathfinding engine*, *adversarial battle engine*, dan *interactive debug overlay*.

```
Game-AI/
├── main.py                     # Entry point aplikasi utama
├── requirements.txt            # Dependensi proyek (pygame)
├── data/
│   └── map.json                # Metadata grid peta, ubin tanah, dan rintangan
├── game/
│   ├── __init__.py
│   ├── app.py                  # Main loop, penanganan input, kamera, dan manajer state
│   ├── battle_ai.py            # Engine AI Duel (State, Utility, Minimax, Alpha-Beta, Expectimax)
│   ├── battle_system.py        # Logika pertarungan turn-based dan pemilih aksi NPC
│   ├── config.py               # Konstanta visual, warna panel, skala, dan jalur aset
│   ├── events.py               # Event dispatcher untuk komunikasi antar-komponen
│   ├── mapdata.py              # Parser map.json, pembangun surface, dan sistem koordinat
│   ├── npc.py                  # Entitas NPC Kucing (pathfinding real-time & pengatur jarak duel)
│   ├── overlay.py              # Visualisasi debug overlay (Pathfinding stats & Duel stats)
│   ├── player.py               # Entitas Player (Bolu)
│   └── search.py               # Engine Pencarian Jalur (UCS, A* Search, dan Heuristik)
└── scratch/
    ├── analyze_map.py          # Script analisis karakteristik peta
    └── run_experiments.py      # Script otomatisasi eksperimen benchmark AI
```

---

## 3. Tahap 1: Pathfinding & Algoritma Pencarian Jalur

### 3.1 Model Grid & Weighted Terrain Cost
Peta permainan direpresentasikan sebagai grid 2D $N \times M$ dengan ukuran ubin $16 \times 16$ piksel. Setiap sel grid $n = (x, y)$ memiliki tipe medan dengan bobot langkah (*step cost*) $c(n, n')$ yang berbeda:

$$c(n, n') = \begin{cases} 
0.5, & \text{jika } n' \in \text{Jalan Tanah (Dirt Road)} \\
1.0, & \text{jika } n' \in \text{Rumput (Grass)} \\
\infty, & \text{jika } n' \in \text{Rintangan (Obstacle / Non-walkable)}
\end{cases}$$

### 3.2 Algoritma Pencarian Jalur

1. **Uniform Cost Search (UCS)**:
   Algoritma pencarian tak diinformasikan (*uninformed search*) yang mengekspansi node berdasarkan akumulasi biaya jalur riwayat terendah $g(n)$ dari titik awal tanpa memperhitungkan estimasi sisa jarak ke target ($h(n) = 0$).
   
   Fungsi evaluasi node:
   $$f(n) = g(n), \quad h(n) = 0$$
   di mana $g(n)$ dihitung secara akumulatif:
   $$g(n) = g(\text{parent}(n)) + c(\text{parent}(n), n)$$

2. **A* Search**:
   Algoritma pencarian diinformasikan (*informed search*) yang menggabungkan akumulasi biaya riwayat $g(n)$ dengan estimasi jarak heuristik $h(n)$ untuk mengarahkan pencarian ke target secara efisien.
   
   Fungsi evaluasi node:
   $$f(n) = g(n) + h(n)$$
   
   *Tie-breaking rule*: Jika dua node memiliki nilai $f(n)$ yang identik, node dengan nilai $h(n)$ lebih kecil diprioritaskan diekspansi terlebih dahulu:
   $$\text{Priority}(n) = (f(n), h(n))$$

### 3.3 Formulasi Matematika Fungsi Heuristik $h(n)$
Fungsi heuristik $h(n)$ memperkirakan jarak terpendek dari posisi saat ini $a = (x_a, y_a)$ ke target $b = (x_b, y_b)$:

1. **Manhattan Distance**:
   $$h_{\text{Manhattan}}(a, b) = |x_a - x_b| + |y_a - y_b|$$

2. **Euclidean Distance**:
   $$h_{\text{Euclidean}}(a, b) = \sqrt{(x_a - x_b)^2 + (y_a - y_b)^2}$$

3. **Chebyshev Distance**:
   $$h_{\text{Chebyshev}}(a, b) = \max(|x_a - x_b|, |y_a - y_b|)$$

---

## 4. Tahap 2: Duel Turn-Based NPC vs Player (Adversarial Search)

### 4.1 Pemicu Transisi Duel
Pertarungan otomatis dipemicu ketika jarak Manhattan antara Player dan NPC bernilai $\le 1$:

$$d_{\text{Manhattan}}(\text{Player}, \text{NPC}) = |x_{\text{player}} - x_{\text{npc}}| + |y_{\text{player}} - y_{\text{npc}}| \le 1$$

### 4.2 Formulasi Formal State Space ($S$) & State Vector
Ruang keadaan (*State Space*) $S$ mencakup seluruh konfigurasi posisi pertarungan yang mungkin. Suatu keadaan direpresentasikan sebagai *State Vector* $s$:

$$s = \langle HP_{\text{player}}, HP_{\text{npc}}, Pot_{\text{player}}, Pot_{\text{npc}}, Def_{\text{player}}, Def_{\text{npc}}, Turn, CD_{\text{player}}, CD_{\text{npc}} \rangle$$

Batasan variabel state:
- $HP_{\text{player}}, HP_{\text{npc}} \in [0, 100]$: Status kesehatan petarung.
- $Pot_{\text{player}}, Pot_{\text{npc}} \in [0, 3]$: Cadangan potion pemulih (stok awal = 2, maksimal = 3).
- $Def_{\text{player}}, Def_{\text{npc}} \in \{\text{True}, \text{False}\}$: Status posisi mempertahankan diri.
- $Turn \in \{\text{MAX (NPC)}, \text{MIN (Player)}\}$: Hak giliran petarung.
- $CD_{\text{player}}, CD_{\text{npc}} \in [0, 2]$: Sisa giliran *cooldown* serangan `HEAVY_ATTACK`.

### 4.3 Ruang Aksi ($A(s)$) & Branching Factor ($b \le 4$)
*Branching Factor* ($b$) adalah jumlah pilihan aksi legal yang dapat diambil dari suatu state node. Pada pertarungan ini, $b \le 4$:

1. **`ATTACK`**: Serangan standar ($D_{\text{base}} = 18$).
2. **`HEAVY_ATTACK`**: Serangan kuat ($D_{\text{base}} = 30$, legal jika $CD = 0$, memicu $CD \leftarrow 2$).
3. **`DEFEND`**: Memasang posisi bertahan (mereduksi kerusakan yang masuk sebesar $65\%$).
4. **`POTION`**: Memulihkan $+25$ HP (legal jika $Pot > 0$ dan $HP < 100$).

Perhitungan kerusakan efektif $D_{\text{effective}}$:

$$D_{\text{effective}} = \begin{cases} 
D_{\text{base}} \times (1 - 0.65) = \lfloor D_{\text{base}} \times 0.35 \rceil, & \text{jika target } Def = \text{True} \\
D_{\text{base}}, & \text{jika target } Def = \text{False}
\end{cases}$$

### 4.4 Terminal Test & Utility Function ($U(s)$)
*Terminal Test* menguji apakah pertarungan telah berakhir ($HP \le 0$). *Utility Function* $U(s)$ memberikan skor numerik mutlak pada keadaan akhir bagi agen MAX (NPC):

$$Terminal(s) = (HP_{\text{player}} \le 0) \lor (HP_{\text{npc}} \le 0)$$

$$U(s) = \begin{cases} 
+1000 + HP_{\text{npc}}, & \text{jika } HP_{\text{player}} \le 0 \land HP_{\text{npc}} > 0 \quad (\text{NPC Menang}) \\
-1000 - HP_{\text{player}}, & \text{jika } HP_{\text{npc}} \le 0 \land HP_{\text{player}} > 0 \quad (\text{Player Menang}) \\
0, & \text{jika } HP_{\text{player}} \le 0 \land HP_{\text{npc}} \le 0 \quad (\text{Seri})
\end{cases}$$

### 4.5 Depth Limit & Evaluation Function ($Eval(s)$)
Ketika pencarian mencapai batas kedalaman (*Depth Limit*), pencarian dihentikan (*early stop*) dan skor heuristik dibangkitkan oleh *Evaluation Function* $Eval(s)$ untuk memperkirakan keuntungan state:

1. **Balanced Evaluation (Seimbang / Standar)**:
   $$Eval_{\text{bal}}(s) = 2.0 \times (HP_{\text{npc}} - HP_{\text{player}}) + 12.0 \times (Pot_{\text{npc}} - Pot_{\text{player}}) + I(Def_{\text{npc}} \land HP_{\text{player}} > 20) \times 5.0$$

2. **Aggressive Evaluation (Penyerang / Offensif)**:
   $$Eval_{\text{agg}}(s) = 4.0 \times (100 - HP_{\text{player}}) - 1.2 \times (100 - HP_{\text{npc}}) + 4.0 \times Pot_{\text{npc}} + I(HP_{\text{player}} \le 30) \times 35.0$$

3. **Defensive Evaluation (Bertahan / Taktis)**:
   $$Eval_{\text{def}}(s) = 3.0 \times HP_{\text{npc}} - 1.5 \times HP_{\text{player}} + 20.0 \times Pot_{\text{npc}} + I(Def_{\text{npc}}) \times 15.0 - I(HP_{\text{npc}} < 40 \land Pot_{\text{npc}} > 0) \times 25.0$$

### 4.6 Algoritma Pencarian Adversarial

#### 4.6.1 Pure Minimax (Minimax Murni)
Algoritma pencarian adversarial berbasis penelusuran mendalam (*Depth-First Search*) yang mengeksplorasi seluruh kemungkinan cabang permainan dua pemain *zero-sum* dengan kompleksitas waktu $O(b^d)$ dan kompleksitas ruang $O(b \cdot d)$.

Formula rekursif Minimax:
$$V(s) = \begin{cases} 
U(s), & \text{jika } Terminal(s) \\
Eval(s), & \text{jika depth} = 0 \\
\max_{a \in A(s)} V(\delta(s, a)), & \text{jika } Turn = \text{MAX (NPC)} \\
\min_{a \in A(s)} V(\delta(s, a)), & \text{jika } Turn = \text{MIN (Player)}
\end{cases}$$

#### 4.6.2 Alpha-Beta Pruning (Pemangkasan Alfa-Beta)
Teknik optimasi yang memotong cabang pohon pencarian yang tidak mempengaruhi keputusan akhir dengan mempertahankan batas bawah $\alpha$ (kepastian terbaik MAX) dan batas atas $\beta$ (kepastian terbaik MIN). Pemangkasan menurunkan kompleksitas waktu kasus terbaik dari $O(b^d)$ menjadi $O(b^{d/2})$.

Kondisi pemangkasan (*Cutoff Condition*):
- Pada node MIN, jika $V(s') \le \alpha$, lakukan $\beta$-cutoff.
- Pada node MAX, jika $V(s') \ge \beta$, lakukan $\alpha$-cutoff.

#### 4.6.3 Heuristic Move Ordering (Pengurutan Aksi)
Teknik mengurutkan cabang aksi paling menjanjikan terlebih dahulu di root/intermediate node agar batas $\alpha$ dan $\beta$ terdorong ke nilai ekstrem lebih cepat, sehingga memicu kondisi *cutoff* lebih awal.

Prioritas pengurutan aksi:
- Node MAX (NPC): `HEAVY_ATTACK` $\succ$ `ATTACK` $\succ$ `POTION` $\succ$ `DEFEND`.
- Node MIN (Player): `HEAVY_ATTACK` $\succ$ `ATTACK` $\succ$ `DEFEND` $\succ$ `POTION`.

#### 4.6.4 Expectimax Search (Pencarian Stokastik)
Variasi pencarian adversarial untuk lingkungan tidak pasti/probabilistik. Node MIN digantikan oleh *Chance Node* yang menghitung *Expected Value* (rata-rata tertimbang probabilitas).

Pada Bakekok, `HEAVY_ATTACK` memiliki akurasi mendarat $75\%$ ($P_{\text{hit}} = 0.75$) dan meleset $25\%$ ($P_{\text{miss}} = 0.25$):
$$V_{\text{Expectimax}}(s, \text{HEAVY}) = 0.75 \times V(\delta(s, \text{HEAVY}_{\text{hit}})) + 0.25 \times V(\delta(s, \text{HEAVY}_{\text{miss}}))$$

---

## 5. Hasil Pengujian Benchmark & Analisis Kinerja

### 5.1 Perbandingan Pure Minimax vs Alpha-Beta Pruning
Hasil benchmark pada berbagai batas kedalaman (*depth limit 1 s/d 6*):

| Depth | Node Minimax | Node Alpha-Beta | Pemangkasan Cabang (%) | Waktu Minimax (ms) | Waktu Alpha-Beta (ms) | Keputusan Identik? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 4 | 4 | 0.0 % | 0.07 ms | 0.04 ms | True |
| 2 | 20 | 20 | 0.0 % | 0.07 ms | 0.09 ms | True |
| 3 | 82 | 51 | 37.8 % | 0.20 ms | 0.09 ms | True |
| 4 | 327 | 142 | 56.6 % | 0.38 ms | 0.21 ms | True |
| 5 | 1,277 | 302 | 76.4 % | 1.52 ms | 0.51 ms | True |
| 6 | 4,983 | 712 | 85.7 % | 6.23 ms | 1.03 ms | True |

Analisis: Alpha-Beta Pruning mampu mengurangi node yang dikunjungi hingga **85.7%** pada Depth 6 dengan peningkatan kecepatan eksekusi hingga **6x lipat**, tanpa mengubah nilai utilitas dan keputusan terbaik (*admissible & optimal*).

### 5.2 Dampak Move Ordering pada Alpha-Beta Pruning

| Depth | Nodes Tanpa Move Ordering | Nodes Dengan Move Ordering | Reduksi Node Tambahan (%) |
|:---:|:---:|:---:|:---:|
| 3 | 66 | 51 | 22.7 % |
| 4 | 211 | 142 | 32.7 % |
| 5 | 592 | 302 | 49.0 % |
| 6 | 1,611 | 712 | 55.8 % |

Analisis: Pengurutan aksi menjanjikan lebih awal meningkatkan efisiensi pemangkasan cabang tambahan sebesar **55.8%** pada Depth 6.

### 5.3 Perbandingan Deterministik vs Expectimax (Skor Aksi Root Node)

| Aksi Legal | Skor Deterministik (Alpha-Beta) | Skor Probabilistik (Expectimax) |
|:---|:---:|:---:|
| `ATTACK` | -46.0 | -14.25 |
| `HEAVY_ATTACK` | 22.0 | 3.94 |
| `DEFEND` | -38.0 | -38.0 |
| `POTION` | -22.0 | -7.0 |

Analisis: Expectimax memperhitungkan risiko 25% meleset pada `HEAVY_ATTACK`, menyesuaikan skor ekspektasi dari 22.0 menjadi 3.94.

---

## 6. Kontrol Permainan

### 6.1 Mode Eksplorasi (Peta Grid)
- **[W, A, S, D] / [Tombol Panah]**: Menggerakkan Player (Bolu).
- **[Spasi]**: Memanggil NPC agar mengejar Player.
- **[B]**: Pintas langsung masuk ke Mode Duel.
- **[Esc]**: Keluar dari permainan.

### 6.2 Mode Duel (Pertarungan Turn-Based)
- **[1 / A]**: Eksekusi aksi `ATTACK` (18 damage).
- **[2 / S]**: Eksekusi aksi `HEAVY_ATTACK` (30 damage).
- **[3 / D]**: Eksekusi aksi `DEFEND` (mereduksi damage 65%).
- **[4 / W]**: Eksekusi aksi `POTION` (+25 HP heal).
- **[R]**: Reset / mulai ulang duel.
- **[Tab]**: Kembali ke Mode Eksplorasi Peta.

---

## 7. Cara Menjalankan

1. **Instalasi Dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Jalankan Permainan Utama**:
   ```bash
   python main.py
   ```

3. **Jalankan Benchmarking Eksperimen AI**:
   ```bash
   python scratch/run_experiments.py
   ```

Dokumen hasil pengujian dan analisis akademis terperinci dapat diakses pada [`LAPORAN_TAHAP_2.md`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/LAPORAN_TAHAP_2.md).

