# TEMPLATE & ACUAN PENYUSUNAN LAPORAN TUGAS BESAR AI (TAHAP 3 & 4)
## SISTEM CSP SOLVER & LOCAL SEARCH OPTIMIZATION UNTUK PENYEIMBANGAN SKUAD NPC ADAPTIF

> **Catatan Penggunaan Dokumen Ini:**  
> File ini dirancang sebagai **master reference / panduan komprehensif** bagi penyusun laporan (baik manusia maupun AI) untuk menyusun dokumen laporan akhir tugas besar mata kuliah Kecerdasan Buatan. Seluruh arsitektur teknis, formulasi matematis, pseudocode, mekanisme algoritma, dan hasil data eksperimen Tahap 3 (Local Search) dan Tahap 4 (CSP) tertuang secara lengkap di sini. Bagian algoritma pencarian jalur (UCS, A\*) dan duel adversarial (Minimax, Alpha-Beta, Expectimax) tidak diulang secara mendalam, melainkan difokuskan pada keterkaitannya dengan fitur baru, sistem item, dan engine optimasi skuad.

---

# BAGIAN I: IDENTITAS & METADATA PROYEK

- **Judul Proyek**: Implementasi Constraint Satisfaction Problem (CSP) dan Local Search Optimization untuk Dynamic Difficulty Adjustment (DDA) pada Game RPG Turn-Based "Bakekok"
- **Mata Kuliah**: Kecerdasan Buatan (Artificial Intelligence)
- **Program Studi**: Ilmu Komputer, Universitas Pendidikan Indonesia
- **Kelompok**: 7 (Tubes AI)
- **Anggota Kelompok**:
  1. **Muhammad Hanif Muyassar**
  2. **Moch Fadillah Pratama**
  3. **Muhammad Zidan Mirza Fedrieka**
- **Teknologi Utama**: Python 3.10+, Pygame-CE (Community Edition), Linear & Cubic Bezier Curve Rendering, Dynamic Difficulty Adjustment (DDA), Backtracking Search with MRV & LCV, Local Search Algorithms (Hill Climbing, Sideways Move, Random Restart, Simulated Annealing, Genetic Algorithm).

---

# BAGIAN II: LATAR BELAKANG & TUJUAN TAHAP 3 & 4

### 1. Permasalahan dalam Game RPG
Dalam game RPG berbasis giliran (*turn-based*), komposisi tim musuh (skuad NPC) yang statis atau diacak secara naif (*pure random*) menimbulkan dua kegagalan fatal:
1. **Ketidakseimbangan Aturan (*Illegal Configurations*)**: Komposisi acak dapat melanggar batas sumber daya dunia game, misalnya tim musuh dengan total HP yang tidak masuk akal, stok ramuan penyembuh tak terbatas, atau role karakter yang identik/monoton.
2. **Disonansi Tingkat Kesulitan (*Difficulty Mismatch*)**: Lawan bisa menjadi terlalu mudah sehingga memicu rasa bosan (*boredom*), atau terlalu sulit sehingga memicu rasa putus asa (*frustration*). Hal ini melanggar prinsip *Flow Theory* (Mihaly Csikszentmihalyi) yang menyatakan bahwa pengalaman bermain terbaik (*Fun Zone*) tercipta ketika tantangan seimbang dengan kemampuan pemain.

### 2. Solusi Dua Lapis (*Two-Tier AI Architecture*)
Untuk menyelesaikan masalah di atas, sistem memadukan dua paradigma AI secara sekuensial dan terintegrasi:
- **Lapis 1 - CSP Solver (Constraint Satisfaction Problem)**: Bertindak sebagai **filter legalitas formal apriori**. CSP memastikan bahwa setiap skuad NPC yang dibentuk mematuhi 8 batasan aturan baku dunia game ($C1 - C8$) menggunakan algoritma *Backtracking Search* yang dipercepat oleh heuristik *MRV*, *LCV*, *AC-3*, dan *Forward Checking*.
- **Lapis 2 - Local Search Optimizer**: Bertindak sebagai **penala tingkat kesulitan (*difficulty tuner*)**. Algoritma pencarian lokal (Hill Climbing, Sideways Move, Random Restart, Simulated Annealing, atau Genetic Algorithm) mengoptimasi parameter skuad legal dari CSP agar skor kesulitannya (*Difficulty Score*) tepat memenuhi target ideal ($\text{Target} \approx 0.55$) secara adaptif terhadap kondisi riil pemain.

---

# BAGIAN III: FITUR-FITUR GAMEPLAY TERPADU BARU

Sebelum masuk ke teknis matematis, sistem tahap ini mengintegrasikan serangkaian fitur gameplay baru yang saling bertaut dengan engine AI:

