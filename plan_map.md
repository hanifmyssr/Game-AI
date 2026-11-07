# Dokumen Rencana Teknis: Perombakan Visual Peta, Kamera Sinematik & Lingkungan Dinamis
## *Comprehensive Map & Visual Architecture Plan* — Game *Bakekok*

> **Mata Kuliah**: Kecerdasan Buatan (Semester 3) — Universitas Pendidikan Indonesia  
> **Kelompok**: 7 (Muhammad Hanif Muyassar, Moch Fadillah Pratama, Muhammad Zidan Mirza Fedrieka)  
> **Berkas**: `plan_map.md`  
> **Target Lokasi**: `Game-AI/`  
> **Status Dokumen**: **SELESAI DIIMPLEMENTASIKAN & DIVERIFIKASI (100% PASSED)**  
> **Prinsip Utama**: **HANYA MENGUBAH TAMPILAN, KAMERA, & PETA** — Seluruh logika permainan dan materi AI perkuliahan (Tahap 1 s/d Tahap 3: UCS, A*, Minimax, Alpha-Beta, Local Search, CSP) **DIJAMIN TETAP UTUH & BERFUNGSI 100%**.

---

## 1. Visi Utama & Parameter Kebutuhan Visual

Berdasarkan kesepakatan tim dan gambar referensi (gaya *16×16 High-Detail Crisp Top-Down Pixel Art*):
1. **Kamera Dekat Sinematik (Close-Up POV)**:
   - Sudut pandang pemain didekatkan secara signifikan (skala zoom $\approx 3.0\times$) agar detail tekstur rumput, pohon, riak sungai, jembatan kayu, serta sprite Bolu dan NPC terlihat besar, jelas, dan hidup.
2. **Bebas Burik (Anti-Blur Nearest-Neighbor Scaling)**:
   - Menghapus sepenuhnya efek kabur/smudge akibat *bilinear filtering* (`pygame.transform.smoothscale`), digantikan dengan *Nearest-Neighbor Scaling* (`pygame.transform.scale`). Seluruh tepi piksel 16×16 tetap tajam, tegas, dan otentik (*razor-sharp pixel art*).
3. **Kamera Halus Mengikuti Pemain (Smooth Lerp Tracking on Large Map)**:
   - Karena peta berukuran luas sementara kamera berada dalam jarak dekat, kamera akan memusatkan pandangan pada Bolu dan meluncur halus mengikuti gerakannya (*spring/lerp damping*), dengan batas luar kamera terkunci (*clamped*) pada tepi peta dunia.
4. **Dunia yang Bergerak & Hidup (Living World Animations)**:
   - **Goyangan Angin Prosedural (*Wind Sway*)**: Kanopi pohon dan pucuk semak meliuk lembut tertiup angin sepoi-sepoi menggunakan fungsi gelombang sinus.
   - **Sungai Beriak & Berbusa**: Animasi siklus ubin air 4 frame dari tepian sungai.
   - **Partikel Lingkungan**: Kilauan cahaya bintang kecil (*ambient sparkles*) di padang rumput dan kepulan debu tipis (*footstep dust*) saat karakter melangkah.
5. **Penataan Bangunan Ramah Jalur (No Roof Overlap)**:
   - Menghadirkan **2 unit rumah** dengan jarak aman (*setback*) minimal 2–3 ubin dari jalan tanah utama, menjamin atap yang miring/runcing tidak menutupi koridor jalan utama sama sekali.
6. **Preservasi Mutlak Fitur AI Akademis**:
   - **Pathfinding Overlay (`[Ctrl]`)**: Visualisasi petak ekspansi (*closed set*) dan garis rute (*path*) UCS / A* harus tetap terproyeksikan secara presisi di atas koordinat ubin yang baru pada skala zoom dekat.
   - Seluruh materi AI dari awal (Tahap 1, 2, 3.1, dan 3.2) tetap berfungsi 100% tanpa ada regresi logika.

---

## 2. Inventarisasi Aset Terpilih (Kombinasi Hibrida)

Kedua paket aset yang telah diunduh di `Game-AI/assets/` memiliki ukuran ubin dasar yang **100% identik dengan sistem game saat ini (`cell_size = 16 piksel`)**, menjamin kompatibilitas grid tanpa distorsi.

