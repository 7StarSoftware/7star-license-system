# 7Star Online License System (v1)

Ye package aapke **apne software** ke liye online license API aur admin panel hai. Ye kisi third-party app ki license bypass karne ke liye nahi hai.

## Features
- Admin login
- Device ID par license create/update
- Expiry date online change
- Activate / deactivate / delete
- API routes:
  - `/api/ns/license/<device_id>`
  - `/api/license/<device_id>`
- License na milne par status `1`; active ke liye `2`; deactivated ke liye `3`
- JSON response mein `license_code`, `expiry_date`, `status`, `plan`, `current_date` etc.

## Local test
Python 3.10+ install karein, phir terminal mein:
```bash
pip install -r requirements.txt
```
Environment variables set karein:
```bash
# Windows PowerShell
$env:ADMIN_PASSWORD="apna-mazboot-password"
$env:FLASK_SECRET_KEY="apni-lambi-random-secret"
python app.py
```
Browser mein `http://127.0.0.1:5000/admin` kholein.

## Online deploy (Render + persistent disk)
1. Is ZIP ko extract karein aur files apne GitHub repository mein upload karein.
2. Render par **New Web Service** banayein aur GitHub repository connect karein.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Persistent disk mount path `/var/data` aur size 1 GB set karein.
6. Environment variables set karein:
   - `ADMIN_PASSWORD`: unique strong password
   - `FLASK_SECRET_KEY`: long random secret
   - `LICENSE_DB_PATH`: `/var/data/licenses.db`
7. Deploy ke baad `/admin` open karke licenses manage karein.

`render.yaml` blueprint bhi included hai. Agar Render plan persistent disk support nahi karta, database reboot/redeploy par reset ho sakta hai; persistent storage zaroor configure karein.

## Important compatibility note
API response ka shape emulator jaisa rakha gaya hai, magar ye **aapke apne client software** ke saath integrate karna hoga. Sirf API host karne se existing software automatically is server ko use nahi karega: client mein API base URL aur response handling configure honi chahiye. Agar client local `lic.json` se online response ko overwrite karta hai, to woh behavior bhi apne code mein theek karna hoga.

## Security notes
- Admin password aur secret GitHub code mein kabhi hardcode na karein.
- Production mein HTTPS use karein.
- Device ID ko apne app se generate karein; secret keys client app mein embed na karein.
- Client-side offline license ko tamper-proof banane ke liye signed license verification add karni chahiye; ye starter package basic online API/admin panel hai, full cryptographic offline activation nahi.
