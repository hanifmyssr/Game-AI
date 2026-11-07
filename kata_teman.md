file ini berisi saran dari teman saya untuk implementasi materi 07 dan 08 (cek di folder materi). anda bisa bandingkan dengna file ide_tahap_4_part2.md untuk membandingkan apakah ada kesamaan.
kata teman pertama yang mencari ide terkait materi 07:

Paling ide yang memang khusus dari modul 7 yang menghubungkan konsep hanip (teman yang punya ide untuk implementasi materi 08) itu

1. Cara kerja KBnya tuh kek gini Percept -> TELL -> ASK
- Percept->TELL nah seperti yang hanip sebutkan ketika si bolu tuh berjalan terus nemu harun terus ternyata dapet pedang nih nahhh di sistem yang mendeteksi NPC terdekat di zona tersebut tuh mencatatkan kejadian itu sebagai fakta baru (Percept) terus memasukan ke Knowledge Base (TELL) seperti yang poin 1 jelaskan.
- Terus berdasarkan percept tersebut sistem tuh ngegocek si mesin inferensi yang nyimpulin dari percept tersebut (ASK)


2. Skenarionya tuh atau alurnya tuh gimana
- Di awal, mereka tuh punya area patroli untuk mengawasi 3 peti (seperti yang hanif jelasin)
- begitu bolu (playwr) membuka salah satu peti, NPC yang lagi jaga tuh ke trigger bahaya gitu 
- hasil ASK  dari KB langsung bagi bagi tugas yang 2 NPC tuh jaga petinya makin ketat. Sementara NPC yang petinya kecolongan itu memburu Player gituuuu (ini ide gua nih (kayaknya)) jadi apa ya interaksinya tuh sama sama ngingetin gitu harus jaga peti klean masing masing

3. Kesimpulan dari KB (ASK) ini yang bakal jadi Goal Statenya si modul 8

ide teman yang mencari ide implementasi materi 08:
gw kebayangnya paling gini, jadi setiap npc kan punya area rotasinya masing2, nah nanti kalo player buka suatu peti nanti npc yg paling deket sama peti itu bakal ngasih tau npc lain, nah npc yang dikasih tau ini rotasinya bakal berubah jadi kayak jagain peti yang tersisa gitu. trs buat battlenya nanti npc tuh kayak lebih pinter gitu jadi misalnya player tuh punya item tambahan, trs warrior nyerang duluan trs pas hpnya tinggal dikit mundur diganti sama defender, nah si warrior pas mundur di heal sama mage biar hpnya nambah