with open('controller/JadwalController.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_block = False
for i, line in enumerate(lines):
    if line.startswith('# @latihanuser_bp.route("/jadwal/semua", methods=["GET"])'):
        in_block = True
    
    if in_block:
        if line.startswith('# '):
            lines[i] = line[2:]
        elif line.startswith('#\n'):
            lines[i] = line[1:]
            
        if 'code": "GET_JADWAL_SEMUA_SUCCESS"' in line:
            # We are near the end. The block ends at the next '    }), 200'
            pass
            
        if in_block and line.startswith('    }), 200'):
            in_block = False

with open('controller/JadwalController.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
