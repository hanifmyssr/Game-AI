# Constraint Satisfaction Problem (CSP)

> Mata Kuliah: Kecerdasan Buatan  
> Tanggal: Oktober 2026

---

## Konteks

**Minggu lalu (Local Search):** Kasus N-queens diselesaikan dengan memindahkan bidak untuk mengurangi konflik. Dimulai dari assignment yang **complete** tapi tidak konsisten, lalu diperbaiki.

**Minggu ini (CSP):** Constraints dibuat eksplisit dan solusi dicari dari awal tanpa konflik — bidak diletakkan **satu per satu**.

> CSP mendefinisikan masalah lebih formal; local search (minggu lalu) adalah salah satu teknik penyelesaiannya.

**Strategi inti agent:** *Menghilangkan yang tidak dapat dilakukan* (eliminasi berdasarkan constraint).

---

## Definisi CSP

CSP ditentukan oleh 3 set: **X**, **D**, dan **C**.

### X — Variables
Hal-hal yang perlu diberi nilai.  
`X = {X₁, …, Xₖ}`

*Contoh:* Pada penjadwalan kuliah, variabel adalah setiap pertemuan mata kuliah.

### D — Domains
Satu domain per variabel, berisi values yang dapat mengisi variabel.  
`D = {D₁, …, Dₖ}`

*Contoh:* Domain berisi set pasangan `(waktu, ruangan)`. Domain variabel kuliah praktikum akan berbeda dengan kuliah biasa.

### C — Constraints
Batasan yang membatasi kombinasi values.

*Contoh:* `slot(A) ≠ slot(B)` — tidak boleh ada dua pertemuan kuliah yang punya slot sama.

---

## Penyusunan Komponen CSP

1. **Identifikasi** apa yang memerlukan value → **variabel**
2. **Identifikasi** values per variabel → **domain**
3. **Identifikasi** kombinasi yang dilarang → **constraint**

**Solusi CSP:** Semua variabel terisi value dan tidak melanggar constraint.

---

## Definisi Solusi

### Complete Assignment
Setiap variabel terisi (assigned) nilai.  
*Contoh:* Setiap perkuliahan mendapat slot ruangan dan waktu.  
> Walau ada bentrok, tetap dianggap complete jika semua variabel terisi.

### Consistent Assignment
Assignment variabel tidak melanggar constraint.  
*Contoh:* Tidak ada bentrok waktu dan ruangan.  
> Walau jadwal kosong, tetap dianggap consistent.

**Solusi = Complete + Consistent**

---

## Jenis Constraint

| Jenis | Deskripsi | Contoh |
|---|---|---|
| **Unary** | Melibatkan satu variabel | Kuliah X tidak boleh dijadwalkan hari Jumat |
| **Binary** | Melibatkan dua variabel | Dua kuliah dengan mahasiswa sama perlu slot berbeda |
| **Global** | Melibatkan banyak variabel | `AllDifferent(X₁, …, Xₖ)` — semua variabel harus berbeda nilainya |

---

## Contoh Kasus: Pewarnaan Peta Australia

**Wilayah:** Western Australia (WA), Northern Territory (NT), South Australia (SA), Queensland (Q), New South Wales (NSW), Victoria (V), Tasmania (T)

**Formalisasi CSP:**

```
X = {WA, NT, SA, Q, NSW, V, T}        # 7 variabel

D = {red, green, blue}                  # domain sama untuk semua

C = { WA≠NT, WA≠SA, NT≠SA, NT≠Q,
      SA≠Q, SA≠NSW, SA≠V, Q≠NSW,
      NSW≠V }                           # tidak boleh ada tetangga warna sama
```

**Jumlah complete assignment:** `3^7 = 2.187`

**Jumlah solusi (complete + consistent):** `18`

### Constraint Graph

- Setiap node = variabel
- Setiap edge = binary constraint antara dua variabel
- Node SA memiliki degree 5 (paling banyak constraint)
- Node T tidak memiliki edge (isolated, bebas dipilih warna apa saja)

---

## Pencarian Naif (Naive Search)