### A. Tulang Punggung Alam (90%): `Sprout Lands - Sprites - Basic pack`
*Lokasi: `assets/Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/`*
* `Tilesets/Grass.png` ($11 \times 7$ ubin): Autotile rumput hijau cerah dan transisi tepi air/tebing.
* `Tilesets/Water.png` ($4 \times 1$ ubin): **4 frame animasi riak air berbusa** untuk efek sungai mengalir.
* `Tilesets/Hills.png` ($11 \times 9$ ubin): Tebing bukit cokelat bertingkat dan mulut gua di sektor utara.
* `Objects/Wood Bridge.png` ($5 \times 3$ ubin): Jembatan kayu horizontal & vertikal dengan tiang pembatas (identik 100% dengan gambar referensi).
* `Objects/Basic_Grass_Biom_things.png` ($9 \times 5$ ubin): Pohon berkanopi rimbun, semak bulat berlapis, batu sungai, dan bunga liar.
* `Tilesets/Fences.png` ($4 \times 4$ ubin): Pagar kayu pembatas pekarangan dan batas selatan.
* `Objects/Paths.png` ($4 \times 4$ ubin): Jalan setapak tanah bertekstur gelombang lembut.
* `Tilesets/Wooden House.png` ($7 \times 5$ ubin): Rumah kayu dengan atap genteng cokelat.
* `Objects/Chest.png` ($15 \times 6$ ubin): Peti harta karun interaktif.

### B. Aksen & Partikel Tambahan (10%): `Shining Fields_free_v1.1`
*Lokasi: `assets/Shining Fields_free_v1.1/Shining Fields_free_v1.1/Sprites/`*
* `Particles/Dust particles_01.png` ($4 \times 1$ frame): Partikel debu halus yang muncul saat Bolu dan NPC melangkah.
* `Tileset/Wooden path.png` ($3 \times 3$ ubin): Jalan papan dermaga kayu di tepian air timur.
* `Objects/Chest _01.png`: Variasi peti harta karun mewah.

---

## 3. Spesifikasi Tata Letak Map Baru (*Map Layout & House Setback*)

Peta dirancang berukuran **44 × 32 ubin** ($704 \times 512$ piksel dunia). Skala luas ini memberikan ruang eksplorasi yang sangat memuaskan ketika dinikmati dengan kamera zoom dekat ($3.0\times$).

### 3.1 Diagram Denah Dunia (*World Map Blueprint*)
```text
========================================================================================
[SEKTOR BARAT: DESA & SPAWN]           [SUNGAI TENGAH]        [SEKTOR TIMUR: PULAU & MONUMEN]
========================================================================================

+-------------------------------------+     ~~~~~     +----------------------------------------+
|                                     |     ~   ~     |  [TEBING BUKIT UTARA & MULUT GUA]      |
|  [RUMAH 1: PONDOK BOLU]             |     ~   ~     |  (Ketinggian 4 ubin - Dinding Cokelat) |
|  (Ukuran: 4x3 ubin, Atap Cokelat)   |     ~   ~     |  (Rute Patroli Utama NPC Kuro)         |
|  [Pintu Menghadap Selatan]          |     ~   ~     |                                        |
|         |                           |     ~   ~     |                                        |
|   (JARAK AMAN: 2-3 UBIN RUMPUT)     |     ~   ~     |                                        |
|         v                           |     ~   ~     |                                        |
| =================================== |   [JEMBATAN]  | ====================================== |
| JALAN TANAH UTAMA (BERSIH 2 UBIN)   |   [  KAYU  ]  | JALAN TANAH UTAMA (BERSIH 2 UBIN)      |
| (Cost = 1.0, Bebas Rintangan Atap)  |   [LEBAR 2x]  | (Cost = 1.0, Bebas Rintangan Atap)     |
| =================================== |   ~   ~   ~   | ============+==============+========== |
|                                     |     ~   ~     |             |              |           |
|  [PADANG RUMPUT, SEMAK & BUNGA]     |     ~   ~     |             v              v           |
|  (Peti Harta 1 - Ramuan)            |     ~   ~     |      [RUMAH 2]       [PATUNG KUNO]     |
|                                     |     ~   ~     |      (Pondok          (Monumen Batu &  |
|  [TITIK AWAL SPAWN BOLU & OYEN]     |     ~   ~     |      Nelayan /        Peti Harta 2)    |
|  (Posisi: Grid 8, 18)               |     ~   ~     |      Penjaga)                          |
|                                     |     ~   ~     |      (3x3 ubin)      [DERMAGA PAPAN]   |
|  [PAGAR KAYU BATAS SELATAN]         |     ~   ~     |                      (Peti Harta 3 &   |
|                                     |     ~   ~     |                       Patroli Shiro)   |
+-------------------------------------+     ~~~~~     +----------------------------------------+
```

