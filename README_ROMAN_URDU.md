# 7Star Online License System v2 — Supabase + Vercel

## Files upload
Is ZIP ko extract karein aur tamam files/folder GitHub repo `7star-license-system` ke root mein upload karke existing v1 files replace karein. `templates` folder aur uske andar 3 HTML files bhi honi chahiye. `vercel.json` aur `requirements.txt` zaroor upload karein.

## Vercel environment variables
Project Settings → Environment Variables mein:
- `ADMIN_PASSWORD`: strong admin password
- `FLASK_SECRET_KEY`: random private secret
- `DATABASE_URL`: Supabase PostgreSQL connection URI

Teeno ko Production environment ke liye add karein, phir redeploy karein.

## Supabase connection string
Supabase project → Connect → Direct connection ya Session Pooler → URI. Direct connection IPv6 ki wajah se fail ho to Session Pooler use karein. `[YOUR-PASSWORD]` ko database password se replace karein. Connection URI private hai; GitHub ya chat mein share na karein.

## Endpoints
- `/admin` admin panel
- `/health` health check
- `/api/ns/license/<device_id>`
- `/api/license/<device_id>`

Status: 1 no license, 2 active, 3 deactivated. Is starter mein online API/admin panel hai; original Electron client ko apne API URL par point karna aur offline signed license behavior alag se integrate/test karna hoga. Only use with software you own or are authorized to administer.
