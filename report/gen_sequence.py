# -*- coding: utf-8 -*-
"""Sequence diagrams drawn with Pillow (Graphviz cannot express them).

Each diagram models a flow implemented in the backend/extension; the source
modules are named in the report text beside each figure.
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "diagrams")
FONT = r"C:\Windows\Fonts\arial.ttf"
BOLD = r"C:\Windows\Fonts\arialbd.ttf"
W = 1400
SC = {  # participant colours (fill, line) -> same roles as the other diagrams
    "blue": ("#DCE9F8", "#2F5D9B"), "green": ("#DDEFE0", "#3C7A4B"), "amber": ("#FBEBCB", "#A8741A"),
    "violet": ("#E9E1F2", "#6B4E9B"), "grey": ("#EEEEEE", "#555555"), "red": ("#F8DCDC", "#A33A3A"),
}


def wrap_text(draw, text, font, maxw):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def sequence(name, parts, msgs):
    """parts: [(label, colour)]; msgs: ('a->b'|'a-->b', text) | ('note', idx, text) | ('alt', text)"""
    f = ImageFont.truetype(FONT, 26)
    fb = ImageFont.truetype(BOLD, 26)
    n = len(parts)
    margin = 40
    colw = (W - 2 * margin) / n
    xs = [margin + colw * (i + 0.5) for i in range(n)]
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    # pre-measure
    rows = []
    for m in msgs:
        if m[0] == "sep":
            rows.append((m, 56))
            continue
        if m[0] == "self":
            lines = wrap_text(tmp, m[2], f, colw * 1.1)
            rows.append((m, 40 + 34 * len(lines)))
            continue
        a, b = m[0].replace("-->", "->").split("->")
        span = abs(xs[int(a)] - xs[int(b)])
        lines = wrap_text(tmp, m[1], f, max(span - 30, 200))
        rows.append((m, 52 + 34 * len(lines)))
    head = 110
    height = head + sum(h for _, h in rows) + 130
    img = Image.new("RGB", (W, height), "white")
    d = ImageDraw.Draw(img)
    for i, (label, col) in enumerate(parts):
        fill, line = SC[col]
        lines = wrap_text(d, label, fb, colw - 24)
        bw = colw - 24
        bh = 28 + 34 * len(lines)
        for yb in (20, height - 20 - bh):
            d.rounded_rectangle([xs[i] - bw / 2, yb, xs[i] + bw / 2, yb + bh], 14, fill=fill, outline=line, width=3)
            for k, ln in enumerate(lines):
                tw = d.textlength(ln, font=fb)
                d.text((xs[i] - tw / 2, yb + 14 + 34 * k), ln, font=fb, fill="black")
        d.line([xs[i], 20 + bh, xs[i], height - 20 - bh], fill="#888888", width=2)
    y = head
    step = 0
    for m, h in rows:
        if m[0] == "sep":
            d.line([margin, y + 24, W - margin, y + 24], fill="#A8741A", width=2)
            tw = d.textlength(m[1], font=fb)
            d.rectangle([W / 2 - tw / 2 - 12, y + 6, W / 2 + tw / 2 + 12, y + 44], fill="#FFF7E0", outline="#A8741A")
            d.text((W / 2 - tw / 2, y + 8), m[1], font=fb, fill="#7A5200")
            y += h
            continue
        if m[0] == "self":
            i = int(m[1])
            lines = wrap_text(d, m[2], f, colw * 1.1)
            x0 = xs[i]
            top = y + 14
            d.line([x0, top, x0 + 60, top, x0 + 60, top + 34, x0, top + 34], fill="black", width=3)
            d.polygon([(x0, top + 34), (x0 + 14, top + 26), (x0 + 14, top + 42)], fill="black")
            for k, ln in enumerate(lines):
                d.text((x0 + 74, top - 6 + 34 * k), ln, font=f, fill="black")
            y += h
            continue
        spec, text = m
        dashed = "-->" in spec
        a, b = spec.replace("-->", "->").split("->")
        ia, ib = int(a), int(b)
        step += 1
        lines = wrap_text(d, text, f, max(abs(xs[ia] - xs[ib]) - 30, 200))
        x1, x2 = xs[ia], xs[ib]
        ytext = y + 6
        for k, ln in enumerate(lines):
            tw = d.textlength(ln, font=f)
            d.text(((x1 + x2) / 2 - tw / 2, ytext + 34 * k), f"{ln}", font=f, fill="black")
        ya = y + 12 + 34 * len(lines) + 12
        direction = 1 if x2 > x1 else -1
        if dashed:
            xx = x1
            while (xx - x2) * direction < -18:
                xe = xx + direction * 14
                d.line([xx, ya, xe, ya], fill="black", width=3)
                xx += direction * 24
        else:
            d.line([x1, ya, x2 - direction * 4, ya], fill="black", width=3)
        d.polygon([(x2, ya), (x2 - direction * 20, ya - 9), (x2 - direction * 20, ya + 9)], fill="black")
        # step number bubble
        d.ellipse([x1 - 16 if direction == 1 else x1 - 16, ya - 16, x1 + 16, ya + 16], fill="#2F5D9B")
        sw = d.textlength(str(step), font=ImageFont.truetype(BOLD, 20))
        d.text((x1 - sw / 2, ya - 12), str(step), font=ImageFont.truetype(BOLD, 20), fill="white")
        y += h
    img.save(os.path.join(OUT, name + ".png"), dpi=(200, 200))
    print("ok", name, img.size)


def build():
    P = [("Browser (dashboard)", "blue"), ("FastAPI router /auth", "green"), ("AuthService", "green"), ("MongoDB", "amber")]
    sequence("seq_register", P, [
        ("0->1", "POST /api/v1/auth/register {full_name, email, password, confirm_password}"),
        ("1->2", "register(request)"),
        ("2->3", "get_by_email(email.lower())"),
        ("3-->2", "none (409 EMAIL_ALREADY_EXISTS if found)"),
        ("self", 2, "hash_password (bcrypt)"),
        ("2->3", "insert user {status: active}"),
        ("1-->0", "201 Created {user_id, full_name, email}"),
    ])
    sequence("seq_login", P, [
        ("0->1", "POST /api/v1/auth/login {email, password}"),
        ("1->2", "login(email, password, rate_key)"),
        ("self", 2, "rate limiter: 5 attempts per 60 s (429)"),
        ("2->3", "get_by_email"),
        ("self", 2, "bcrypt verify (dummy hash if unknown email)"),
        ("2-->1", "create_access_token: JWT {sub, jti, iat, exp, typ=access}"),
        ("1-->0", "200 {access_token, user}"),
        ("0->1", "any request: Authorization: Bearer token"),
        ("2->3", "is_revoked(jti)? user active?"),
        ("0->1", "POST /auth/logout"),
        ("2->3", "revoke(jti, expires_at); TTL index purges later"),
    ])

    sequence("seq_upload", [("Browser (dashboard)", "blue"), ("Documents API", "green"), ("Pipeline runner", "green"), ("MongoDB", "amber"), ("ChromaDB", "amber")], [
        ("0->1", "POST /api/v1/documents (multipart file)"),
        ("self", 1, "validate extension, magic bytes, size, checksum"),
        ("1->3", "insert document {status: uploaded}"),
        ("1-->0", "201 {document_id, status}"),
        ("1->2", "dispatch job (inline task or Celery)"),
        ("2->3", "status processing; record stages"),
        ("self", 2, "parse, extract, merge (LLM optional)"),
        ("2->3", "replace structured_facts and discovered_facts"),
        ("2->4", "delete old chunks; upsert chunk vectors (user_id metadata)"),
        ("2->3", "status processed; index_status; fact_count"),
        ("0->1", "GET /documents/{id}/status (polling)"),
        ("1-->0", "{current_stage, progress, status}"),
    ])

    sequence("seq_fill", [("Popup + content script", "blue"), ("FastAPI /forms", "green"), ("LangGraph pipeline", "green"), ("MongoDB", "amber"), ("ChromaDB + LLM", "violet")], [
        ("self", 0, "SFA_EXTRACT: detect fields, skip sensitive (no values read)"),
        ("0->1", "POST /forms/sessions {website_origin, page_url, form_id}"),
        ("0->1", "POST /forms/sessions/{id}/analyze {fields[]} (202)"),
        ("1->2", "run(user_id, session_id, fields)"),
        ("2->3", "resolve_view: active structured_facts"),
        ("2->4", "classify (ambiguous only) and RAG for empty fields"),
        ("2->3", "upsert recommendations"),
        ("0->1", "GET .../recommendations (poll)"),
        ("1-->0", "recommendations with reason, source, status"),
        ("self", 0, "user ticks, edits or skips each field"),
        ("0->1", "POST .../decisions; GET .../approved-values"),
        ("self", 0, "SFA_FILL: write values, verify DOM"),
        ("0->1", "POST .../verify {applied, verified, reason}"),
        ("1->3", "update counters; session stays not_submitted"),
    ])

    sequence("seq_rag", [("Browser (Ask page)", "blue"), ("Retrieval API", "green"), ("RAGAnswerService", "green"), ("ChromaDB", "amber"), ("LLM provider", "violet")], [
        ("0->1", "POST /retrieval/rag/answer {query, top_k}"),
        ("1->2", "answer(user_id, question, top_k)"),
        ("self", 2, "embed query (MiniLM 384-dim)"),
        ("2->3", "query where user_id = current user, cosine"),
        ("3-->2", "chunks with similarity"),
        ("self", 2, "drop below 0.35; drop injection-like chunks"),
        ("2->4", "prompt: UNTRUSTED_EVIDENCE + UNTRUSTED_QUESTION"),
        ("4-->2", "JSON {answer, used_chunk_ids, confidence}"),
        ("self", 2, "keep only cited chunks; cap confidence by similarity"),
        ("1-->0", "answered with sources, or insufficient_evidence"),
    ])

    sequence("seq_conflict", [("Browser (Conflicts page)", "blue"), ("Facts API", "green"), ("FactService", "green"), ("MongoDB", "amber")], [
        ("0->1", "GET /profile/facts/conflicts"),
        ("1->2", "list_conflicts(user_id)"),
        ("2->3", "list_active structured_facts"),
        ("self", 2, "group by comparison_key; conflict if 2+ values on single-valued concept"),
        ("1-->0", "conflicts: CROSS_DOCUMENT / INTRA_DOCUMENT / VERIFIED_VS_NEW"),
        ("0->1", "PATCH .../conflicts/{concept}/resolve {candidate | custom | reject}"),
        ("2->3", "chosen facts confirmed; others superseded (or custom user fact)"),
        ("2->3", "record correction (audit)"),
        ("1-->0", "resolved concept view"),
    ])


if __name__ == "__main__":
    build()