### 1. Sistem Item, Peti Karun & Mini-Game Gacha Roulette
- **Peti Karun Interaktif**: Terdapat 3 peti harta karun pada grid peta eksplorasi di koordinat `(6, 20)`, `(22, 10)`, dan `(32, 27)`.
- **Interaksi `[E]`**: Ketika Player berada pada jarak Manhattan $\le 1$ dari peti, pemain dapat menekan tombol `[E]`.
- **Mini-Game Gacha Roulette**: Membuka peti memicu animasi roulette selama 1.5 detik yang mengacak item sebelum menghadiahkan perlengkapan:
  - **Health Potion**: Menambah inventaris ramuan pemain secara persisten (+30 HP saat diminum dalam duel).
  - **Pedang Legendaris**: Memberikan bonus kekuatan serangan permanen ($+4 \text{ s/d } +6 \text{ ATK}$).
  - **Perisai Baja**: Memberikan bonus pertahanan permanen ($+2 \text{ s/d } +4 \text{ DEF}$).
- **Status Persisten**: HP, jumlah ramuan, dan buff perlengkapan pemain tersimpan secara persisten dari penjelajahan peta hingga ke arena pertempuran.

### 2. 3 Karakter NPC di Peta Eksplorasi
Peta dunia dihuni oleh 3 agen NPC kucing dengan perilaku berbeda:
- **Oyen (Kucing Oranye)**: Agen pengejar (*chaser*) yang melacak dan memburu posisi Player menggunakan algoritma pencarian jalur ($A^*$ / UCS) saat dipanggil (`[Spasi]`).
- **Kuro (Kucing Hitam)**: Agen penjaga yang berpatroli secara mandiri melintasi 4 titik *waypoint* di kawasan barat dan utara peta.
- **Shiro (Kucing Putih/Silver)**: Agen patroli yang menjelajahi rute *waypoint* kawasan timur dan selatan peta.
- **Fitur Tambahan**: Penerapan *palette swapping* prosedural (`tint_color`) dan indikator radar tepi layar (*offscreen pulsing indicator*) yang memandu arah posisi NPC di luar pandangan kamera.

### 3. Fase Pre-Battle & Transisi Adaptif
- **Pemicu Duel**: Terjadi otomatis saat jarak Manhattan antara Player dan NPC $\le 1$, atau melalui tombol pintas `[B]`.
- **Fase Pre-Battle**: Sebelum duel turn-based dimulai, game memasuki layar persiapan taktis. Di balik layar, sistem mengeksekusi CSP Solver dan Local Search terpilih untuk membentuk skuad musuh yang siap bertarung.
- **Interaksi Pemain di Pre-Battle**:
  - Tombol `[1 - 5]`: Memilih algoritma Local Search yang ingin digunakan (1: Simple HC, 2: Sideways HC, 3: Random Restart, 4: Simulated Annealing, 5: Genetic Algorithm).
  - Tombol `[R]`: Mengacak ulang (*reroll*) komposisi skuad musuh secara instan.
  - Tombol `[T]` / Klik Tombol Inspeksi: Membuka **Modal Visualizer AI Fullscreen** untuk meninjau pohon keputusan CSP dan grafik trajektori optimasi.
  - Tombol `[Spasi]` / `[Enter]`: Memulai duel pertempuran.

### 4. Arena Pertarungan Tag-Team 1 vs 1 Skuad
- **Format Tag-Team**: Player bertarung satu lawan satu melawan anggota *frontline* aktif dari skuad NPC musuh.
- **Rotasi Bench Otomatis**: Jika frontline musuh tumbang dan antrean cadangan (*bench*) masih tersedia, anggota skuad berikutnya otomatis maju ke arena dengan HP penuh.
- **Indikator Status Skuad**: Status anggota skuad ditampilkan transparan di layar dengan lencana:
  - `[BERTARUNG ⚔️]`: Karakter yang sedang aktif bertarung di arena.
  - `[CADANGAN (HP)]`: Karakter cadangan yang bersiap di bangku cadangan.
  - `[GUGUR ✕]`: Karakter yang telah dikalahkan.

### 5. Efek Visual Pertarungan Prosedural (Tweening VFX)
Animasi pertarungan di-render secara dinamis menggunakan interpolasi matematis (*lerp tweening*) tanpa dependensi aset sprite eksternal:
- **Aksi Serang (Attack & Heavy Attack)**: Sprite pedang meluncur cepat dari penyerang ke target disertai rotasi sudut dan getaran layar (*hit shake*).
- **Aksi Bertahan (Defend)**: Sprite perisai melayang di depan karakter dengan denyut transparansi (*alpha pulsing glow*).
- **Aksi Ramuan (Potion)**: Botol ramuan melayang dan miring menuangkan cairan di atas kepala karakter, disertai teks pemulihan melayang (`+30 HP`).

### 6. Modal Fullscreen AI Visualizer (`[T]`)
Antarmuka inspeksi edukatif berkecepatan 60 FPS dengan latar belakang blur halus (*dual-scale Gaussian simulation*):
- **Tab 1: Pohon Keputusan CSP (Backtracking & Pruning)**:
  - Penataan pohon horizontal dari kiri ke kanan dengan kurva Bezier kubik mulus.
  - Kotak simpul informatif 3 baris: Variabel & Nilai, Lencana Status, dan Alasan Keputusan Konsistensi.
  - Sidebar Kanan Interaktif: Pinned Header, Card 1 (Formulasi), Card 2 (Kamus Simpul), Card 3 (Analisis Langkah Lengkap dengan penjelasan Mengapa Dipilih vs Mengapa Di-prune), serta fitur *scrollable* menggunakan mouse wheel / dua jari touchpad.
  - Tombol Popup `[?] C1-C8`: Dialog panduan ringkas seluruh aturan batasan formal CSP.