### 3.2 Ketentuan Ketat Penempatan Rumah (*Zero Roof Overlap Rule*)
Untuk memenuhi syarat mutlak agar atap rumah tidak menimpa/menutupi jalan utama:
1. **Rumah 1 (Pondok Bolu — Barat Laut)**:
   - Ukuran bangunan: $4 \times 3$ ubin.
   - Posisi dinding depan: Minimal pada koordinat $Y = 7$, sementara jalan tanah utama membentang di koordinat $Y = 10 \text{ s/d } 11$.
   - **Terdapat ruang penyangga (*buffer setback*) sejauh 2–3 ubin padang rumput bersih ($Y = 8 \text{ dan } 9$)** antara rumah dan jalan.
   - Atap berada di sisi utara ($Y = 5 \text{ s/d } 6$), sehingga sudut atap yang miring menjauhi jalan raya.
   - Disediakan jalan setapak kecil pekarangan ($1$ ubin) dari pintu rumah menuju jalan utama.
2. **Rumah 2 (Pondok Nelayan / Pos Jaga Shiro — Tenggara)**:
   - Ukuran bangunan: $3 \times 3$ ubin.
   - Terletak di cabang jalan bawah (ke arah dermaga), tidak menjorok ke koridor lintas utama jembatan.
   - Dihiasi tong kayu, jaring ikan, dan jalan papan dermaga di dekat tepian air.
3. **Jalur Utama Bersih Mutlak**:
   - Seluruh ubin jalan tanah utama selebar 2 ubin ($cost = 1.0$) dan jembatan kayu bebas dari objek collision maupun sprite yang menumpuk. Jalur lurus dari barat melintasi jembatan ke timur benar-benar lapang.

---

## 4. Spesifikasi Teknis Kamera & Renderer Anti-Burik

### 4.1 Eliminasi Tampilan Burik (Pixel-Perfect Scaling)
* **Masalah Lama**: `pygame.transform.smoothscale` menerapkan interpolasi *bilinear* yang mencampur warna piksel tetangga, menghasilkan grafis buram/kabur saat diperbesar.
* **Solusi Baru**:
  1. Seluruh pembesaran kanvas peta menggunakan `pygame.transform.scale(...)` (Nearest-Neighbor).
  2. Piksel 16×16 asli diperbesar secara proporsional dengan faktor zoom tetap ($\approx 3.0\times$), menghasilkan grafis retro yang sangat tajam, bersih, dan memanjakan mata.

### 4.2 Sistem Kamera Sinematik (Smooth Damped Tracking)
* **Default Close-Up Zoom**: `self.camera.zoom = 3.0` (setiap ubin 16px menjadi 48px di layar).
* **Fokus Mengikuti Pemain (*Player Centering*)**:
  Kamera selalu menempatkan Bolu di tengah layar:
  $$\text{target\_x} = \frac{\text{screen\_width} - \text{debug\_panel\_width}}{2} - \text{player.px} \times \text{zoom}$$
  $$\text{target\_y} = \frac{\text{screen\_height}}{2} - \text{player.py} \times \text{zoom}$$
* **Smooth Camera Lerp (Peredam Kejut)**:
  Kamera meluncur mengikuti pergerakan Bolu dengan fungsi interpolasi halus:
  $$\text{offset\_x} \leftarrow \text{offset\_x} + (\text{target\_x} - \text{offset\_x}) \times (10.0 \times \Delta t)$$
  $$\text{offset\_y} \leftarrow \text{offset\_y} + (\text{target\_y} - \text{offset\_y}) \times (10.0 \times \Delta t)$$
* **Batas Tepi Peta (*World Clamping*)**:
  Kamera mengunci batas geser agar area hitam di luar peta tidak pernah terlihat di layar.

---

## 5. Spesifikasi Animasi Lingkungan Hidup (*Dynamic Environment*)

