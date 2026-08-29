"""End-to-end smoke test of the v2 operator flow over real HTTP.

Walks the exact path an operator takes, including the two refusals the whole
rewrite is about: you cannot start a second lead without a handover comment, and
you cannot see a lead somebody else is holding.

    docker compose cp backend/tests/smoke_e2e.py backend:/app/smoke_e2e.py
    docker compose exec backend python smoke_e2e.py

Not collected by pytest (no `test_` prefix, and it needs a live server).

WRITES TO THE DATABASE. It creates two operators and drives two real leads
through the full lifecycle, so run it against a scratch database -- or undo it
afterwards, noting the ids it reports:

    DELETE FROM lead_events     WHERE company_id IN (<a>, <b>);
    DELETE FROM lead_states     WHERE company_id IN (<a>, <b>);
    DELETE FROM company_reviews WHERE company_id IN (<a>, <b>);
    DELETE FROM users WHERE username LIKE 'smoke\_%';
"""

import os
import sys

import httpx

BASE = os.getenv("SMOKE_BASE", "http://localhost:8000/api")
ADMIN = (os.getenv("INITIAL_ADMIN_USERNAME", "admin"), os.getenv("INITIAL_ADMIN_PASSWORD", "admin123"))

failures: list[str] = []


def check(label: str, ok: bool, extra: str = "") -> None:
    print(f"  {'OK  ' if ok else 'FAIL'} {label}{(' — ' + extra) if extra and not ok else ''}")
    if not ok:
        failures.append(label)