Pada pencarian naif, **urutan variable assignment tidak diperbaiki** — semua permutasi dicoba.

**Analisis untuk n variabel dengan domain d:**

| Level | Cabang |
|---|---|
| Root (level 0) | n·d |
| Level 1 | (n−1)·d |
| Level k | (n−k+1)·d |
| Level n (daun) | semua terisi |

**Total daun:** `n! · dⁿ`

**Masalah:** Hanya ada `dⁿ` complete assignment yang berbeda, tapi muncul `n!` kali di pohon pencarian.

*Contoh Peta Australia:* `7! × 3^7 ≈ 11 juta daun` padahal hanya `2.187` assignment berbeda.

---

## Commutativity

`WA=red → NT=green` **sama dengan** `NT=green → WA=red`

**Solusi:** Pilih **satu variabel** di setiap level, dan branch berdasarkan nilai (value).

**Efek:** Branching factor turun dari `(n−k+1)·d` → `d`, sehingga `n!·dⁿ` turun menjadi `dⁿ` daun.

*Peta Australia:* `11 juta → 2.187`

---

## Early Checking (Pruning)

Naive search hanya mengecek constraint **pada daun** setelah assignment selesai.

**Early Checking:** Cek constraint segera setelah setiap assignment.

*Contoh:* Jika `WA=red` dan kemudian dicoba `NT=red`, langsung ditolak karena WA & NT bersebelahan — tanpa perlu melanjutkan assign 5 daerah lainnya.

**Pruning yang dibuang:** `d^(n−k)` subtree  
*Contoh:* `3^5 = 243` node yang tidak perlu dieksplorasi

---

## Backtracking Search

**Backtracking = Commutativity + Early Checking**

### Algoritma

```
BACKTRACK(assignment, domains):
    if assignment is complete: return assignment
    X ← SELECT-VARIABLE(assignment, domains)
    for v in ORDER-VALUES(X, assignment, domains):
        if v is consistent with assignment:
            assign X = v
            result ← BACKTRACK(assignment, domains)
            if result != failure: return result
            remove X = v from assignment    # gagal, backtrack
    return failure
```

**Prinsip:** "Pilih, periksa, assign, rekursif, jika gagal restore"

> Simulasi: https://pusdat.id/simulation/csp-backtracking.html

---

## Heuristik Pemilihan Variabel

### MRV — Minimum Remaining Values

Pilih variabel yang belum di-assign dengan **legal values tersisa yang paling sedikit**.

**Legal value:** Value yang konsisten dengan variabel yang sudah di-assign.

*Contoh setelah `WA=red`, `NT=green`:*

| Variabel | Legal Values Tersisa | Jumlah |
|---|---|---|
| **SA** | blue | **1** ← dipilih MRV |
| Q | red, blue | 2 |
| NSW | red, green, blue | 3 |
| V | red, green, blue | 3 |
| T | red, green, blue | 3 |

**Filosofi:** *Fail-first* — tangani variabel yang paling terikat di awal, agar dead end bisa ditemukan lebih cepat.

### Degree Heuristic (Tie-Breaker)

Jika MRV seri (nilai yang sama), pilih variabel yang terlibat dengan **unassigned variables paling banyak**.

*Contoh setelah `WA=red`, `NT=green` (NSW, V, T sama-sama MRV=3):*

| Variabel | Degree (tetangga belum di-assign) |
|---|---|
| NSW | 3 (SA, Q, V) |
| V | 2 (SA, NSW) |
| T | 0 |

### Urutan Prioritas

1. **MRV** — paling sedikit legal values
2. **MRV + Degree** — jika MRV seri, pilih degree tertinggi
3. **Urutan tetap** — jika masih seri

**Perbandingan performa (Peta Australia):**

| Metode | Assignment Dicoba | Backtrack |
|---|---|---|
| Urutan tetap | 17 | 2 |
| MRV | 11 | 0 |
| MRV + Degree | 15 | 0 |

---

## Heuristik Pemilihan Nilai: LCV

### LCV — Least Constraining Value

Setelah memilih variabel, pilih **value yang menghilangkan paling sedikit legal options** dari tetangga yang belum di-assign.

