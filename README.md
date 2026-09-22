# Bakekok

## Deskripsi
Proyek Bakekok ini merupakan tugas besar mata kuliah Kecerdasan Buatan untuk kelompok 7. Implementasi ini menggunakan Godot Engine untuk membuat visualisasi algoritma A* (A-star) dan UCS dalam game atau simulasi.

## Fitur
- Implementasi algoritma pencarian jalur A*.
- Visualisasi langkah‑langkah pencarian secara real‑time.
- Kontrol interaktif untuk mengatur titik mulai dan tujuan.
- Dukungan export ke berbagai platform melalui Godot.

## Algoritma Pencarian NPC
NPC (Non‑Player Character) dapat mencari jalur terpendek pada grid menggunakan beberapa algoritma:

### Uniform Cost Search (UCS)
Varian Dijkstra yang memperluas node dengan biaya kumulatif terendah terlebih dahulu. Tidak memerlukan heuristik, memastikan solusi optimal bila semua biaya sisi non‑negatif.

### A* Search
Menggabungkan keunggulan UCS dengan heuristik. Nilai f = g + h, dimana **g** adalah biaya dari start ke node saat ini, dan **h** adalah perkiraan biaya ke tujuan.

## Heuristik yang Digunakan
Pengguna dapat memilih tipe heuristik melalui inspector Godot (variabel `HeuristicType` di `Pathfinder.gd`):

- **Manhattan Distance**: `h = |x1 - x2| + |y1 - y2|` – cocok untuk gerakan empat arah.
- **Euclidean Distance**: `h = sqrt((x1 - x2)^2 + (y1 - y2)^2)` – untuk gerakan bebas arah.
- **Diagonal Distance**: `h = max(|dx|, |dy|)` – kombinasi Manhattan dan Euclidean, cocok untuk gerakan delapan arah.
- **Chebyshev Distance**: `h = max(|dx|, |dy|)` – secara khusus memperhitungkan gerakan diagonal seperti gerakan Raja pada catur, memberikan estimasi yang cepat dan admissible bila diagonal diizinkan.

## Cara Kerja dalam Godot
1. **Node Grid**: Dibangun dari TileMap, setiap tile menjadi node dengan koordinat `(x, y)`.
2. **Pathfinder.gd**: Skrip utama yang mengimplementasikan UCS dan A* menggunakan `PriorityQueue`.
3. **Pemilihan Algoritma**: Pada inspector, pilih `SearchAlgorithm` (UCS atau A*) dan, bila A* dipilih, pilih `Heuristic` (termasuk Chebyshev).
4. **Visualisasi**: Node yang sedang diproses ditandai biru, jalur akhir berwarna hijau.

## Cara Menjalankan
1. Pastikan **Godot Engine** versi 4.x sudah terpasang.
2. Buka proyek dengan menjalankan `godot` pada folder proyek atau buka `project.godot` melalui UI Godot.
3. Jalankan scene utama yang berada di dalam folder `Scenes`.

## Instalasi
- **Godot Engine**: Unduh dari https://godotengine.org/download
- Tidak ada dependensi tambahan karena semua skrip berada di dalam folder `Scripts`.

## Kelompok
Kelompok 7 - Universitas Pendidikan Indonesia
- Hanif Muyassar
- Moch Fadillah Pratama
- Muhammad Zidan Mirza Fedrieka
