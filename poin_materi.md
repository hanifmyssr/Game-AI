# 📚 Poin Materi AI (Local Search & CSP) dan Analisis Implementasi Game

Dokumen ini memetakan seluruh poin penting dari materi kuliah **Local Search & Optimization** dan **Constraint Satisfaction Problem (CSP)** yang wajib diimplementasikan pada **Tubes Tahap 3**, serta menyajikan hasil audit mendalam terhadap kondisi kode proyek saat ini.

---

## 🎯 Bagian 1: Poin-Poin Penting Materi Kuliah

Berdasarkan modul slide perkuliahan:
1. **Local Search & Optimization** (Slide 1–23)
2. **Constraint Satisfaction Problem (CSP)** (Slide 1–46)
3. **Spesifikasi Khusus Tubes Tahap 3** (Slide 22 & Slide 46)

### A. Konsep Dasar & Perbedaan Paradigma
| Aspek | Pathfinding (Informed Search / A*) | Local Search & Optimization | Constraint Satisfaction Problem (CSP) |
|---|---|---|---|
| **Fokus Solusi** | Jalur/urutan aksi dari *start* menuju *goal* | Konfigurasi optimal state akhir (*path* tidak penting) | Konfigurasi legal lengkap (*complete & consistent*) |
| **Kebutuhan Memori** | $O(b^d)$ (memerlukan *frontier* & *explored set*) | **$O(1)$ konstan** (hanya menyimpan *current state*) | $O(d \cdot n)$ pada depth-first backtracking |
| **Karakter Masalah** | Navigasi peta, labirin, rute | Optimasi parameter, penjadwalan, penyeimbangan game | Pewarnaan peta, alokasi sumber daya dengan aturan ketat |

---

### B. Materi 1: Local Search & Optimization
Tujuan utama: Mencari konfigurasi state dengan nilai objektif/fitness terbaik di ruang pencarian tanpa mempedulikan langkah historisnya.

1. **Hill Climbing (Steepest Ascent)**:
   - Evaluasi seluruh tetangga 1-langkah (*immediate neighbours*).
   - Berpindah ke tetangga dengan nilai evaluasi tertinggi ($highest\text{-}valued\ successor$).
   - Berhenti jika tidak ada tetangga yang memiliki nilai strictly lebih baik daripada state saat ini.
2. **Identifikasi Tiga Failure Modes**:
   - **Local Maximum**: Puncak lokal yang lebih tinggi dari seluruh tetangga di sekitarnya, tetapi bukan solusi global terbaik.
   - **Plateau / Shoulder**: Area datar dengan gradien nol di mana semua tetangga memiliki nilai yang sama (tidak ada arah mendaki).
   - **Ridge**: Lereng punggung bukit di mana arah perbaikan ada tetapi membutuhkan kombinasi langkah berurutan yang harus melewati penurunan nilai terlebih dahulu.
3. **Solusi Mengatasi Failure Modes**:
   - **Sideways Move**: Memperbolehkan perpindahan ke tetangga dengan nilai yang sama untuk menyeberangi *plateau* atau *shoulder* (dengan batasan jumlah langkah sideways maksimal agar tidak terjadi *infinite loop*).
   - **Random Restart**: Jika pencarian terjebak di local optimum, lakukan restart dari *seed* atau state awal acak baru hingga menemukan solusi optimal.
   - **Simulated Annealing (SA)**:
     - Mengizinkan gerakan memperburuk nilai (*downhill*) dengan probabilitas Boltzmann:
       $$P(\text{accept downhill}) = e^{\Delta E / T}$$
     - Di mana $\Delta E = \text{VALUE}(next) - \text{VALUE}(current) \le 0$ dan $T$ adalah temperatur.
     - Jadwal pendinginan (*cooling schedule*): $T \leftarrow T \times cooling\_factor$ (umumnya $0.95$ s.d. $0.995$).
     - Perilaku: Saat $T$ tinggi berperilaku seperti *random walk* (eksplorasi luas); saat $T$ mendekati 0 berperilaku murni seperti *hill climbing* (eksploitasi lokal).
   - **Genetic Algorithm (GA)**:
     - Terinspirasi dari evolusi biologi: populasi individu, fungsi fitness, seleksi (turnamen/roulette), *crossover* (rekombinasi gen yang bermakna), dan *mutasi*.
     - Representasi/encoding kromosom harus valid dan setiap segmen gen memiliki makna fungsional.

---

### C. Materi 2: Constraint Satisfaction Problem (CSP)
Tujuan utama: Menemukan assignment variabel yang memenuhi seluruh batasan (*constraints*) tanpa konflik sejak awal.

1. **Formulasi CSP Tiga Komponen $(X, D, C)$**:
   - **Variables ($X$)**: $\{X_1, X_2, \dots, X_n\}$ — Entitas yang memerlukan penugasan nilai.
   - **Domains ($D$)**: $\{D_1, D_2, \dots, D_n\}$ — Himpunan nilai yang diizinkan untuk setiap variabel.
   - **Constraints ($C$)**: Batasan yang membatasi kombinasi nilai:
     - *Unary Constraint*: Melibatkan 1 variabel tunggal (misal: Tank wajib HP $\ge 90$).
     - *Binary Constraint*: Melibatkan relasi antara 2 variabel (misal: $Job_A \neq Job_B$).
     - *Global Constraint*: Melibatkan banyak variabel (misal: Total HP tim $\le 250$).