*Contoh: `WA=red`, `NT=green`, variabel Q dipilih:*

```
Q legal values: {red, blue}
Tetangga Q yang belum di-assign: SA={blue}, NSW={red, green, blue}

Q=red:  buang 0 dari SA + 1 (red) dari NSW = Total 1 opsi dibuang
Q=blue: buang 1 dari SA + 1 (blue) dari NSW = Total 2 opsi dibuang

LCV pilih: Q=red (paling sedikit menghilangkan opsi tetangga)
```

**Filosofi:** *Succeed-first* — pilih value yang menyisakan paling banyak opsi untuk variabel lain.

### Analogi: Fail-First vs Succeed-First

> Seperti merencanakan perjalanan ke luar negeri:
> - **MRV (fail-first):** Cek dulu hal yang bisa menggagalkan seluruh perjalanan — passport (expired?) atau visa.
> - **LCV (succeed-first):** Memilih rute ke airport (kereta, travel, sewa mobil) — hanya perlu satu yang jalan, pilih yang paling umum berhasil.

**Prinsip:** *"Every variable must be assigned, but only one value needs to succeed."*

---

## Forward Checking

Setelah meng-assign variabel X, dari setiap tetangga yang **belum di-assign**, hapus value yang tidak konsisten dengan X. Jika ada domain yang menjadi kosong, lakukan backtrack.

*Contoh:*

```
WA=red  → NT dan SA kehilangan red: NT={green,blue}, SA={green,blue}
Q=green → NT, SA, NSW kehilangan green: NT={blue}, SA={blue}, NSW={red,blue}
V=blue  → SA dan NSW kehilangan blue: SA={} (EMPTY!), NSW={red}
         → FAIL, backtrack sebelum assign NT, SA, atau NSW lebih lanjut
```

**Keterbatasan Forward Checking:** Hanya mengecek hubungan antara variabel yang sudah di-assign dengan tetangganya — tidak melihat konflik antara **dua variabel yang sama-sama belum di-assign**.

---

## Arc Consistency — AC-3

### Motivasi

*Masalah Forward Checking:* Setelah `WA=red` dan `Q=green`, forward checking memberikan `NT={blue}` dan `SA={blue}`. Tidak ada domain yang kosong, tetapi NT dan SA bertetangga dan keduanya hanya punya warna yang sama → dead end tidak terdeteksi.

**Penyebab:** Forward checking hanya memeriksa Q→NT dan Q→SA, bukan NT→SA.

### Definisi Arc Consistency

Arc `X → Y` **konsisten** ketika setiap nilai di `D(X)` setidaknya punya **satu nilai di D(Y)** yang memenuhi constraint (disebut *support*).

*Contoh `X ≠ Y`, `D(X)={red, blue}`, `D(Y)={blue}`:*

```
X=red  → support di Y: blue (karena blue ≠ red) → biarkan red
X=blue → support di Y: tidak ada (karena blue = blue) → HAPUS blue

Setelah hapus: D(X) = {red}. Arc X→Y sekarang konsisten.
```

> Perhatikan: `X→Y` berbeda dengan `Y→X`. Keduanya perlu dicek.

### Fungsi REVISE

```
REVISE(X, Y):
    revised ← false
    for each x in D(X):
        if no y in D(Y) satisfies constraint between X and Y:
            delete x from D(X)
            revised ← true
    return revised
```

### Algoritma AC-3

```
AC-3(csp):
    queue ← semua arcs (arah dua-arah untuk setiap constraint)
    while queue is not empty:
        (X, Y) ← pop dari depan queue
        if REVISE(X, Y):
            if D(X) is empty: return failure
            for each tetangga Z dari X (kecuali Y):
                if (Z, X) tidak ada di queue:
                    add (Z, X) ke belakang queue
    return success
```

**Logika:** Jika domain X berubah, semua constraint yang melibatkan X perlu diperiksa ulang.

### Contoh Trace: X < Y < Z

```
D(X) = D(Y) = D(Z) = {1, 2, 3}
Queue awal: (X,Y), (Y,X), (Y,Z), (Z,Y)
```

