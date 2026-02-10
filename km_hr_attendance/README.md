# KM HR Attendance

## Timezone Behavior Analysis & Fix

### Problem
Odoo menyimpan semua datetime field dalam database sebagai **UTC** dan secara otomatis mengkonversi ke timezone user saat ditampilkan di UI.

### Impact pada Attendance Data
Jika data attendance disimpan tanpa timezone conversion:
```
Input: 08:00 (WIB/UTC+7)
Stored: 08:00 (dianggap UTC oleh Odoo)
Displayed: 08:00 + 7 jam = 15:00 ❌ SALAH
```

### Root Cause
1. **Mock Data Generator** (`util_hr_mock_data_gen`) awalnya menyimpan waktu "as-is" tanpa timezone conversion
2. **Odoo Database** menyimpan datetime sebagai UTC tanpa timezone info
3. **Odoo UI** otomatis menambah offset timezone user (+7 untuk Jakarta) saat display
4. **Result**: Data yang seharusnya 08:00 WIB ditampilkan sebagai 15:00 WIB

### Solution Implemented

#### 1. Fix di Mock Data Generator
File: `util_hr_mock_data_gen/models/attendance_generator.py`

```python
# Subtract 7 hours to convert from WIB (UTC+7) to UTC
check_in_dt = check_in_dt - timedelta(hours=7)
check_out_dt = check_out_dt - timedelta(hours=7)
```

**Flow setelah fix:**
```
Input: 08:00 (WIB/UTC+7)
Stored: 01:00 (UTC) ← dikurangi 7 jam
Displayed: 01:00 + 7 jam = 08:00 (WIB) ✅ BENAR
```

#### 2. Override Views di km_hr_attendance
File: `km_hr_attendance/views/hr_attendance_views.xml` & `km_hr_attendance/models/hr_attendance.py`

**Form View:**
- **Hidden**: Original `check_in` dan `check_out` fields (yang auto-convert timezone)
- **Shown**: `check_in_utc` dan `check_out_utc` (raw UTC values dari database)
- **Labels**: Tetap "Check In" dan "Check Out" untuk user-friendly

**Tree/List View:**
- **Replaced**: `check_in` dan `check_out` diganti dengan UTC variants
- **Result**: List view sekarang menampilkan raw values tanpa timezone conversion

**Kenapa perlu:**
- Menghindari double conversion (generator -7 jam, Odoo +7 jam = kembali ke 08:00)
- User melihat waktu yang sebenarnya disimpan/diinput
- Konsisten dengan data yang di-generate mock

Ditambahkan computed fields di model:
- `check_in_utc`: Raw UTC time di database (string format)
- `check_out_utc`: Raw UTC time di database (string format)

**Note**: Fields ini sekarang digunakan sebagai **primary display fields**, bukan hanya untuk debugging.

### Technical Details
- **Database timezone**: UTC (default Odoo)
- **User timezone**: Asia/Jakarta (UTC+7)
- **Conversion formula**: `local_time - timedelta(hours=7)` sebelum simpan ke database
- **Display**: Raw UTC values (no auto conversion by Odoo)

### Important Notes
- ✅ Manual attendance input via Odoo UI **sudah benar** - Odoo otomatis handle timezone conversion
- ✅ Mock data generator **sudah diperbaiki** - manual conversion ditambahkan (-7 jam)
- ✅ Views **sudah override** - menampilkan raw UTC values untuk konsistensi
- ⚠️ Jika timezone user berubah, perlu adjust offset di generator
- 🔧 Untuk timezone selain UTC+7, ubah `timedelta(hours=7)` sesuai offset

### Testing
1. Generate mock data dengan waktu 08:00 - 17:00
2. Check di list view: harus tampil raw UTC (01:00 - 10:00)
3. Buka form view: tampil raw UTC dengan label "Check In" / "Check Out"
4. Verify data tersimpan dengan benar: 08:00 input → 01:00 stored

### Related Modules
- `util_hr_mock_data_gen`: Mock data generator dengan timezone fix
- `km_hr_attendance`: Base extension dengan view overrides & UTC display
- `hr_attendance`: Odoo core module
