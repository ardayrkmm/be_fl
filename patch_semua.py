import re

def patch_semua():
    with open('d:/kmpl/Aplikasi/be_fl_fisio/controller/JadwalController.py', 'r', encoding='utf-8') as f:
        content = f.read()

    pattern_semua = r'''(              latihan_item = {\s*"id_latihan": lat\.id_latihan,\s*"nama_latihan": lat\.nama_latihan,\s*"deskripsi": lat\.deskripsi,\s*"image_url": lat\.url_gambar,\s*"video_url": lat\.video_url,\s*"level": int\(lat\.level\) if lat\.level else 1,\s*# [^\n]* TARGET LATIHAN\s*"target": {\s*"set": rule\.target_set if rule else None,\s*"repetisi": rule\.target_repetisi if rule else None,\s*"waktu": rule\.target_waktu if rule else None,\s*"hold_detik": int\(rule\.hold_detik\) if \(rule and rule\.hold_detik is not None\) else 0\s*},\s*# [^\n]* DURASI fallback\s*"duration": int\(rule\.target_waktu or 0\) if rule else 0,\s*# [^\n]* PENTING: sisi tidak di-merge\s*"sisi": detail\.sisi,\s*# [^\n]* FLAG\s*"is_unilateral": lat\.is_unilateral,\s*# [^\n]* tracking penting untuk history nanti\s*"id_detail_jadwal": detail\.id_detail,\s*"urutan": detail\.urutan\s*})'''

    replace_semua = '''              final_set = rule.target_set if rule else None
              final_rep = rule.target_repetisi if rule else None
              final_waktu = rule.target_waktu if rule else None
              final_hold = int(rule.hold_detik) if (rule and rule.hold_detik is not None) else 0

              if kondisi and kondisi.durasi_nyeri_minggu is not None:
                  durasi = kondisi.durasi_nyeri_minggu
                  if durasi < 2:
                      final_set = 2
                      if final_waktu is not None and final_waktu > 0:
                          final_waktu = 10
                      else:
                          final_rep = 8
                  elif 2 <= durasi <= 4:
                      final_set = 3
                      if final_waktu is not None and final_waktu > 0:
                          final_waktu = 20
                      else:
                          final_rep = 12

              latihan_item = {
                  "id_latihan": lat.id_latihan,
                  "nama_latihan": lat.nama_latihan,
                  "deskripsi": lat.deskripsi,
                  "image_url": lat.url_gambar,
                  "video_url": lat.video_url,
                  "level": int(lat.level) if lat.level else 1,

                  "target": {
                      "set": final_set,
                      "repetisi": final_rep,
                      "waktu": final_waktu,
                      "hold_detik": final_hold
                  },

                  "duration": int(final_waktu or 0),
                  "sisi": detail.sisi,
                  "is_unilateral": lat.is_unilateral,
                  "id_detail_jadwal": detail.id_detail,
                  "urutan": detail.urutan
              }'''
              
    content = re.sub(pattern_semua, replace_semua, content, count=1)
    
    with open('d:/kmpl/Aplikasi/be_fl_fisio/controller/JadwalController.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Done patching get_jadwal_semua")

if __name__ == '__main__':
    patch_semua()