| Step | Arc | Deletion & Alasan | D(X) | D(Y) | D(Z) |
|---|---|---|---|---|---|
| 1 | (X,Y) | Hapus X=3: tidak ada Y > 3 | {1,2} | {1,2,3} | {1,2,3} |
| 2 | (Y,X) | Hapus Y=1: tidak ada X < 1 | {1,2} | {2,3} | {1,2,3} |
| 3 | (Y,Z) | Hapus Y=3: tidak ada Z > 3. Tambah (X,Y) lagi | {1,2} | {2} | {1,2,3} |
| 4 | (Z,Y) | Hapus Z=1 dan Z=2: tidak ada yang > Y=2 | {1,2} | {2} | {3} |
| 5 | (X,Y) | Hapus X=2: 2 tidak < Y=2 | {1} | {2} | {3} |

**Hasil:** X=1, Y=2, Z=3 ✓ (sesuai X < Y < Z)

### Kompleksitas AC-3

`O(c · d³)`

- `c` = jumlah total directed arcs (setiap binary constraint punya dua arah)
- `d` = ukuran domain terbesar

### Keterbatasan AC-3

AC-3 melihat **pasangan** variabel, bukan **group**.

*Contoh (Segitiga 3 node, domain {red, blue}):*

```
A ≠ B, B ≠ C, A ≠ C

Setiap pasangan: fine (red pairs with blue)
Semua bersama: butuh 3 warna, tapi hanya ada 2 → TIDAK ADA SOLUSI

AC-3 hasil: 6 arcs diperiksa, tidak ada yang dihapus → lolos padahal tidak ada solusi
```

> Arc consistent **belum tentu** berarti ada solusi.

---

## Backtracking dengan Inferensi

```
BACKTRACK(assignment, domains):
    if assignment is complete: return assignment
    X ← SELECT-VARIABLE(assignment, domains)
    for v in ORDER-VALUES(X, assignment, domains):
        if v is consistent with assignment:
            assign X = v
            pruned ← INFERENCE(X, v, domains)    # FC atau AC-3
            if pruned did not empty any domain:
                result ← BACKTRACK(assignment, domains)
                if result != failure: return result
            restore every value in pruned
            remove X = v from assignment
    return failure
```

**Pilihan inferensi:** Forward Checking atau AC-3

---

## CSP vs Local Search

### Kapan CSP lebih cocok

| Kondisi | Penjelasan |
|---|---|
| Solusi jarang (banyak constraint) | Local search berasumsi hanya perlu sedikit perbaikan |
| Perlu tahu apakah ada solusi | Local search bisa berhenti karena time limit |
| Perlu semua solusi / solusi terbaik | Local search tidak menjamin completeness |
| Hasil harus reproducible | Local search menggunakan random yang berbeda tiap run |

### Kapan Local Search lebih cocok

| Kondisi |
|---|
| Solusi banyak |
| Ukuran problem sangat besar |
| "Good enough" solution dapat diterima (yang penting cepat) |
| Hanya memperbaiki assignment yang sudah ada |

---

## Ringkasan Teknik CSP

| Teknik | Tipe | Fungsi |
|---|---|---|
| **Commutativity** | Struktural | Hilangkan duplikasi urutan variable |
| **Early Checking** | Pruning dasar | Tolak assignment yang langsung melanggar |
| **Backtracking** | Algoritma inti | Pilih, assign, rekursif, undo jika gagal |
| **MRV** | Heuristik variabel | Pilih variabel dengan sisa legal value paling sedikit |
| **Degree** | Tie-breaker | Pilih variabel dengan paling banyak unassigned neighbors |
| **LCV** | Heuristik nilai | Pilih value yang paling sedikit membatasi tetangga |
| **Forward Checking** | Inferensi | Hapus values dari domain tetangga setelah assign |
| **AC-3** | Inferensi | Propagasi arc consistency ke seluruh graph |

---

## Referensi Simulasi

- Backtracking CSP: https://pusdat.id/simulation/csp-backtracking.html
- AC-3: https://pusdat.id/simulation/ac3.html
