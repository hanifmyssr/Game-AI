# LAPORAN TAHAP-2: DUEL TURN-BASED MENGGUNAKAN MINIMAX & ALPHA-BETA PRUNING

**Mata Kuliah:** Kecerdasan Buatan  
**Kelompok 7:**
- Hanif Muyassar
- Moch Fadillah Pratama
- Muhammad Zidan Mirza Fedrieka  
**Program Studi:** Ilmu Komputer - Universitas Pendidikan Indonesia

---

## 1. Pendahuluan & Formulasi Masalah AI
Pada Tugas Besar Tahap-2 ini, sistem permainan diperluas dari fase pencarian jalur (*Pathfinding A\* & UCS*) menjadi fase **Duel Turn-Based (Pertarungan Bergilir)** antara Bolu (Player) dan Kucing Hitam (NPC) saat keduanya berada dalam jarak kedekatan (jarak Manhattan $\le 1$).

Pencarian keputusan NPC dimodelkan menggunakan kerangka kerja **Adversarial Search (Game Theory)** dengan formulasi formal:

### 1.1 State Representation ($S$)
Suatu *state* $s$ merepresentasikan snapshot kondisi duel lengkap:
$$s = \langle HP_{\text{player}}, HP_{\text{npc}}, Pot_{\text{player}}, Pot_{\text{npc}}, Def_{\text{player}}, Def_{\text{npc}}, Turn \rangle$$
- $HP_{\text{player}}, HP_{\text{npc}} \in [0, 100]$: Status kesehatan masing-masing petarung.
- $Pot_{\text{player}}, Pot_{\text{npc}} \in [0, 3]$: Jumlah cadangan potion pemulih (+25 HP).
- $Def_{\text{player}}, Def_{\text{npc}} \in \{\text{True}, \text{False}\}$: Status bertahan (mengurangi damage yang masuk berikutnya sebesar 65%).
- $Turn \in \{\text{MAX (NPC)}, \text{MIN (Player)}\}$: Petarung yang memegang hak giliran.

### 1.2 Actions ($A(s)$) — Branching Factor $b \le 4$
Setiap giliran, petarung dapat memilih maksimal salah satu dari 4 aksi legal:
1. `ATTACK`: Serangan reguler dengan damage dasar 18 (tereduksi menjadi 6 jika musuh bertahan).
2. `HEAVY_ATTACK`: Serangan telak dengan damage dasar 30 (tereduksi menjadi 10 jika musuh bertahan).
3. `DEFEND`: Memasang posisi bertahan, mereduksi kerusakan yang diterima giliran berikutnya sebesar ~65%.
4. `POTION`: Memulihkan +25 HP (hanya legal jika sisa potion > 0 dan HP < 100).

### 1.3 Terminal Test ($Terminal(s)$)
Permainan mencapai kondisi akhir jika salah satu atau kedua petarung memiliki $HP \le 0$:
$$Terminal(s) = (HP_{\text{player}} \le 0) \lor (HP_{\text{npc}} \le 0)$$

### 1.4 Utility Function ($U(s)$)
Diberikan pada terminal state:
$$U(s) = \begin{cases} 
+1000 + HP_{\text{npc}}, & \text{jika } HP_{\text{player}} \le 0 \land HP_{\text{npc}} > 0 \quad (\text{NPC/MAX Menang}) \\
-1000 - HP_{\text{player}}, & \text{jika } HP_{\text{npc}} \le 0 \land HP_{\text{player}} > 0 \quad (\text{Player/MIN Menang}) \\
0, & \text{jika keduanya } \le 0 \quad (\text{Seri})
\end{cases}$$

### 1.5 Evaluation Functions ($Eval(s)$)
Ketika pohon pencarian mencapai batas kedalaman (*depth limit*), fungsi evaluasi memperkirakan seberapa menguntungkan state tersebut bagi MAX:
1. **Balanced (Standar):**
   $$Eval_{\text{bal}}(s) = 2.0 \times (HP_{\text{npc}} - HP_{\text{player}}) + 12.0 \times (Pot_{\text{npc}} - Pot_{\text{player}}) + (5.0 \text{ jika } Def_{\text{npc}})$$
2. **Aggressive (Offensif):**
   $$Eval_{\text{agg}}(s) = 4.0 \times (100 - HP_{\text{player}}) - 1.2 \times (100 - HP_{\text{npc}}) + 4.0 \times Pot_{\text{npc}} + (35.0 \text{ jika } HP_{\text{player}} \le 30)$$
3. **Defensive (Taktis/Kelangsungan Hidup):**
   $$Eval_{\text{def}}(s) = 3.0 \times HP_{\text{npc}} - 1.5 \times HP_{\text{player}} + 20.0 \times Pot_{\text{npc}} + (15.0 \text{ jika } Def_{\text{npc}}) - (25.0 \text{ jika sekarat & punya potion})$$

---

## 2. Hasil Pengujian & Eksperimen AI

Semua eksperimen dieksekusi secara otomatis dan diverifikasi menggunakan modul evaluasi pada `scratch/run_experiments.py`.

### 2.1 Eksperimen 1: Perbandingan Pure Minimax vs Alpha-Beta Pruning
Eksperimen ini menguji efisiensi pemangkasan cabang (*pruning*) pada variasi batas kedalaman (Depth 1 hingga 6).

| Depth | Node Minimax | Node Alpha-Beta | Pemangkasan Cabang (%) | Waktu Minimax (ms) | Waktu Alpha-Beta (ms) | Keputusan Identik? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 4 | 4 | 0.0 % | 0.07 ms | 0.04 ms | **True** |
| 2 | 20 | 20 | 0.0 % | 0.07 ms | 0.09 ms | **True** |
| 3 | 82 | 51 | 37.8 % | 0.20 ms | 0.09 ms | **True** |
| 4 | 327 | 142 | 56.6 % | 0.38 ms | 0.21 ms | **True** |
| 5 | 1,277 | 302 | 76.4 % | 1.52 ms | 0.51 ms | **True** |
| 6 | 4,983 | 712 | **85.7 %** | 6.23 ms | 1.03 ms | **True** |