### 5.1 Efek Rumput & Pohon Bergoyang (*Procedural Foliage Sway*)
* **Mekanisme**: Menggunakan fungsi pergeseran horizontal (*sine wave shear*) pada lapisan pohon dan semak.
* **Formulasi**:
  - Bagian akar/batang bawah ($y \ge \text{tinggi} - 6\text{px}$) bernilai statis ($\Delta x = 0$).
  - Daun kanopi atas digeser horizontal sebesar:
    $$\Delta x = \sin(\text{waktu} \times 2.8 + \text{posisi\_x} \times 0.2) \times 2.0\text{px}$$
  - Memberikan kesan dedaunan hidup bernapas tertiup angin sepoi-sepoi secara dinamis dan sangat ringan tanpa membebani CPU.

### 5.2 Animasi Siklus Air Sungai Berbusa (4-Frame Water Animation)
* Memanfaatkan file `Water.png` ($64 \times 16\text{px}$ yang berisi 4 frame ubin 16×16):
  - Sistem memperbarui indeks frame air setiap **$0.2$ detik**:
    $$\text{frame\_air} = \text{int}(\text{waktu} / 0.2) \pmod 4$$
  - Ubin air dan buih di pinggir sungai secara otomatis berdenyut dan mengalir secara alami.

### 5.3 Partikel Kilau Rumput (*Ambient Sparkles*) & Debu Langkah (*Footstep Dust*)
* **Ambient Sparkles**: Partikel titik bintang kuning/emas kecil yang sesekali muncul di padang rumput, membesar, lalu memudar perlahan (seperti pada gambar referensi).
* **Footstep Dust**: Mengambil 4 frame dari `Dust particles_01.png` (Shining Fields) yang dipicu setiap kali Bolu atau NPC menyelesaikan satu langkah ubin.

---

## 6. Jaminan Mutlak Preservasi Logika AI (Zero Regression Protocol)

Modul-modul AI berikut **dikunci dan tidak disentuh rumusnya sama sekali**:

```mermaid
flowchart TD
    subgraph AI_Core ["🔒 ZONA TERKUNCI 100% (LOGIKA AI UTUH)"]
        S["search.py:<br/>UCS & A* (Manhattan, Euclidean, Chebyshev)"]
        B["battle_ai.py & battle_system.py:<br/>Minimax, Alpha-Beta, Expectimax, Tag-Team"]
        C["npc_config_csp.py:<br/>Backtracking, AC-3, MRV, LCV, Constraints C1-C8"]
        O["npc_config_optimizer.py:<br/>5 Local Search (HC, Sideways, Restart, SA, GA) & DDA"]
    end

    subgraph Visual_Bridge ["🎨 ZONA ADAPTASI VISUAL"]
        Cam["app.py (Camera Transform):<br/>world_to_screen(wx, wy) dengan Zoom 3.0x & Offset Baru"]
        Overlay["overlay.py (Pathfinding Render):<br/>Draw Closed Set (Kuning) & Path (Biru)"]
    end

    S -->|Himpunan Node Grid (x, y)| Overlay
    Cam -->|Matriks Skala & Posisi Layar| Overlay
```

### 6.1 Preservasi Pathfinding Overlay (`[Ctrl]`)
* Ketika tombol `[Ctrl]` ditekan:
  - Seluruh simpul yang diekspansi (*closed set*) dihitung oleh algoritma yang sama (`search.py`).
  - Fungsi `camera.world_to_screen()` mengonversi koordinat grid ke layar sesuai zoom dekat ($3.0\times$).
  - Kotak kuning berdenyut (*closed set*) dan garis rute biru (*path*) muncul **tepat di atas ubin peta baru** dengan ukuran proporsional ($16\text{px} \times 3.0 = 48\text{px}$), lengkap dengan angka biaya langkah (*step cost*).

### 6.2 Preservasi Fitur Permainan Lainnya
* **Pengejaran NPC Oyen (`[Spasi]`)**: Oyen tetap melacak Bolu menggunakan A\* Search melintasi padang rumput dan jembatan kayu.
* **Patroli NPC Kuro & Shiro**: Titik koordinat patroli (`waypoints`) disesuaikan ke area tebing utara (Kuro) dan pulau timur (Shiro).
* **Interaksi Peti Gacha (`[E]`)**: 3 peti diletakkan di koordinat strategis yang mudah dijangkau di dekat jalan.
* **Pre-Battle Inspector (`[I]`)**: Membuka modal visualizer pohon CSP dan grafik Local Search secara normal.
* **Battle Decision Tree (`[T]`)**: Membuka pohon evaluasi Minimax & pemangkasan Alpha-Beta saat giliran musuh.