2. **Definisi Status Solusi**:
   - **Complete**: Seluruh variabel telah terisi nilai (*assigned*).
   - **Consistent**: Tidak ada batasan (*constraint*) yang dilanggar.
   - **Solusi Sah**: *Complete* **AND** *Consistent*.
3. **Backtracking Search**:
   - Depth-First Search yang memanfaatkan sifat **Commutativity** (urutan pemilihan variabel tidak mempengaruhi hasil assignment akhir).
   - **Early Checking / Pruning**: Langsung menolak cabang yang melanggar constraint di level atas tanpa perlu mengeksplorasi cabang di bawahnya.
4. **Heuristik Pemilihan Variabel (Variable Ordering)**:
   - **MRV (Minimum Remaining Values)**: *Fail-First principle*. Pilih variabel unassigned dengan sisa nilai legal di domain paling sedikit agar dead-end terdeteksi secepat mungkin.
   - **Degree Heuristic**: *Tie-breaker* jika nilai MRV seri. Pilih variabel yang memiliki keterlibatan constraint terbanyak terhadap variabel lain yang belum di-assign.
   - **Hierarki Prioritas**: `MRV` $\rightarrow$ Jika seri: `MRV + Degree` $\rightarrow$ Jika masih seri: urutan indeks/tetap.
5. **Heuristik Pengurutan Nilai (Value Ordering)**:
   - **LCV (Least Constraining Value)**: *Succeed-First principle*. Pilih nilai yang menyisakan jumlah pilihan legal terbanyak bagi variabel tetangga yang belum di-assign.
6. **Inferensi & Pemangkasan Domain (Inference / Pruning)**:
   - **Forward Checking**: Setiap kali suatu variabel $X$ diberi nilai, pangkas nilai-nilai inkonsisten dari domain variabel tetangganya. Jika domain tetangga menjadi kosong, langsung lakukan *backtrack*.
   - **Arc Consistency (AC-3)**:
     - Busur $X \to Y$ konsisten jika setiap nilai di $D(X)$ memiliki pasangan nilai di $D(Y)$ yang memenuhi batasan (*support*).
     - Fungsi `REVISE(X, Y)`: Menghapus nilai pada $D(X)$ yang tidak didukung oleh $D(Y)$.
     - Algoritma antrean busur (*queue of arcs*): Jika `REVISE` memperkecil domain $X$, seluruh busur tetangga $(Z, X)$ dimasukkan kembali ke antrean untuk dipropagasi.
     - Mampu mendeteksi kebuntuan antarvariabel unassigned yang gagal dideteksi oleh Forward Checking biasa.
7. **Backtracking dengan Inferensi**:
   - Algoritma rekursif yang memadukan pemilihan variabel (MRV+Degree), pemilihan nilai (LCV), dan propagasi inferensi (Forward Checking / AC-3) di setiap langkah assignment.

---

### D. Mandat Khusus Tugas Besar (Slide 22 & 46)
> **Tubes Tahap 3**:
> 1. Konfigurasi NPC sebelum menyerang yang mencakup:
>    - **Jumlah dan karakter NPC penyerang** (Job Class / Tipe Karakter).
>    - **Konfigurasi item dan atribut yang digunakan NPC** (HP, Potion, Buff ATK/DEF, Profil AI).
> 2. **Goal Desain Permainan**:
>    - Dinamis: Tidak terlalu gampang (player bosan), tidak terlalu sulit (player frustrasi) $\rightarrow$ *Dynamic Difficulty Balancing*.
> 3. **Arsitektur Teknis**:
>    - **Gabungan Local Search + CSP** (Backtracking dengan MRV, Degree, LCV, AC-3 / Forward Checking).

---

## 🔍 Bagian 2: Analisis Kondisi Proyek Saat Ini

Berdasarkan audit menyeluruh terhadap berkas:
- [`game/npc_config_csp.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_csp.py)
- [`game/npc_config_optimizer.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_optimizer.py)
- [`game/difficulty.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/difficulty.py)
- [`game/app.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py)
- [`game/overlay.py`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/overlay.py)

Berikut adalah status implementasi dari setiap poin materi:

### 📊 Matriks Kesesuaian Implementasi
| No | Komponen Materi | Status di Kode | Lokasi File | Evaluasi & Catatan |
|---|---|---|---|---|
| **1** | **Formulasi CSP $(X, D, C)$** | ✅ **Lengkap** | [`game/npc_config_csp.py:113-136`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_csp.py#L113-L136) | Variabel $X$ (char_type, hp, potion, atk, def, eval), Domain $D$, dan Batasan $C$ (C1-C8) didefinisikan dengan jelas. |
| **2** | **Backtracking Search** | ✅ **Lengkap** | [`game/npc_config_csp.py:313-348`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_csp.py#L313-L348) | Algoritma rekursif `_backtrack` dengan early partial consistency check dan undo saat gagal (*backtrack*). |
| **3** | **Heuristik MRV** | ✅ **Lengkap** | [`game/npc_config_csp.py:196-207`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_csp.py#L196-L207) | `select_unassigned_variable_mrv` memilih variabel unassigned dengan ukuran domain terkecil (*fail-first*). |
| **4** | **Heuristik Degree (MRV + Degree)** | ⚠️ **Belum Lengkap** | [`game/npc_config_csp.py:206`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_csp.py#L206) | Hanya mengambil `min` berdasarkan domain size. Jika beberapa variabel memiliki domain size yang sama, tie-breaker Degree Heuristic belum diterapkan. |
| **5** | **Heuristik LCV** | ✅ **Lengkap** | [`game/npc_config_csp.py:208-244`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_csp.py#L208-L244) | `order_domain_values_lcv` mengurutkan nilai berdasarkan minimnya konflik terhadap domain variabel lain. |
| **6** | **Forward Checking / AC-3 Propagation** | ⚠️ **Parsial** | [`game/npc_config_csp.py:138-191`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_csp.py#L138-L191) | `apply_ac3_unary` hanya memangkas unary constraint di awal secara statis. Belum ada antrean busur (*queue of arcs*) AC-3 dinamis antar unassigned variables saat backtracking. |
| **7** | **Hill Climbing (Steepest Ascent)** | ✅ **Lengkap** | [`game/npc_config_optimizer.py:178-200`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_optimizer.py#L178-L200) | Menemukan tetangga legal terbaik dan berhenti saat mencapai local optimum. |
| **8** | **Hill Climbing + Sideways Move** | ✅ **Lengkap** | [`game/npc_config_optimizer.py:205-240`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_optimizer.py#L205-L240) | Mengizinkan pergerakan ke nilai yang sama hingga batas toleransi (`max_sideways=15`) untuk menembus plateau. |
| **9** | **Hill Climbing + Random Restart** | ✅ **Lengkap** | [`game/npc_config_optimizer.py:245-274`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_optimizer.py#L245-L274) | Melakukan restart dari solusi acak legal CSP hingga `max_restarts` kali. |
| **10** | **Simulated Annealing (SA)** | ✅ **Lengkap** | [`game/npc_config_optimizer.py:278-324`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_optimizer.py#L278-L324) | Menggunakan temperatur $T$, cooling rate, dan probabilitas penerimaan downhill $P = \exp(\Delta E / T)$. |
| **11** | **Genetic Algorithm (GA)** | ✅ **Lengkap** | [`game/npc_config_optimizer.py:328-420`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_optimizer.py#L328-L420) | Populasi, seleksi turnamen, crossover seragam anggota skuad, mutasi tetangga legal, dan elitisme. |
| **12** | **Integrasi Sinergis CSP + Local Search** | ✅ **Lengkap** | [`game/npc_config_optimizer.py:72-173`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/npc_config_optimizer.py#L72-L173) | CSP digunakan sebagai generator state awal dan validator ruang pencarian tetangga legal (*neighbourhood generator*). |
| **13** | **Dynamic Difficulty Balancing** | ✅ **Lengkap** | [`game/difficulty.py:58-96`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/difficulty.py#L58-L96) | Formula difficulty terbobot [0.0–1.0], target adaptif sesuai HP & buff player, serta fungsi fitness evaluasi. |
| **14** | **Visualisasi UI & Pre-Battle Mode** | ✅ **Lengkap** | [`game/overlay.py:580-680`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/overlay.py#L580-L680) | Layar `PRE_BATTLE` memungkinkan pemain/dosen memilih algoritma Local Search, melihat gauge kesulitan, checklist constraint CSP, dan kartu anggota tim musuh. |

---

## 📌 Kesimpulan & Temuan Kunci (Gap Analysis)

Secara garis besar, **seluruh arsitektur besar Tubes Tahap 3 (Local Search + CSP untuk konfigurasi squad NPC penyerang)** telah dibangun dengan sangat solid di dalam proyek.

Namun, terdapat **2 poin teknis algoritma** dari materi kuliah yang masih perlu disempurnakan agar nilai akademis terpenuhi 100%:
1. **MRV + Degree Heuristic**: Di `npc_config_csp.py`, fungsi pemilihan variabel saat ini hanya melihat ukuran domain (`len(domains[var])`). Jika terdapat beberapa variabel dengan ukuran domain sama, perlu ditambahkan *tie-breaker* Degree Heuristic (menghitung jumlah keterlibatan constraint dengan variabel unassigned lainnya).
2. **AC-3 Propagation Antrean Busur**: Di `npc_config_csp.py`, fungsi AC-3 saat ini baru berupa filtering unary statis di awal. Implementasi fungsi `REVISE(X, Y)` dan antrean busur `queue = [all_arcs]` yang memotong domain secara berantai saat backtracking akan menyempurnakan implementasi AC-3 sesuai slide 36–39.