> **Analisis:**
> - Pada kedalaman 6, Alpha-Beta Pruning berhasil memangkas **85.7% node** dari pohon pencarian tanpa mengubah nilai keputusan ataupun aksi terbaik sama sekali (*admissible & optimal*).
> - Kecepatan eksekusi Alpha-Beta meningkat hingga **6x lipat lebih cepat** dibandingkan Minimax murni pada Depth 6 (1.03 ms vs 6.23 ms).

---

### 2.2 Eksperimen 2: Dampak Move Ordering (Urutan Aksi)
Eksperimen ini membandingkan kinerja Alpha-Beta Pruning saat cabang dievaluasi secara acak/natural vs saat cabang diurutkan (*heuristic move ordering*):

| Depth | Tanpa Move Ordering (Nodes) | Dengan Move Ordering (Nodes) | Peningkatan Reduksi Node (%) |
|:---:|:---:|:---:|:---:|
| 3 | 66 | 51 | 22.7 % |
| 4 | 211 | 142 | 32.7 % |
| 5 | 592 | 302 | 49.0 % |
| 6 | 1,611 | 712 | **55.8 %** |

> **Analisis:**
> - Menempatkan aksi-aksi ofensif/kritis terlebih dahulu di pohon pencarian memungkinkan nilai $\alpha$ dan $\beta$ terdorong ke nilai ekstrem lebih awal.
> - Hal ini menghasilkan kondisi *cutoff* ($\beta \le \alpha$) yang jauh lebih cepat, memangkas tambahan **55.8% node** pada Depth 6.

---

### 2.3 Eksperimen 3: Tingkah Laku NPC Berdasarkan Fungsi Evaluasi

Dilakukan pengujian pada 3 skenario kondisi duel berbeda:

#### Skenario 1: Kondisi Awal / Netral ($HP_{\text{player}} = 100, HP_{\text{npc}} = 100$)
- **Balanced**: Memilih `HEAVY_ATTACK` (Skor: 0.0). Membuka inisiatif ofensif terukur.
- **Aggressive**: Memilih `HEAVY_ATTACK` (Skor: 48.0). Menekan lawan sedini mungkin.
- **Defensive**: Memilih `DEFEND` (Skor: 145.0). Mengutamakan menjaga keutuhan pertahanan sebelum melancarkan aksi berisiko.

#### Skenario 2: Kondisi Tertekan ($HP_{\text{player}} = 75, HP_{\text{npc}} = 25$)
- Ketiga fungsi evaluasi sepakat memilih `POTION`. Pada skenario ini, aksi serangan menghasilkan kekalahan terminal di kedalaman berikutnya (karena Player dapat membalas dan membunuh NPC). Dengan memilih `POTION`, NPC bertahan dari ancaman lethal.

#### Skenario 3: Kondisi Menang / Eksekusi ($HP_{\text{player}} = 20, HP_{\text{npc}} = 70$)
- Ketiga fungsi evaluasi sepakat memilih `HEAVY_ATTACK` dengan skor utility terminal $+1070.0$. NPC langsung mengeksekusi kemenangan secara instan tanpa membuang giliran.

---

### 2.4 Eksperimen 4: Analisis Expectimax (Stokastik & Probabilitas)
Pada varian ini, aksi `HEAVY_ATTACK` memiliki elemen peluang (*chance node*): $75\%$ akurasi mendarat (30 damage) dan $25\%$ meleset (0 damage).

| Aksi | Skor Deterministik (Alpha-Beta) | Skor Probabilistik (Expectimax) |
|:---|:---:|:---:|
| `ATTACK` (Pasti) | -46.0 | -14.25 |
| `HEAVY_ATTACK` (75% Chance) | **22.0** | **3.94** |
| `DEFEND` | -38.0 | -38.0 |
| `POTION` | -22.0 | -7.0 |

> **Analisis:**
> - Pada Expectimax, skor ekspektasi `HEAVY_ATTACK` terkoreksi turun dari $+22.0$ menjadi $+3.94$ akibat penalti 25% kemungkinan serangan meleset.
> - Meskipun terkoreksi, nilai ekspektasi mathematically still positive dan tetap menjadi aksi rasional terbaik bagi NPC pada kondisi tersebut.

---

## 3. Fitur Debug Overlay Duel
Antarmuka debug overlay di sebelah kiri diperluas dengan fitur interaktif:
1. **Dropdown Algoritma:** Memilih langsung antara *Alpha-Beta Pruning*, *Pure Minimax*, dan *Expectimax*.
2. **Dropdown Evaluasi:** Memilih gaya bermain NPC (*Balanced*, *Aggressive*, *Defensive*).
3. **Selector Kedalaman (Depth Limit):** Mengatur batas kedalaman pencarian secara dinamis (Depth 1 s/d 8).
4. **Toggle Move Ordering:** Menyalakan/mematikan optimasi urutan aksi untuk melihat perbandingan node count secara *real-time*.
5. **Live Action Scoring Table:** Menampilkan daftar nilai pertimbangan heuristik yang dihitung NPC untuk seluruh aksi legal (`ATTACK`, `HEAVY_ATTACK`, `DEFEND`, `POTION`) beserta aksi terpilih bertanda `▶`.
6. **Live Node Counters & Timing:** Menampilkan jumlah node yang dikunjungi, jumlah cabang yang di-prune, dan waktu berpikir AI dalam milidetik.
