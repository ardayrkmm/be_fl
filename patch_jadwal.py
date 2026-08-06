import re

def patch_file():
    with open('d:/kmpl/Aplikasi/be_fl_fisio/controller/JadwalController.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern for get_jadwal_hari_ini
    pattern_hari_ini = r'''(            program\.append\({[\s\S]*?"sisi": detail\.sisi,\s*"target": {\s*"set": rule_for_lat\.target_set if rule_for_lat else None,\s*"repetisi": rule_for_lat\.target_repetisi if rule_for_lat else None,\s*"waktu": rule_for_lat\.target_waktu if rule_for_lat else None,\s*"hold_detik": int\(rule_for_lat\.hold_detik\) if \(rule_for_lat and rule_for_lat\.hold_detik is not None\) else 0\s*}\s*}\s*}\))'''
    
    replace_hari_ini = '''            final_set = rule_for_lat.target_set if rule_for_lat else None
            final_rep = rule_for_lat.target_repetisi if rule_for_lat else None
            final_waktu = rule_for_lat.target_waktu if rule_for_lat else None
            final_hold = int(rule_for_lat.hold_detik) if (rule_for_lat and rule_for_lat.hold_detik is not None) else 0

            if kondisi_for_jadwal and kondisi_for_jadwal.durasi_nyeri_minggu is not None:
                durasi = kondisi_for_jadwal.durasi_nyeri_minggu
                if durasi < 2:
                    final_set = 2
                    if final_waktu is not None and final_waktu > 0:
                        final_waktu = 10
                    else:
                        final_rep = 8
                elif 2 <= durasi <= 6:
                    final_set = 3
                    if final_waktu is not None and final_waktu > 0:
                        final_waktu = 20
                    else:
                        final_rep = 12

            program.append({
                "id_jadwal": j.id_jadwal,
                "nama_jadwal": j.nama_jadwal,
                "status": j.status,
                "latihan": {
                    "id_latihan": lat.id_latihan,
                    "nama_latihan": lat.nama_latihan,
                    "deskripsi": lat.deskripsi,
                    "gambar": lat.url_gambar,
                    "video_url": lat.video_url,
                    "sisi": detail.sisi,
                    "target": {
                        "set": final_set,
                        "repetisi": final_rep,
                        "waktu": final_waktu,
                        "hold_detik": final_hold
                    }
                }
            })'''
    
    content = re.sub(pattern_hari_ini, replace_hari_ini, content, count=1)


    # Pattern for get_jadwal_per_fase
    pattern_per_fase = r'''(        if lat\.id_latihan not in latihan_map:\s*latihan_map\[lat\.id_latihan\] = {\s*"id_latihan": lat\.id_latihan,\s*"nama_latihan": lat\.nama_latihan,\s*"deskripsi": lat\.deskripsi,\s*"image_url": lat\.url_gambar,\s*"level": int\(lat\.level\) if lat\.level else 1,\s*"duration": int\(rule\.target_waktu or 0\) if rule else 0,\s*"target": {\s*"set": rule\.target_set if rule else None,\s*"repetisi": rule\.target_repetisi if rule else None,\s*"waktu": rule\.target_waktu if rule else None,\s*"hold_detik": int\(rule\.hold_detik\) if \(rule and rule\.hold_detik is not None\) else 0\s*},\s*"video_url": lat\.video_url,\s*"is_unilateral": lat\.is_unilateral,\s*"sisi": \[\]\s*})'''

    replace_per_fase = '''        if lat.id_latihan not in latihan_map:
            final_set = rule.target_set if rule else None
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
                elif 2 <= durasi <= 6:
                    final_set = 3
                    if final_waktu is not None and final_waktu > 0:
                        final_waktu = 20
                    else:
                        final_rep = 12

            latihan_map[lat.id_latihan] = {
                "id_latihan": lat.id_latihan,
                "nama_latihan": lat.nama_latihan,
                "deskripsi": lat.deskripsi,
                "image_url": lat.url_gambar,
                "level": int(lat.level) if lat.level else 1,
                "duration": int(final_waktu or 0),
                "target": {
                    "set": final_set,
                    "repetisi": final_rep,
                    "waktu": final_waktu,
                    "hold_detik": final_hold
                },
                "video_url": lat.video_url,
                "is_unilateral": lat.is_unilateral,
                "sisi": []
            }'''
            
    content = re.sub(pattern_per_fase, replace_per_fase, content, count=1)


    # Pattern for get_jadwal_semua
    pattern_semua = r'''(              latihan_item = {\s*"id_latihan": lat\.id_latihan,\s*"nama_latihan": lat\.nama_latihan,\s*"deskripsi": lat\.deskripsi,\s*"image_url": lat\.url_gambar,\s*"video_url": lat\.video_url,\s*"level": int\(lat\.level\) if lat\.level else 1,\s*# \S* TARGET LATIHAN\s*"target": {\s*"set": rule\.target_set if rule else None,\s*"repetisi": rule\.target_repetisi if rule else None,\s*"waktu": rule\.target_waktu if rule else None,\s*"hold_detik": int\(rule\.hold_detik\) if \(rule and rule\.hold_detik is not None\) else 0\s*},\s*# \S* DURASI fallback\s*"duration": int\(rule\.target_waktu or 0\) if rule else 0,\s*# \S* PENTING: sisi tidak di-merge\s*"sisi": detail\.sisi,\s*# \S* FLAG\s*"is_unilateral": lat\.is_unilateral,\s*# \S* tracking penting untuk history nanti\s*"id_detail_jadwal": detail\.id_detail,\s*"urutan": detail\.urutan\s*})'''

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
                  elif 2 <= durasi <= 6:
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
    
    print("Done patching JadwalController")

if __name__ == '__main__':
    patch_file()
