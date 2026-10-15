# 📋 Laporan Identifikasi & Resolusi Masalah — Bakekok Game AI

> **Status Dokumen**: ✅ **Seluruh Masalah Telah Diperbaiki & Diverifikasi**  
> **Tanggal Pembaruan**: 14 Oktober 2026  
> **Target File Utama**: `game/app.py`  
> **Target File Terkait**: `game/battle_system.py`, `scratch/analyze_map.py`  

---

## 📌 Ringkasan Eksekutif

Setelah dilakukan audit kode secara menyeluruh terhadap berkas [game/app.py](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py) serta keterhubungannya dengan sistem pertarungan [game/battle_system.py](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py) dan modul lainnya, ditemukan **9 poin masalah**. 

Kini **seluruh 9 masalah telah berhasil diperbaiki** dengan rincian berikut:

---

## 🚨 Bagian 1: Masalah pada `game/app.py`

### 1. Pemain Terjebak di Layar Pertarungan Setelah Kemenangan Final
* **Tingkat Keparahan**: 🔴 **Kritis** (Game-Breaking / Freeze)
* **Status**: ✅ **Telah Diperbaiki**
* **Lokasi Kode**: [`game/app.py:1274-1280`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L1274-L1280) (`_dismiss_loot_modal`)
* **Masalah**:
  Saat pemain memenangkan duel final dan menutup modal rampasan perang, blok `else:` hanya melepaskan status `is_locked`, namun tidak memanggil `self.exit_battle()`, menyebabkan layar tetap berada di arena pertempuran tanpa musuh.
* **Solusi yang Diterapkan**:
  Ditambahkan pemanggilan `self.exit_battle()` ketika `modal.get("is_final", False)` bernilai `True`. Game kini kembali mulus ke peta eksplorasi.

---

### 2. Bentrok Input (Z-Order Clashing) pada Modal Decision Tree
* **Tingkat Keparahan**: 🟠 **Tinggi** (UI Input Clashing)
* **Status**: ✅ **Telah Diperbaiki**
* **Lokasi Kode**: [`game/app.py:541-588`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L541-L588) (`_handle_events`)
* **Masalah**:
  Event mouse wheel dan mouse button down mengecek tombol di lapisan bawah (seperti tombol log atau toggle modal) sebelum memeriksa modal Decision Tree.
* **Solusi yang Diterapkan**:
  Pemeriksaan `self.overlay.tree_overlay.visible` dan `tree_overlay.handle_event(event)` kini diprioritaskan di baris pertama event `MOUSEWHEEL` dan `MOUSEBUTTONDOWN` pada mode `BATTLE`. Input hanya diteruskan ke elemen di belakangnya jika modal tidak sedang aktif.

---

### 3. Loop Pertarungan Berulang (NPC yang Dikalahkan Tidak Respawn/Pindah)
* **Tingkat Keparahan**: 🟠 **Tinggi** (Gameplay Loop)
* **Status**: ✅ **Telah Diperbaiki**
* **Lokasi Kode**: [`game/app.py:437`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L437) (`enter_pre_battle`) & [`game/app.py:483-492`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L483-L492) (`exit_battle`)
* **Masalah**:
  Argumen `leader_npc` tidak disimpan di `enter_pre_battle`, dan saat pemain menang duel, NPC musuh tetap berada di koordinat yang sama di sebelah pemain sehingga memicu pertempuran berulang terus-menerus.
* **Solusi yang Diterapkan**:
  1. `self.current_encounter_npc = leader_npc` disimpan saat memasuki fase pertempuran.
  2. Pada `exit_battle()`, jika `self.battle_system.winner == "PLAYER"`, modul memanggil `enc_npc._spawn()` untuk memindahkan NPC ke posisi spawn awal/jauh, serta mereset status `chasing = False`, `moving = False`, dan `path = []`.

---

### 4. Missing Import Tipe `Optional, Dict, Any` (Potensi Crash Python < 3.14)
* **Tingkat Keparahan**: 🟠 **Tinggi** (Kompatibilitas Runtime)
* **Status**: ✅ **Telah Diperbaiki**
* **Lokasi Kode**: [`game/app.py:5`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L5)
* **Masalah**:
  Type hints `Optional, Dict, Any` digunakan di method signature `_on_npc_tag_in` tanpa di-import dari modul `typing`, berpotensi melempar `NameError` pada versi Python standar.
* **Solusi yang Diterapkan**:
  Menambahkan import `from typing import Optional, Dict, Any, List, Tuple` di bagian paling atas berkas `game/app.py`.

---

### 5. Artefak Rampasan Perang Tidak Muncul di Tas Inventori Player (Pre-Battle Screen)
* **Tingkat Keparahan**: 🟡 **Sedang** (Visual Glitch)
* **Status**: ✅ **Telah Diperbaiki**
* **Lokasi Kode**: [`game/app.py:1600-1618`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L1600-L1618)
* **Masalah**:
  Pengecekan `if it in self.item_images` gagal karena `inventory` menyimpan nama lengkap item (misal `"Pedang Ksatria Oyen"`), sedangkan kunci `item_images` adalah ID teknis seperti `"item_sword"`.
