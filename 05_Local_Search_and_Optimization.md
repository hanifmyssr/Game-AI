# Local Search & Optimization

> Mata Kuliah: Kecerdasan Buatan  
> Tanggal: September 2026

---

## Konteks

**Minggu sebelumnya:** Pencarian jalur (path) — menemukan urutan aksi menuju goal.

**Hari ini:** Pencarian konfigurasi optimal — path tidak penting, hanya state akhir yang penting.

**Contoh:** Penjadwalan kuliah. Yang penting jadwal tidak bentrok (state akhir), bukan urutan bagaimana jadwal itu dibuat.

---

## Kompetensi

1. Membedakan problem yang solusinya berupa **path** dari problem yang solusinya berupa **konfigurasi**, dan menjelaskan konsekuensinya terhadap kebutuhan memori.
2. Menelusuri hill climbing dan simulated annealing dari sebuah seed yang diberikan, serta mengidentifikasi failure mode yang tercapai.
3. Menjelaskan tiga failure mode local search: **local maximum**, **plateau/shoulder**, dan **ridge**.
4. Merancang encoding genetic algorithm untuk sebuah problem yang dideskripsikan, dan menjustifikasi mengapa crossover pada encoding itu bermakna.
5. Membandingkan biaya beberapa metode dalam satuan yang sama, dan menjelaskan mengapa satuan yang dipilih dapat mengubah kesimpulan.
6. Menyebutkan kondisi yang membuat random restart, simulated annealing, dan genetic algorithm masing-masing layak dipakai.

---

## Konsep Dasar Local Search

- Hanya menggunakan **state saat ini** (tidak ada frontier, tidak ada explored seperti A*)
- Kebutuhan memori: **O(1)** — konstan terlepas dari ukuran masalah → scalable

---

## Contoh Kasus: 8-Queens

**Tujuan:** Tidak ada queen yang saling mengancam.

**Representasi state:**
- Satu kolom satu queen (8 queen)
- `8^8 ≈ 17 juta` kemungkinan state
- Jika queen bisa ditempatkan di mana saja: `C(64,8) = 4.4 Miliar` state → Pilihan constraint sangat penting

**Fungsi objektif:** Meminimalkan jumlah queen yang saling menyerang.

**Neighbour:** Pindahkan satu queen dalam kolomnya.
- `8 × 7 = 56` neighbour per state

---

## Hill Climbing

### Algoritma

```
current ← initial state
loop:
    neighbour ← highest-valued successor of current
    if VALUE(neighbour) ≤ VALUE(current): return current
    current ← neighbour
```

### Performa pada 8-Queens (1.000 random start)

| Kondisi | Nilai |
|---|---|
| Tingkat keberhasilan (0 konflik) | 13,2% |
| Langkah rata-rata saat **berhasil** | 4,1 langkah |
| Langkah rata-rata saat **tersangkut** | 3,1 langkah |

Pencapaian state optimal dalam ~4 langkah, walaupun tingkat kegagalan 87% tetap dapat dianggap murah karena biaya per percobaan sangat rendah.

> Simulasi: https://pusdat.id/simulation/hillclimb.html

---

## Failure Modes

### 1. Local Maximum
- State lebih tinggi dari semua tetangganya, tapi bukan global maximum
- Seluruh neighbour bernilai lebih buruk → pencarian berhenti

### 2. Plateau / Shoulder
- **Plateau:** Region datar, gradient nol, tidak ada gerakan naik
- **Shoulder:** Infleksi datar pada lereng, masih ada kenaikan di salah satu ujung
- Solusi: izinkan **sideways move** (bergerak ke nilai yang sama)

### 3. Ridge
- Arah perbaikan ada, tetapi memerlukan minimal dua langkah terkoordinasi
- Setiap langkah individual mengharuskan penurunan nilai terlebih dahulu
- **Contoh:** Dari nilai 14, perlu turun ke 11 dulu, baru naik ke 16

---

## Sideways Move

Mengizinkan bergerak ke nilai yang **sama** (bukan hanya yang lebih tinggi).

**Efek pada 8-Queens (dengan maks. 100 sideways move):**

| Metrik | Tanpa Sideways | Dengan Sideways |
|---|---|---|
| Tingkat keberhasilan | 13,2% | 95,5% |
| Langkah rata-rata (berhasil) | 4,1 | 18,5 |
| Langkah rata-rata (gagal) | 3,1 | 64,9 |

---

## Random Restart

Jika terjadi failure, lakukan restart dengan seed baru yang random.

| Jumlah Restart | Probabilitas Berhasil |
|---|---|
| 1 | 13,2% |
| 5 | 50,7% |
| 8 | 67,8% |
| 16 | 89,6% |
| 25 | 97,1% |