- **Tab 2: Trajectory Local Search & Konvergensi**:
  - Grafik 2D interaktif yang memplot nilai *Difficulty* dan *Fitness* terhadap langkah iterasi.
  - Garis target ideal 0.55 (*Fun Zone*).
  - Penanda titik event khusus: *Ascent (Improve)*, *Sideways Move*, *Local Maximum*, *Plateau Stop*, dan *SA Accept Worse*.
  - Pratinjau skuad live yang berubah secara *real-time* seiring timeline animasi scrubber digerakkan.

---

# BAGIAN IV: FORMULASI & CARA KERJA CONSTRAINT SATISFACTION PROBLEM (CSP)

Modul implementasi: `game/npc_config_csp.py`

### 1. Definisi Formal CSP: Triplet $\langle X, D, C \rangle$

Sesuai literatur Russell & Norvig (*Artificial Intelligence: A Modern Approach*), masalah penentuan komposisi tim musuh dirumuskan secara formal sebagai triplet $\langle X, D, C \rangle$:

#### A. Himpunan Variabel ($X$)
Untuk skuad dengan $k$ anggota ($k \in \{1, 2, 3\}$), terdapat 6 variabel per karakter ditambah 1 variabel ukuran tim:
$$X = \{ \text{npc\_count} \} \cup \bigcup_{i=0}^{k-1} \{ \text{char\_type}_i, \text{hp}_i, \text{potions}_i, \text{atk\_bonus}_i, \text{def\_bonus}_i, \text{eval\_profile}_i \}$$
Total variabel untuk skuad 3 NPC adalah **19 variabel**.

#### B. Himpunan Domain Diskrit Legal ($D$)
- $D(\text{npc\_count}) = \{1, 2, 3\}$
- $D(\text{char\_type}_i) = \{\text{"warrior"}, \text{"tank"}, \text{"ranger"}, \text{"assassin"}, \text{"mage"}\}$
- $D(\text{hp}_i) = \{70, 80, 90, 100, 110, 120\}$
- $D(\text{potions}_i) = \{0, 1, 2, 3\}$
- $D(\text{atk\_bonus}_i) = \{0, 5, 10, 15\}$
- $D(\text{def\_bonus}_i) = \{0, 2, 4, 6\}$
- $D(\text{eval\_profile}_i) = \{\text{"BALANCED"}, \text{"AGGRESSIVE"}, \text{"DEFENSIVE"}\}$

#### C. Himpunan Batasan Formal ($C = \{C1, C2, \dots, C8\}$)
Aturan batasan mengikat relasi unary (satu variabel) dan n-ary (lintas variabel dan skuad):
1. **$C1$ (Budget Total HP Tim)**: Total HP kumulatif seluruh anggota skuad tidak boleh melampaui batas anggaran dunia game:
   $$\sum_{i=0}^{k-1} \text{hp}_i \le \text{Budget}_{\text{HP}} \quad (\text{default: } 200 \text{ s/d } 250)$$
2. **$C2$ (Budget Total Ramuan Tim)**: Total kuota ramuan skuad dibatasi agar musuh tidak melakukan penyembuhan berlebihan:
   $$\sum_{i=0}^{k-1} \text{potions}_i \le \text{Budget}_{\text{Potions}} \quad (\text{default: } 2 \text{ s/d } 5)$$
3. **$C3$ (Syarat Karakter Tank - Daya Tahan)**: Karakter bertipe *Tank* wajib memiliki fisik yang tebal untuk menyerap serangan:
   $$\text{char\_type}_i = \text{"tank"} \implies \text{hp}_i \ge 90$$
4. **$C4$ (Syarat Karakter Ranger - Jangkauan Serang)**: Karakter *Ranger* wajib memiliki spesialisasi bonus serangan fisik:
   $$\text{char\_type}_i = \text{"ranger"} \implies \text{atk\_bonus}_i \ge 5$$
5. **$C5$ (Keunikan Role/Kelas Skuad - AllDifferent)**: Jika skuad terdiri dari 2 atau lebih NPC, tidak boleh ada kelas karakter yang kembar/duplikat (menjamin variasi taktik tim):
   $$k \ge 2 \implies \text{AllDifferent}(\text{char\_type}_0, \text{char\_type}_1, \dots, \text{char\_type}_{k-1})$$
6. **$C6$ (Mage Glass Cannon & AI Ofensif)**: Karakter *Mage* memiliki daya tahan fisik rendah namun berorientasi serangan sihir agresif:
   $$\text{char\_type}_i = \text{"mage"} \implies (\text{hp}_i \le 90) \land (\text{eval\_profile}_i \in \{\text{"BALANCED"}, \text{"AGGRESSIVE"}\})$$