* **Solusi yang Diterapkan**:
  Menambahkan kamus pemetaan nama `name_to_key` yang menerjemahkan nama item rampasan duel maupun item dari peti ke ID gambar yang valid di `self.item_images`.

---

### 6. Desain Penamaan Karakter: NPC Pengejar Utama Bernama "Bolu"
* **Tingkat Keparahan**: 🟡 **Sedang** (Klarifikasi Desain Sistem)
* **Status**: ✅ **Telah Diselaraskan**
* **Lokasi Kode**: [`game/app.py:192-193`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L192-L193) & [`game/app.py:824-826`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L824-L826)
* **Klarifikasi Desain Pengembang**:
  Sesuai konsep awal game *BoluKesepian*, NPC kucing utama yang mengejar pemain memang bernama **Bolu**, sedangkan pemain adalah pengembara tanpa nama (*Hero*). Oleh karena itu, badge offscreen indicator yang menampilkan `"🐱 Bolu"` adalah benar dan disengaja.
* **Solusi yang Diterapkan**:
  Inisialisasi NPC pengejar utama di `game/app.py` diselaraskan menjadi `name="Bolu"`, dan label indikator offscreen menggunakan format dinamis `f"🐱 {self.npc.name} ({dist_grid} meter)"` sehingga konsisten dengan identitas NPC.

---

### 7. Potensi Nilai Lebar Negatif pada HP Bar Skuad Lawan saat Resize Window
* **Tingkat Keparahan**: 🟡 **Sedang** (Visual Glitch)
* **Status**: ✅ **Telah Diperbaiki**
* **Lokasi Kode**: [`game/app.py:1664-1667`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/app.py#L1664-L1667)
* **Masalah**:
  Kalkulasi `squad_area_w - 280` dapat bernilai $\le 0$ saat jendela di-resize ke resolusi lebih kecil, memicu anomali visual pada `pygame.draw.rect`.
* **Solusi yang Diterapkan**:
  Menerapkan batas bawah aman:
  ```python
  m_hp_w = max(40, min(160, squad_area_w - 280))
  m_fill = max(0, min(m_hp_w, int((m.max_hp / 120.0) * m_hp_w)))
  ```

---

## ⚙️ Bagian 2: Masalah pada Modul Pendukung Terkait

### 8. `is_locked` & `last_loot` Tidak Di-reset pada `reset_with_squad()` di `battle_system.py`
* **Tingkat Keparahan**: 🔴 **Kritis** (Unresponsive Duel)
* **Status**: ✅ **Telah Diperbaiki**
* **Lokasi Kode**: [`game/battle_system.py:212-215`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/game/battle_system.py#L212-L215)
* **Masalah**:
  Saat duel di-reset via `reset_with_squad()`, status `self.is_locked` dan `self.last_loot` tidak dikembalikan ke nilai awal, sehingga jika duel sebelumnya terkunci oleh animasi, pemain tidak dapat memilih aksi apa pun.
* **Solusi yang Diterapkan**:
  Menambahkan `self.is_locked = False` dan `self.last_loot = None` secara eksplisit di dalam `reset_with_squad()`.

---

### 9. File Rusak / Obsolete di Folder Scratch: `scratch/analyze_map.py`
* **Tingkat Keparahan**: ⚪ **Rendah** (Dev Tooling)
* **Status**: ✅ **Telah Diperbaiki**
* **Lokasi Kode**: [`scratch/analyze_map.py:3-5`](file:///c:/Users/Pavilion/Documents/DOKUMEN%20TUGAS/Kuliah/Tubes_ai_kel7/Fix_nya/Game-AI/scratch/analyze_map.py#L3-L5)
* **Masalah**:
  Skrip mencoba membuka `data/map.json` yang tidak ada di repositori (`data/map_tubes.json`).
* **Solusi yang Diterapkan**:
  Memperbarui pemanggilan file target agar memeriksa keberadaan `data/map_tubes.json` secara dinamis.

---

## 📊 Matriks Status Akhir

| No | Modul / File | Lokasi Baris | Kategori Masalah | Status Terkini |
|:---:|---|---|---|:---:|
| 1 | `game/app.py` | L1274-1280 | Kemenangan final otomatis keluar ke map (`exit_battle`) | ✅ Selesai |
| 2 | `game/battle_system.py` | L212-215 | `is_locked` & `last_loot` di-reset di `reset_with_squad` | ✅ Selesai |
| 3 | `game/app.py` | L541-588 | Z-Order event mouse pada Decision Tree Modal & log | ✅ Selesai |
| 4 | `game/app.py` | L437, L483 | Respawn NPC yang kalah (mencegah loop duel) | ✅ Selesai |
| 5 | `game/app.py` | L5 | Import `typing` (`Optional, Dict, Any`, dll.) | ✅ Selesai |
| 6 | `game/app.py` | L1600-1618 | Resolusi ikon item rampasan perang di tas inventori | ✅ Selesai |
| 7 | `game/app.py` | L192, L824 | Desain penamaan: NPC utama Bolu & Player Hero | ✅ Selesai |
| 8 | `game/app.py` | L1664-1667 | Batas bawah aman lebar HP bar skuad lawan | ✅ Selesai |
| 9 | `scratch/analyze_map.py` | L3-5 | Path file peta valid (`data/map_tubes.json`) | ✅ Selesai |