def login(client: httpx.Client, username: str, password: str) -> str:
    r = client.post(f"{BASE}/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def ensure_operator(client: httpx.Client, admin_token: str, username: str) -> None:
    client.post(
        f"{BASE}/operators",
        headers=auth(admin_token),
        json={"username": username, "password": "smoke-pass-123", "full_name": username.title()},
    )


def main() -> int:
    with httpx.Client(timeout=20) as c:
        admin_token = login(c, *ADMIN)
        print("admin login OK")

        for name in ("smoke_op1", "smoke_op2"):
            ensure_operator(c, admin_token, name)
        op1 = login(c, "smoke_op1", "smoke-pass-123")
        op2 = login(c, "smoke_op2", "smoke-pass-123")
        print("operator logins OK\n")

        # --- the queue -----------------------------------------------------
        r = c.get(f"{BASE}/leads", headers=auth(op1), params={"status": "new", "limit": 5})
        check("GET /leads javob berdi", r.status_code == 200, r.text[:200])
        if r.status_code != 200:
            return 1
        body = r.json()
        check("javobda items/total/counts bor", {"items", "total", "counts"} <= set(body))
        check("counts beshta statusni qamraydi", {"new", "in_progress", "waiting", "approved", "rejected"} <= set(body["counts"]))
        if len(body["items"]) < 2:
            print("\n  (bazada 2 ta yangi lead yo'q — qolgan tekshiruvlar o'tkazib yuborildi)")
            return 1
        a, b = body["items"][0]["id"], body["items"][1]["id"]
        print(f"  (bu ishga tushirish {a} va {b} raqamli leadlarga yozadi)")
        check("yangi lead statusi 'new'", body["items"][0]["status"] == "new")

        # --- claiming ------------------------------------------------------
        r = c.post(f"{BASE}/leads/{a}/start", headers=auth(op1))
        check("ishni boshlash 200", r.status_code == 200, r.text[:200])
        check("status 'in_progress' ga o'tdi", r.json().get("status") == "in_progress")
        check("available_actions serverdan keldi", "pause" in r.json().get("available_actions", []))

        # --- exclusivity ---------------------------------------------------
        r = c.get(f"{BASE}/leads/{a}", headers=auth(op2))
        check("boshqa operatorga 404 (403 emas)", r.status_code == 404, f"status={r.status_code}")

        r = c.get(f"{BASE}/leads", headers=auth(op2), params={"status": "new", "limit": 100})
        check("band lead boshqaning ro'yxatida yo'q", a not in [i["id"] for i in r.json()["items"]])

        r = c.get(f"{BASE}/leads/{a}", headers=auth(admin_token))
        check("admin band leadni ko'ra oladi", r.status_code == 200)

        # --- the handover rule ---------------------------------------------
        r = c.post(f"{BASE}/leads/{b}/start", headers=auth(op1))
        detail = r.json().get("detail", {})
        check("ikkinchi lead 409 handover_required beradi", r.status_code == 409 and detail.get("code") == "handover_required", r.text[:200])
        check("xato javobida joriy ish nomi bor", detail.get("active_company_id") == a)

        r = c.post(f"{BASE}/leads/{b}/switch", headers=auth(op1), json={"from_company_id": a, "note": "   "})
        check("bo'sh izoh bilan o'tish rad etildi", r.status_code in (409, 422), f"status={r.status_code}")

        r = c.get(f"{BASE}/leads/{a}", headers=auth(op1))
        check("rad etilgandan keyin eski lead hali ham menda", r.json().get("status") == "in_progress")

        r = c.post(
            f"{BASE}/leads/{b}/switch",
            headers=auth(op1),
            json={"from_company_id": a, "note": "3 marta qo'ng'iroq qildim, javob yo'q"},
        )
        check("izoh bilan o'tish 200", r.status_code == 200, r.text[:200])

        r = c.get(f"{BASE}/leads/{a}", headers=auth(op1))
        old = r.json()
        check("eski lead 'waiting' ga o'tdi", old.get("status") == "waiting")
        check("eski lead egasi bo'shadi", old.get("assignee_id") is None)
        handover = [e for e in old.get("events", []) if e["type"] == "handover"]
        check("handover izohi tarixga tushdi", len(handover) == 1 and "javob yo'q" in (handover[0]["note"] or ""))

        # --- the next operator picks it up ---------------------------------
        r = c.get(f"{BASE}/leads", headers=auth(op2), params={"status": "waiting", "limit": 100})
        row = next((i for i in r.json()["items"] if i["id"] == a), None)
        check("qoldirilgan lead boshqaga ko'rinadi", row is not None)
        check("oxirgi izoh ro'yxat qatorida ko'rinadi", bool(row and row.get("last_note")))
        check("izoh muallifi ko'rsatilgan", bool(row and row.get("last_note_by")))

        # --- finishing -----------------------------------------------------
        r = c.post(f"{BASE}/leads/{b}/finish", headers=auth(op1), json={"result": "approved", "note": None})
        check("to'ldirilmagan lead tasdiqlanmadi", r.status_code == 409 and r.json()["detail"]["code"] == "fields_incomplete", r.text[:200])

        r = c.patch(
            f"{BASE}/leads/{b}/draft",
            headers=auth(op1),
            json={"website": {"available": True, "comment": "sayti bor"}, "lms": {"available": False, "comment": "yo'q"}},
        )
        check("qoralama saqlandi", r.status_code == 200, r.text[:200])

        r = c.get(f"{BASE}/leads/{b}", headers=auth(op1))
        check("qoralama status o'zgartirmadi", r.json()["status"] == "in_progress")
        check("qoralama tarixga yozuv qo'shmadi", not any(e["type"] == "comment" for e in r.json()["events"]))
        check("endi tasdiqlash mumkin", "approve" in r.json()["available_actions"])

        r = c.post(f"{BASE}/leads/{b}/finish", headers=auth(op1), json={"result": "approved", "note": None})
        check("tasdiqlash 200", r.status_code == 200 and r.json()["status"] == "approved", r.text[:200])

        # --- correcting your own mistake, no admin ---------------------------
        r = c.post(f"{BASE}/leads/{b}/reopen", headers=auth(op1), json={"note": ""})
        check("sababsiz qayta ochish rad etildi", r.status_code in (409, 422))

        r = c.post(f"{BASE}/leads/{b}/reopen", headers=auth(op1), json={"note": "LMS ni xato belgilabman"})
        check("sabab bilan qayta ochish 200 (admin ruxsatisiz)", r.status_code == 200 and r.json()["status"] == "in_progress", r.text[:200])
        fields = {f["field"]: f["available"] for f in r.json()["fields"]}
        check("qayta ochishda ma'lumot yo'qolmadi", fields.get("website") is True and fields.get("lms") is False)

        # --- the v1 machinery is gone ----------------------------------------
        for path in ("/claims/me", "/claim-requests", "/permission-requests", "/reviews"):
            r = c.get(f"{BASE}{path}", headers=auth(op1))
            check(f"eski endpoint {path} yo'q", r.status_code == 404, f"status={r.status_code}")

    print()
    if failures:
        print(f"{len(failures)} ta tekshiruv yiqildi:")
        for f in failures:
            print("  -", f)
        return 1
    print("Barcha smoke tekshiruvlari o'tdi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