7. **$C7$ (Tank Guard & AI Defensif)**: Karakter *Tank* berorientasi pada penjagaan garis depan dan perlindungan tim:
   $$\text{char\_type}_i = \text{"tank"} \implies \text{eval\_profile}_i \in \{\text{"BALANCED"}, \text{"DEFENSIVE"}\}$$
8. **$C8$ (Spesialisasi Assassin & Budget Total ATK)**: Karakter *Assassin* memiliki serangan mematikan, tubuh ramping, dan agresif; serta total bonus serangan skuad dibatasi:
   $$\text{char\_type}_i = \text{"assassin"} \implies (\text{atk\_bonus}_i \ge 10) \land (\text{hp}_i \le 90) \land (\text{eval\_profile}_i \in \{\text{"BALANCED"}, \text{"AGGRESSIVE"}\})$$
   $$\sum_{i=0}^{k-1} \text{atk\_bonus}_i \le \text{Budget}_{\text{ATK}} \quad (\text{default: } 12 \text{ s/d } 25)$$

---

### 2. Alur Algoritma Penyelesaian CSP

```
Inisialisasi Masalah CSP
        │
        ▼
[Langkah 1: AC-3 Filtering] ──► Pangkas nilai domain apriori yang mustahil
        │
        ▼
[Langkah 2: Cek Kelengkapan] ──► Apakah semua variabel terisi? ──► [YA] ──► SOLUSI DITEMUKAN
        │ [TIDAK]
        ▼
[Langkah 3: Heuristik MRV] ──► Pilih variabel X dengan |Domain(X)| terkecil (fail-first)
        │
        ▼
[Langkah 4: Heuristik LCV] ──► Urutkan nilai v dalam Domain(X) berdasarkan konflik terendah
        │
        ▼
[Langkah 5: Forward Checking]
   ├── Nilai v melanggar C1-C8? ──► [YA] ──► PANGKAS (PRUNED) ──► Coba nilai berikutnya
   │
   └── [KONSISTEN] ──► Assign X = v ──► Rekursif ke Langkah 2
                              │
                              └── Cabang bawah gagal semua? ──► BACKTRACK (Undo Assignment)
```

#### A. Penyaringan Awal: AC-3 Unary Domain Filtering
Sebelum pencarian mendalam dimulai, fungsi `apply_ac3_unary()` memvalidasi domain terhadap batasan unary statis. Nilai yang mustahil sejak awal dipangkas apriori, mengurangi ukuran pohon pencarian secara drastis dalam waktu $< 0.01$ milidetik.

#### B. Pemilihan Variabel: Minimum Remaining Values (MRV / Fail-First Principle)
Fungsi `select_unassigned_variable_mrv(assignment, domains)` memilih variabel yang belum terisi dengan jumlah nilai legal tersisa paling sedikit:
$$\text{Var}^* = \arg\min_{X_j \notin \text{assigned}} |D(X_j)|$$
*Tujuan Teoretis*: Menetapkan variabel yang paling ketat terlebih dahulu. Jika suatu cabang ditakdirkan gagal, kegagalan akan terdeteksi di level atas pohon (*prune early*), menghindari ekspansi jutaan cabang sia-sia di level bawah.

#### C. Pengurutan Nilai: Least Constraining Value (LCV)
Fungsi `order_domain_values_lcv(var, assignment, domains)` mengurutkan nilai domain $v \in D(\text{Var}^*)$ berdasarkan jumlah nilai yang disingkirkan pada domain variabel tetangga lainnya:
$$v^* = \arg\min_{v} \sum_{Y \in \text{Neighbors}} \text{count\_conflicts}(Y, v)$$
*Tujuan Teoretis*: Memaksimalkan fleksibilitas variabel masa depan. Nilai yang paling ramah dan menimbulkan 0 konflik dicoba terlebih dahulu agar solusi legal pertama dapat ditemukan secepat mungkin.

#### D. Pemangkasan Proaktif: Forward Checking
Setiap kali nilai $v$ diuji pada variabel $X$, sistem mengevaluasi batasan parsial terhadap variabel yang telah terisi. Jika nilai tersebut melanggar batasan anggaran (misal: $\text{Total HP} > 200$) atau aturan keunikan role ($C5$), simpul tersebut langsung diberi status **`PRUNED`** dan dipotong tanpa membuat sub-cabang di bawahnya.

#### E. Pemulihan Jalan Buntu: Backtracking
Jika seluruh nilai domain pada suatu variabel mengalami *pruning* (*domain wipeout*), simpul tersebut dinyatakan sebagai **`BACKTRACK`** (*dead-end*). Sistem membatalkan penugasan terakhir (*undo assignment*), mengembalikan nilai domain, dan mundur ke simpul induk untuk mencoba cabang alternatif.

---

# BAGIAN V: FORMULASI & CARA KERJA LOCAL SEARCH OPTIMIZATION

Modul implementasi: `game/difficulty.py` dan `game/npc_config_optimizer.py`

### 1. Formulasi Matematika Fungsi Objektif Kesulitan (*Difficulty Evaluator*)

Tingkat kesulitan skuad NPC tidak ditentukan secara subjektif, melainkan melalui formulasi multikriteria berbobot 6 dimensi pada `game/difficulty.py`:

$$\text{Difficulty Score} = \sum_{j \in \{\text{hp, pot, atk, def, count, aggro}\}} w_j \cdot \overline{\text{Metric}}_j$$

Dengan vektor bobot baku ($\sum w_j = 1.0$):
- $w_{\text{hp}} = 0.25$: Bobot total daya tahan darah skuad musuh.
- $w_{\text{pot}} = 0.15$: Bobot cadangan pemulihan ramuan instan tim.
- $w_{\text{atk}} = 0.20$: Bobot kekuatan bonus serangan ofensif.
- $w_{\text{def}} = 0.10$: Bobot proteksi pengurangan damage perisai.
- $w_{\text{count}} = 0.20$: Bobot kuantitas petarung musuh di medan laga.
- $w_{\text{aggro}} = 0.10$: Bobot profil keagresifan AI pertempuran.

#### Formula Normalisasi Nilai Metrik ($\overline{\text{Metric}}_j \in [0.0, 1.0]$)
Setiap dimensi dinormalisasi terhadap nilai maksimum teoretis dunia game:
$$\overline{\text{HP}} = \min\left(1.0, \frac{\sum \text{hp}_i}{3 \times 120}\right) = \min\left(1.0, \frac{\sum \text{hp}_i}{360}\right)$$
$$\overline{\text{Pot}} = \min\left(1.0, \frac{\sum \text{potions}_i}{3 \times 3}\right) = \min\left(1.0, \frac{\sum \text{potions}_i}{9}\right)$$
$$\overline{\text{Atk}} = \min\left(1.0, \frac{\sum \text{atk\_bonus}_i}{3 \times 15}\right) = \min\left(1.0, \frac{\sum \text{atk\_bonus}_i}{45}\right)$$
$$\overline{\text{Def}} = \min\left(1.0, \frac{\sum \text{def\_bonus}_i}{3 \times 6}\right) = \min\left(1.0, \frac{\sum \text{def\_bonus}_i}{18}\right)$$
$$\overline{\text{Count}} = \min\left(1.0, \frac{k}{3.0}\right)$$
$$\overline{\text{Aggro}} = \frac{1}{k} \sum_{i=0}^{k-1} \text{ProfileWeight}(\text{eval\_profile}_i)$$

Di mana bobot profil AI adalah:
$$\text{ProfileWeight}(\text{eval\_profile}) = \begin{cases} 
1.0, & \text{jika } \text{"AGGRESSIVE"} \\
0.5, & \text{jika } \text{"BALANCED"} \\
0.2, & \text{jika } \text{"DEFENSIVE"}
\end{cases}$$

---

### 2. Formulasi Fungsi Fitness (*Fitness Function*)

Tujuan Local Search adalah meminimalkan deviasi antara kesulitan skuad terhadap target ideal:
$$\text{Fitness}(\text{State}) = - \left| \text{Difficulty}(\text{State}) - \text{Target Difficulty} \right|$$

- **Rentang Nilai**: $[-\text{Target}, 0.0]$.
- **Nilai Global Optimum**: $\text{Fitness} = 0.0$ (tercapai ketika kesulitan skuad persis sama dengan target).
- **Target Baku (*Fun Zone*)**: $\text{Target} = 0.55$.

---

### 3. Dynamic Player Context Balancing (Penyesuaian Adaptif)

Sistem tidak mengunci target kesulitan pada angka statis, melainkan memodulasinya secara dinamis berdasarkan kondisi riil pemain saat bersua musuh di peta eksplorasi (`get_adaptive_target_difficulty`):

$$\text{Target Adaptif} = \text{clamp}\left(0.40, 0.70, 0.55 + \Delta_{\text{HP}} + \Delta_{\text{Buff}}\right)$$

Di mana:
$$\Delta_{\text{HP}} = \frac{\text{HP}_{\text{player}} - 100}{250.0}$$
$$\Delta_{\text{Buff}} = \frac{\text{Atk}_{\text{player\_bonus}} + \text{Def}_{\text{player\_bonus}}}{100.0}$$

#### Skenario Penyesuaian Adaptif:
1. **Pemain Kritis / Sekarat** ($\text{HP}=35$, tanpa potion): $\Delta_{\text{HP}} = -0.26$, target turun ke batas bawah $\approx 0.40$. Musuh otomatis di-nerf (jumlah anggota berkurang menjadi 2, profil AI lebih defensif) agar pemain tidak langsung tewas.
2. **Pemain Normal / Bugar** ($\text{HP}=100$, ramuan standar): $\text{Target} = 0.55$ (standar *Fun Zone* seimbang).
3. **Pemain Kuat / Berperlengkapan Peti** ($\text{HP}=100, \text{ATK}=+6, \text{DEF}=+4$): $\Delta_{\text{Buff}} = +0.10$, target naik ke $\approx 0.65 - 0.70$. Musuh otomatis di-buff (3 NPC, stat tinggi, profil AI agresif) untuk memberikan tantangan proporsional.

---

### 4. Mekanisme Pembangkit Tetangga Legal (*Legal Neighbour Generator*)