**Kapan digunakan:** Ketika problem memiliki banyak local optima dan setiap run sangat murah.

---

## Simulated Annealing (SA)

### Motivasi
Terinspirasi dari metalurgi: logam dipanaskan sehingga atomnya bergerak bebas, lalu didinginkan perlahan agar mengendap pada struktur kristal → lebih kuat.

**Ide kunci:** Terkadang boleh mengambil langkah **downhill** (lebih buruk) agar bisa keluar dari local optimum.

**Contoh:** `14 → 11 → 16` (turun dulu ke 11, lalu naik ke 16)

### Algoritma

```
T ← T0
while T > ε dan current belum solusi:
    next ← neighbour yang dipilih SECARA ACAK
    ΔE ← VALUE(next) − VALUE(current)
    if ΔE > 0:
        current ← next              # perbaikan → ambil
    else:
        u ← acak seragam pada [0,1)
        if u < e^(ΔE/T):
            current ← next          # terima dengan probabilitas e^(ΔE/T)
    T ← T × cooling
return current
```

> **Perbedaan dengan Hill Climbing:** Hill climbing memilih `next` berdasarkan **skor terbaik**, sedangkan SA memilih **secara acak**.

### Analisis Perilaku

| Kasus | `e^(ΔE/T)` | Perilaku (ΔE ≤ 0 = langkah lebih buruk) |
|---|---|---|
| T besar | → 1 | Hampir semua diterima → **random walk** |
| T kecil | → 0 | Semakin sulit menerima langkah → **hill climbing** |
| ΔE sedikit negatif | mendekati 1 | Lebih mudah menerima langkah |
| ΔE sangat negatif | mendekati 0 | Semakin sulit menerima langkah |

SA memungkinkan mengambil langkah yang lebih buruk berdasarkan **ΔE/T** dengan harapan bisa naik di langkah berikutnya.

### Cooling Factor

```
T ← T × cooling    # biasanya T × 0.995
```

- **Terlalu cepat dingin:** Terlalu cepat berhenti di local minimum terdekat
- **Terlalu lambat dingin:** Terlalu lama mencari secara random

**Kapan digunakan SA:** Ketika problem memiliki landscape yang kompleks dengan banyak local optima, dan random restart terlalu mahal.

---

## Genetic Algorithm (GA)

### Motivasi
Terinspirasi dari biologi. Simpan **populasi** state, lakukan crossover dan mutasi, harapkan terjadi evolusi.

### Komponen

- **Individu (kromosom):** Representasi satu state, misalnya untuk 8-Queens: `06534567`
- **Fungsi fitness():** Mengukur kualitas individu
- **Crossover:** Mengawinkan dua individu untuk menghasilkan individu baru
- **Mutasi:** Perubahan kecil secara acak pada individu

### Syarat Encoding yang Valid

State harus bisa direpresentasikan sebagai individu yang bisa di-cross dan dimutasi, di mana **setiap string harus state yang valid** dan **substring punya makna**.

**Contoh encoding yang SALAH** (untuk masalah kota yang dikunjungi):

```
Induk 1:  A B C | D E
Induk 2:  E D A | C B
Anak 1:   A B C | C B   ← C dan B dikunjungi 2x, D dan E tidak
Anak 2:   E D A | D E   ← D dan E dikunjungi 2x, B dan C tidak
```

> **Gunakan GA hanya jika encoding-nya bermakna.**

**Kapan digunakan GA:** Problem dengan solusi banyak, ruang pencarian sangat besar, dan representasi yang memungkinkan crossover bermakna.

---

## Perbandingan: Local Search vs Informed Search (A*)

| Aspek | Local Search & Optimization | Informed Search (A*) |
|---|---|---|
| Informasi yang digunakan | State saat ini + tetangga | Heuristik (estimasi ke goal) |
| Tujuan | Optimasi (nilai terbaik) | Mencapai goal (path terpendek) |
| Perilaku | Greedy / local improvement | Sistematis, dipandu heuristik |
| Penggunaan tipikal | Optimization problems | Path finding / search problems |
| Memori | O(1) | O(b^d) |

---

## Ringkasan Kapan Menggunakan Tiap Metode

| Metode | Gunakan Ketika... |
|---|---|
| **Hill Climbing** | Solusi banyak, biaya per restart rendah |
| **Sideways Move** | Ada plateau/shoulder yang perlu dilalui |
| **Random Restart** | Banyak local optima, setiap run murah |
| **Simulated Annealing** | Landscape kompleks, random restart terlalu mahal |
| **Genetic Algorithm** | Representasi memungkinkan crossover bermakna, ruang sangat besar |