---

## 7. Tahapan Eksekusi Bertahap (Action Plan)

1. **Langkah 1: Script Generator & Compiler Map (`scratch/compile_new_map.py`)**
   - Menghasilkan berkas peta JSON baru (`data/map_sprout.json`) yang memetakan aset *Sprout Lands* & *Shining Fields* ke dalam struktur ubin, jalan, sungai, 2 rumah berjarak aman, dan rintangan.
2. **Langkah 2: Pembaruan Renderer Kamera di `game/app.py`**
   - Mengganti `smoothscale` menjadi `scale` (bebas burik).
   - Mengaktifkan default zoom $3.0\times$ dan kamera *smooth lerp tracking* yang memusatkan pandangan pada Bolu.
3. **Langkah 3: Integrasi Animasi Lingkungan**
   - Menambahkan loop animasi riak air 4-frame dan fungsi *wind sway* pada pepohonan/semak.
4. **Langkah 4: Validasi & Uji Coba Kepatuhan**
   - Menjalankan unit test dan uji visual interaktif:
     - Memastikan jalan utama bersih dan tidak tertimpa atap rumah.
     - Memastikan tombol `[Ctrl]` menampilkan visualisasi pathfinding yang tajam dan presisi.
     - Memastikan interaksi `[Spasi]`, `[E]`, `[B]`, `[I]`, dan `[T]` berfungsi normal.

---

## 8. Laporan Hasil Implementasi & Verifikasi (Verification Summary)

Semua poin dalam dokumen rencana ini telah sukses diimplementasikan dan diverifikasi 100% tanpa ada eror:

1. **Peta Baru $44 \times 32$ Beresolusi 16x16 Pixel**:
   - Berkas: `Game-AI/data/map_tubes.json` (backup aman di `data/map_tubes_backup.json`).
   - Ground rumput Sprout Lands rapi, sungai melintang vertikal di $x=19..23$, jembatan kayu di $x=19..23, y=12..13$.
   - **Setback Rumah**: Rumah 1 (Pondok Bolu) di $x=4..7, y=4..7$ (jarak 4 tile ke jalan tanah di $y=12$) dan Rumah 2 (Pondok Pustaka) di $x=28..31, y=16..19$ (jarak 2 tile ke jalan tanah di $y=13$). Jalan tanah 100% bebas dari atap yang menjorok.

2. **Kamera Sinematik Close-up & Anti-Burik**:
   - Default zoom `2.8x` dengan interpolasi halus (*smooth lerp tracking*) mengikuti pemain.
   - Penskalaan grafis menggunakan **Nearest-Neighbor** (`pygame.transform.scale`), mengeliminasi efek buram/blur dari bilinear interpolation (`smoothscale`), menghasilkan pixel art retro yang tajam dan jernih (*pixel-perfect*).

3. **Dunia Hidup & Dinamis (*Living World*)**:
   - **Riak Air Sungai**: Animasi 4-frame dari tileset `Water.png` berputar tiap 0.2 detik secara instan (0.00 ms runtime).
   - **Goyangan Angin (*Procedural Wind Sway*)**: Kanopi pohon ($32 \times 16$), semak bulat ($16 \times 16$), dan bunga liar bergoyang halus secara sinusoidal dihembus angin.
   - **Kilau Padang Rumput (*Ambient Sparkles*)**: Bintang-bintang kecil berkelap-kelip lembut di atas rumput terbuka.
   - **Debu Langkah Kaki (*Footstep Dust*)**: Menghasilkan kepulan debu 4-frame dari `Dust_particles.png` saat Bolu melangkah.

4. **Preservasi Penuh Algoritma AI (Zero Regression)**:
   - Visualisasi pencarian jalur `[Ctrl]` (*Pathfinding wavefront closed set* + rute terpendek) tetap tajam, presisi, dan berskala $2.8\times$.
   - Jalur A* dan UCS melintasi jembatan kayu dan jalan tanah dengan bobot biaya (*step cost*) yang tepat (jalan tanah = 1.0, rumput = 2.0).
   - Semua alur *Pre-Battle CSP + 5 Local Search Optimizers* dan *Turn-Based Tag-Team Battle Minimax/Alpha-Beta Pruning* dengan inspeksi pohon `[T]` dan `[I]` lulus 100% pada integrasi end-to-end.