Fungsi `generate_legal_neighbours(state)` memodifikasi state saat ini melalui operator mutasi 1-langkah:
- Mutasi HP: $\text{HP}_i \pm 10$ atau $\pm 20$.
- Mutasi Potion: $\text{Potions}_i \pm 1$.
- Mutasi Bonus Serangan: $\text{ATK}_i \in D(\text{atk\_bonus})$.
- Mutasi Bonus Pertahanan: $\text{DEF}_i \in D(\text{def\_bonus})$.
- Mutasi Profil AI: $\text{eval\_profile}_i \in \{\text{BALANCED}, \text{AGGRESSIVE}, \text{DEFENSIVE}\}$.
- Mutasi Role Karakter: $\text{char\_type}_i \in D(\text{char\_type})$.

> **Garansi 100% Legalitas**: Setiap kandidat mutasi langsung diuji silang oleh `self.csp.validate_config(cand)[0]`. Jika kandidat melanggar salah satu aturan $C1 - C8$, kandidat langsung dibuang. Hanya tetangga yang 100% patuh aturan CSP yang dimasukkan ke dalam daftar suksesor.

---

### 5. Cara Kerja 5 Algoritma Local Search yang Diimplementasikan

#### 1. Simple Hill Climbing (Steepest Ascent)
- **Mekanisme**: Mengevaluasi seluruh himpunan tetangga legal. Memilih tetangga dengan nilai fitness tertinggi yang lebih besar dari state saat ini ($f(s') > f(s)$).
- **Terminasi**: Berhenti seketika saat tidak ada lagi tetangga yang memiliki fitness lebih tinggi (*Local Maximum*).
- **Kelemahan**: Rentan terjebak pada puncak lokal (*local optimum*) atau lereng datar (*plateau*).

#### 2. Hill Climbing with Sideways Move
- **Mekanisme**: Memperbolehkan langkah mendatar ($f(s') = f(s)$) ketika tidak ada suksesor yang lebih baik, dengan batas toleransi maksimal **15 langkah berturut-turut** (`max_sideways = 15`).
- **Terminasi**: Berhenti saat menemukan perbaikan lebih tinggi, atau saat batas 15 langkah sideways terlampaui tanpa ada kenaikan (*Plateau Stop*).
- **Kelebihan**: Berhasil melintasi dataran tinggi (*plateau*) dan bahu bukit (*shoulder*), mencapai fitness optimal dengan waktu eksekusi tercepat.

#### 3. Random Restart Hill Climbing
- **Mekanisme**: Menjalankan siklus Hill Climbing secara berulang (default: 5 iterasi restart). Pada setiap restart, state awal diacak ulang menggunakan solusi legal baru dari CSP Solver.
- **Terminasi**: Menyimpan konfigurasi terbaik global dari seluruh siklus restart.
- **Kelebihan**: Bersifat *complete* secara probabilitas; mampu melompat dari jebakan puncak lokal yang buruk menuju puncak global.

#### 4. Simulated Annealing (SA)
- **Mekanisme**: Terinspirasi dari proses pendinginan logam. Mengadopsi jadwal pendinginan temperatur eksponensial:
  $$T_k = T_0 \cdot \alpha^k \quad (T_0 = 1.0, \, \alpha = 0.92, \, T_{\min} = 0.001)$$
  - Jika tetangga acak $s'$ lebih baik ($\Delta E = f(s') - f(s) > 0$), langkah selalu diterima.
  - Jika tetangga $s'$ lebih buruk ($\Delta E \le 0$), langkah diterima dengan probabilitas Boltzmann:
    $$P(\text{Accept}) = \exp\left(\frac{\Delta E}{T}\right)$$
- **Kelebihan**: Pada temperatur tinggi ($T$ besar), agen bebas melompat keluar dari lembah lokal. Pada temperatur rendah ($T$ mendekati 0), agen menstabilkan diri pada puncak terbaik.

#### 5. Genetic Algorithm (GA)
- **Mekanisme**: Berbasis komputasi evolusioner populasi:
  1. **Inisialisasi**: Membangkitkan populasi berukuran 12 individu legal dari CSP Solver.
  2. **Seleksi Turnamen**: Memilih calon induk terbaik melalui turnamen k-way ($k=3$).
  3. **Pindah Silang (*Crossover*)**: Menggabungkan kromosom anggota tim dari dua induk pada titik potong acak.
  4. **Mutasi Genetik**: Menerapkan laju mutasi 15% pada atribut stat/role individu anak dengan tetap mematuhi validator CSP.
  5. **Generasi**: Berjalan selama 30 generasi untuk mengkonvergensikan seluruh populasi menuju target kesulitan.
- **Kelebihan**: Melakukan pencarian paralel berbasis populasi (*beam-like diversity*), sangat tangguh terhadap lanskap fungsi objektif multimodus.

---

# BAGIAN VI: HASIL EKSPERIMEN, DATA PENGUJIAN & ANALISIS

Data berikut diperoleh secara empiris melalui skrip benchmark otomatis `scratch/run_tahap3_experiments.py`:

### 1. Eksperimen 1: Kinerja CSP Solver (AC-3 + Backtracking + MRV + LCV)

| Parameter / Metrik Evaluasi | Nilai Observasi | Keterangan Ilmiah |
|:---|:---:|:---|
| **Waktu Eksekusi AC-3 Unary Filtering** | **0.005 ms** | Pemangkasan apriori berlangsung instan sub-milidetik |
| **Domain Pruned via AC-3** | 0 nilai | Domain variabel telah terstruktur rapi sejak definisi |
| **Waktu Solve Skuad 2 NPC** | **0.175 ms** | Backtracking + MRV + LCV menemukan solusi legal pertama |
| **Waktu Solve Skuad 3 NPC** | **0.299 ms** | Menemukan konfigurasi 18 variabel legal dalam $< 0.3$ ms |
| **Kepatuhan Constraint C1 - C8** | **100% Valid (0 Violations)** | Seluruh solusi memenuhi batasan budget dan keunikan role |
| **Komposisi Default Terbentuk** | Warrior + Tank + Assassin | Role unik, sinergi kelas seimbang (C5 terpenuhi) |

> **Analisis CSP**: Kombinasi heuristik MRV (memilih variabel paling restriktif) dan LCV (memilih nilai dengan potensi konflik minimal) berhasil menekan angka *backtrack* hingga mendekati nol pada pencarian awal, memungkinkan pembuatan skuad musuh secara instan tanpa menurunkan frame rate game.

---

### 2. Eksperimen 2: Perbandingan Komparatif 5 Algoritma Local Search

Pengujian dijalankan dengan Target Difficulty = $0.55$ (*Fun Zone*), masing-masing diulang 5 kali percobaan independen:

| Algoritma Local Search | Waktu Komputasi (ms) | Rata-rata Iterasi/Gen | Final Fitness | Difficulty Dicapai | Deviasi (|Diff - 0.55|) | Kepatuhan CSP |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Hill Climbing (Simple)** | 3.93 ms | 5.0 | -0.0028 | 0.5528 | 0.0028 | **100% Valid** |
| **HC with Sideways Move** | **2.84 ms** | 5.0 | -0.0028 | 0.5528 | 0.0028 | **100% Valid** |
| **Random Restart HC** | 11.98 ms | 5.6 (per run) | **-0.0016** | **0.5516** | **0.0016** | **100% Valid** |
| **Simulated Annealing** | 29.97 ms | 136.0 | -0.0072 | 0.5572 | 0.0072 | **100% Valid** |
| **Genetic Algorithm** | 65.30 ms | 30.0 generasi | -0.0025 | 0.5480 | 0.0020 | **100% Valid** |

> **Analisis Komparatif Algoritma**:
> 1. **Akurasi Terbaik**: **Random Restart HC** meraih nilai fitness tertinggi ($-0.0016$) dengan kesulitan akhir $0.5516$, karena mengeksplorasi beberapa cekungan atraksi berbeda.
> 2. **Kecepatan Terbaik**: **HC with Sideways Move** mencatat waktu tercepat (**2.84 ms**), menjadikannya algoritma paling efisien untuk penyeimbangan *real-time* saat transisi Pre-Battle.
> 3. **Eksplorasi Stokastik**: **Simulated Annealing** membutuhkan 136 iterasi pendinginan temperatur dengan waktu 29.97 ms, berhasil menghindari jebakan lokal dengan baik.
> 4. **Integritas Aturan**: Seluruh 5 algoritma mencatat **100% kepatuhan CSP (0 pelanggaran)**, membuktikan efektivitas fungsi `generate_legal_neighbours()` sebagai penjamin legalitas.

---

### 3. Eksperimen 3: Uji Adaptabilitas Dinamis Skuad terhadap Status Pemain

Pengujian modul `get_adaptive_target_difficulty` untuk mengamati respon adaptif skuad terhadap kondisi riil pemain:

| Skenario Status Pemain | HP Player | Buff Peralatan | Target Diff Adaptif | Difficulty Teroptimasi | Komposisi Skuad Terbentuk | Total HP Skuad | Respon Sistem AI |
|:---|:---:|:---:|:---:|:---:|:---|:---:|:---|
| **Skenario A: Pemain Bugar** | 100 | Atk +0, Def +0 | **0.5500** | **0.5528** | `Warrior(BAL) + Tank(BAL) + Assassin(BAL)` | 220 HP | Standar seimbang *Fun Zone* |
| **Skenario B: Pemain Sekarat** | 35 | Atk +0, Def +0 | **0.4000** | **0.3986** | `Warrior(BAL) + Tank(BAL)` (2 Anggota) | 150 HP | **Nerf Adaptif**: Jumlah musuh berkurang, HP dipangkas |
| **Skenario C: Pemain Buff Peti** | 100 | Atk +6, Def +4 | **0.6500** | **0.6472** | `Warrior(BAL) + Tank(BAL) + Assassin(AGG)` | 220 HP | **Buff Adaptif**: AI menjadi Agresif, stat ditingkatkan |

> **Kesimpulan Adaptabilitas**: Sistem berhasil merealisasikan *Dynamic Difficulty Adjustment (DDA)* secara mulus: permainan secara otomatis memberikan kelonggaran saat pemain terdesak dan meningkatkan intensitas perlawanan saat pemain berada dalam kondisi prima.

---

# BAGIAN VII: STRUKTUR STANDAR PENYUSUNAN LAPORAN AKADEMIS

Bagi AI atau penulis yang menyusun laporan formal berdasarkan dokumen ini, gunakan struktur bab dan poin pembahasan berikut:

```
COVER LAPORAN (Judul, Logo UPI, Kelompok 7, Nama Anggota, Prodi Ilmu Komputer)
KATA PENGANTAR & DAFTAR ISI

BAB I: PENDAHULUAN
  1.1 Latar Belakang (Pentingnya Dynamic Difficulty Adjustment & Penyeimbangan RPG)
  1.2 Rumusan Masalah (Bagaimana merancang komposisi skuad legal dan seimbang?)
  1.3 Tujuan Pengembangan (Implementasi CSP & 5 Algoritma Local Search)
  1.4 Batasan Masalah (Fokus pada Pre-Battle Optimization Tahap 3 & 4)

BAB II: LANDASAN TEORI
  2.1 Konsep Constraint Satisfaction Problem (CSP, X, D, C, Backtracking, MRV, LCV, AC-3)
  2.2 Konsep Local Search Optimization (Hill Climbing, Sideways, Random Restart, SA, GA)
  2.3 Teori Aliran Permainan (Flow Theory & Fun Zone 0.55)
  2.4 Dynamic Player Context Balancing

BAB III: PERANCANGAN & IMPLEMENTASI SISTEM
  3.1 Arsitektur Perangkat Lunak (Struktur Modul Game-AI)
  3.2 Perancangan Fitur Gameplay Baru (Peti Karun Gacha, 3 NPC, Tag-Team Battle, Tweening VFX)
  3.3 Implementasi CSP Solver (Formulasi X, D, C1-C8, Alur Backtracking & Forward Checking)
  3.4 Implementasi Local Search (Fungsi Objektif Kesulitan, Fitness, dan 5 Algoritma)
  3.5 Antarmuka Visualizer Pre-Battle (Pohon CSP Bezier, Pinned Sidebar, Popup Aturan [?] C1-C8, Grafik 2D)

BAB IV: HASIL PENGUJIAN DAN PEMBAHASAN
  4.1 Pengujian Kinerja CSP Solver (Tabel Waktu Eksekusi & Validitas C1-C8)
  4.2 Pengujian Komparatif 5 Algoritma Local Search (Tabel Waktu, Iterasi, Fitness, Difficulty)
  4.3 Pengujian Adaptabilitas Dinamis terhadap Kondisi Pemain (Skenario Bugar, Sekarat, Buff)
  4.4 Pembahasan & Analisis Kritis (Kelebihan, Kekurangan, dan Trade-off masing-masing algoritma)

BAB V: KESIMPULAN DAN SARAN
  5.1 Kesimpulan (Keberhasilan integrasi CSP + Local Search menjamin legalitas dan keadilan game)
  5.2 Saran Pengembangan Masa Depan (Eksplorasi Reinforcement Learning atau multi-agent squad cooperation)

DAFTAR PUSTAKA
LAMPIRAN (Tangkapan Layar Permainan, Potongan Kode Kunci, Log Eksperimen)
```

---

# BAGIAN VIII: PROMPT INSTRUKSI SIAP PAKAI UNTUK AI PENULIS LAPORAN

Jika dokumen ini ingin diberikan ke AI lain (misal Claude, ChatGPT, atau model lain) untuk langsung menghasilkan naskah laporan lengkap, sertakan prompt pengantar berikut:

```text
"Halo! Tolong buatkan naskah laporan akademis formal yang lengkap, mendalam, dan terstruktur rapi untuk Tugas Besar Mata Kuliah Kecerdasan Buatan (Tahap 3 & 4: Local Search & CSP) berdasarkan seluruh data teknis, formulasi matematika, fitur gameplay, dan hasil eksperimen yang ada di dalam dokumen 'template_laporan.md' ini.

Panduan Penulisan:
1. Ikuti struktur Bab I sampai Bab V sesuai panduan di Bagian VII.
2. Gunakan gaya bahasa formal akademis Indonesia yang baku, profesional, dan objektif.
3. Tuliskan seluruh formulasi matematika (triplet CSP, rumus normalisasi bobot difficulty, rumus fitness, jadwal pendinginan SA, rumus adaptif) menggunakan format LaTeX yang rapi.
4. Sertakan seluruh tabel pengujian eksperimen yang ada di Bagian VI tanpa menghilangkan data numerik sedikit pun.
5. Uraikan penjelasan cara kerja CSP (MRV, LCV, Forward Checking, Backtrack, C1-C8) dan 5 algoritma Local Search secara komprehensif.
6. Jangan menyalin mentah-mentah dalam bentuk poin pendek, melainkan kembangkan menjadi paragraf-paragraf penjelasan ilmiah yang mengalir dan runtut."
```
