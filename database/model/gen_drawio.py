"""Generate database/model/cinema_model.drawio (logical + physical pages) from the live catalog (meta.json)."""
import json, re, sys
from html import escape

META = json.load(open(sys.argv[1], encoding="utf-8"))
OUT = sys.argv[2]

TABLES = ["users", "movies", "theater_rooms", "seats", "showtimes", "bookings", "booking_seats"]
ENT = {"users": ("USERS", "사용자"), "movies": ("MOVIES", "영화"), "theater_rooms": ("ROOMS", "상영관"), "seats": ("SEATS", "좌석"),
       "showtimes": ("SCREENINGS", "상영 일정"), "bookings": ("BOOKINGS", "예매"), "booking_seats": ("BOOKING_SEATS", "예매 좌석")}
KO = {
    "users": {"user_id": "사용자 번호", "username": "계정 ID", "password_hash": "비밀번호 해시", "role": "역할", "created_at": "가입 일시"},
    "movies": {"movie_id": "영화 번호", "title": "제목", "genre": "장르", "duration_minutes": "상영 시간(분)", "rating": "관람 등급", "synopsis": "줄거리", "release_date": "개봉일", "poster_url": "포스터 경로"},
    "theater_rooms": {"room_id": "상영관 번호", "room_name": "상영관명"},
    "seats": {"seat_id": "좌석 번호", "room_id": "상영관 번호", "seat_row": "좌석 행", "seat_number": "좌석 열 번호"},
    "showtimes": {"showtime_id": "상영 번호", "movie_id": "영화 번호", "room_id": "상영관 번호", "starts_at": "시작 시각", "ends_at": "종료 시각", "ticket_price": "좌석 단가"},
    "bookings": {"booking_id": "예매 번호", "user_id": "사용자 번호", "showtime_id": "상영 번호", "status": "예매 상태", "payment_status": "결제 상태", "booked_at": "예매 시각",
                 "expires_at": "결제 기한", "total_amount": "총 예매 금액", "paid_at": "결제 일시", "cancelled_at": "취소 일시"},
    "booking_seats": {"booking_seat_id": "예매 좌석 번호", "booking_id": "예매 번호", "showtime_id": "상영 번호", "seat_id": "좌석 번호", "price_at_booking": "예매 시점 단가"},
}
REL_LABEL = {("users", "bookings"): "예매한다", ("movies", "showtimes"): "상영된다", ("theater_rooms", "seats"): "포함한다", ("theater_rooms", "showtimes"): "개최한다",
             ("showtimes", "bookings"): "예매 대상", ("bookings", "booking_seats"): "점유한다", ("seats", "booking_seats"): "배정된다"}

cols = {t: [c for c in META["columns"] if c["t"] == t] for t in TABLES}
cons = {t: [c for c in META["constraints"] if c["t"] == t] for t in TABLES}
idxs = {t: [i for i in META["indexes"] if i["t"] == t] for t in TABLES}


def parse_cols(d):
    return [x.strip() for x in d.split("(", 1)[1].split(")", 1)[0].split(",")]


pk, uk, fk = {t: set() for t in TABLES}, {t: set() for t in TABLES}, {t: set() for t in TABLES}
rels = []  # (parent, child, fkcols)
for t in TABLES:
    for c in cons[t]:
        if c["type"] == "p":
            pk[t] |= set(parse_cols(c["def"]))
        elif c["type"] == "u":
            uk[t] |= set(parse_cols(c["def"]))
        elif c["type"] == "f":
            m = re.match(r"FOREIGN KEY \((.*?)\) REFERENCES (\w+)\(", c["def"])
            fk[t] |= {x.strip() for x in m.group(1).split(",")}
            rels.append((m.group(2), t, m.group(1)))
# lower(username) unique index counts as UK on username
for i in idxs["users"]:
    if "UNIQUE" in i["def"] and "lower" in i["def"]:
        uk["users"].add("username")

_id = [1]


def nid():
    _id[0] += 1
    return f"n{_id[0]}"


def cell(parent, value, style, x, y, w, h, vertex=True):
    i = nid()
    return i, f'<mxCell id="{i}" value={q(value)} style="{style}" vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'


def q(v):
    return '"' + escape(v, quote=True) + '"'


TABLE_STYLE = "shape=table;startSize=34;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=0;fontStyle=1;align=center;resizeLast=1;html=1;fontSize=15;fillColor=%s;strokeColor=%s;fontColor=#FFFFFF;"
ROW_STYLE = "shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=0;fillColor=%s;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=1;strokeColor=#D9DCE1;"
CELL_STYLE = "shape=partialRectangle;connectable=0;fillColor=none;top=0;left=0;bottom=0;right=0;overflow=hidden;whiteSpace=wrap;html=1;align=left;spacingLeft=6;fontSize=13;%s"


def table(parts, tname, x, y, widths, rows, header, colour, rowh=28):
    """rows: list of (cells[list of str], style_flags)"""
    w = sum(widths)
    h = 34 + rowh * len(rows)
    tid = nid()
    parts.append(f'<mxCell id="{tid}" value={q(header)} style="{TABLE_STYLE % (colour, colour)}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    for r, (vals, flags) in enumerate(rows):
        rid = nid()
        fill = "#FDECEE" if flags.get("pk") else ("#FFFFFF" if r % 2 == 0 else "#F4F5F8")
        parts.append(f'<mxCell id="{rid}" value="" style="{ROW_STYLE % fill}" vertex="1" parent="{tid}"><mxGeometry y="{34 + r * rowh}" width="{w}" height="{rowh}" as="geometry"/></mxCell>')
        cx = 0
        for k, (val, cw) in enumerate(zip(vals, widths)):
            bold = "fontStyle=1;" if (k == 0 or flags.get("pk") and k == 1) else ""
            colr = "fontColor=#C8102E;" if k == 0 else ("fontColor=#565C68;" if k >= 2 else "")
            parts.append(f'<mxCell id="{nid()}" value={q(val)} style="{CELL_STYLE % (bold + colr)}" vertex="1" parent="{rid}"><mxGeometry x="{cx}" width="{cw}" height="{rowh}" as="geometry"><mxRectangle width="{cw}" height="{rowh}" as="alternateBounds"/></mxGeometry></mxCell>')
            cx += cw
    return tid, w, h


def textbox(parts, html, x, y, w, h):
    parts.append(f'<mxCell id="{nid()}" value={q(html)} style="text;html=1;whiteSpace=wrap;overflow=hidden;align=left;verticalAlign=top;fontSize=11;fontColor=#565C68;fillColor=#F4F5F8;strokeColor=none;spacing=6;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def edge(parts, src, dst, label, exit_=None):
    st = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=ERzeroToMany;startArrow=ERmandOne;startFill=0;endFill=0;strokeWidth=2;strokeColor=#565C68;fontSize=12;fontColor=#14161B;labelBackgroundColor=#FFFFFF;"
    if exit_:
        st += exit_
    parts.append(f'<mxCell id="{nid()}" value={q(label)} style="{st}" edge="1" parent="1" source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry"/></mxCell>')


def short_types(t):
    t = t.replace("character varying", "varchar").replace("timestamp with time zone", "timestamptz").replace("character", "char")
    return t


def summary(t):
    lines = []
    ck = [c["name"] for c in cons[t] if c["type"] == "c"]
    ex = [c["name"] for c in cons[t] if c["type"] == "x"]
    uq = [c["name"] + " " + c["def"].replace("UNIQUE ", "") for c in cons[t] if c["type"] == "u"]
    fks = [c["name"] for c in cons[t] if c["type"] == "f"]
    skip = {c["name"] for c in cons[t] if c["type"] in ("p", "u", "x")}
    ix = []
    for i in idxs[t]:
        if i["name"] in skip:
            continue
        ix.append(i["name"] + (" (부분)" if " WHERE " in i["def"] else "") + (" UNIQUE" if "UNIQUE" in i["def"] else ""))
    if uq: lines.append("<b>UNIQUE</b> " + "; ".join(uq))
    if fks: lines.append("<b>FK</b> " + ", ".join(fks))
    if ck: lines.append("<b>CHECK</b> " + ", ".join(ck))
    if ex: lines.append("<b>EXCLUDE</b> " + ", ".join(ex))
    if ix: lines.append("<b>INDEX</b> " + ", ".join(ix))
    tg = [g["name"] for g in META["triggers"] if g["t"] == t]
    if tg: lines.append("<b>TRIGGER</b> " + ", ".join(tg))
    return "<br>".join(lines)


def build_page(kind):
    parts = []
    pos = {}
    X = [40, 520, 1000, 1480]
    layout = {"users": (0, 0), "bookings": (1, 0), "showtimes": (2, 0), "movies": (3, 0), "booking_seats": (1, 1), "seats": (2, 1), "theater_rooms": (3, 1)}
    ids = {}
    yB = 480
    for t in TABLES:
        cx, ry = layout[t]
        x, y = X[cx], 60 if ry == 0 else yB
        if kind == "physical":
            widths = [48, 150, 130, 52]
            rows = []
            for c in cols[t]:
                flag = "PK" if c["n"] in pk[t] else ("FK" if c["n"] in fk[t] else ("UK" if c["n"] in uk[t] else ""))
                if c["n"] in pk[t] and c["n"] in fk[t]: flag = "PK,FK"
                rows.append(([flag, c["n"], short_types(c["type"]), "NN" if c["notnull"] else ""], {"pk": c["n"] in pk[t]}))
            tid, w, h = table(parts, t, x, y, widths, rows, t, "#14161B")
        else:
            widths = [48, 160, 150]
            rows = []
            for c in cols[t]:
                flag = "PK" if c["n"] in pk[t] else ("FK" if c["n"] in fk[t] else ("UK" if c["n"] in uk[t] else ""))
                if c["n"] in pk[t] and c["n"] in fk[t]: flag = "PK,FK"
                rows.append(([flag, KO[t][c["n"]], c["n"]], {"pk": c["n"] in pk[t]}))
            e, k = ENT[t]
            tid, w, h = table(parts, t, x, y, widths, rows, f"{e}  ({k})", "#C8102E")
        ids[t] = tid
    for parent, child, fkc in rels:
        key = (parent, child)
        if key in {r[:2] for r in rels} and not any(p == "EDGE" for p in []):
            pass
    seen = set()
    for parent, child, fkc in rels:
        if (parent, child) in seen:
            continue
        seen.add((parent, child))
        special = "exitX=0.15;exitY=0;exitDx=0;exitDy=0;entryX=0.85;entryY=1;entryDx=0;entryDy=0;" if (parent, child) == ("theater_rooms", "showtimes") else None
        edge(parts, ids[parent], ids[child], REL_LABEL.get((parent, child), ""), special)
    title = "물리적 데이터 모델 (Physical): PostgreSQL 18, 마이그레이션 0001~0005" if kind == "physical" else "논리적 데이터 모델 (Logical): 엔티티·속성·관계 (3NF)"
    parts.append(f'<mxCell id="{nid()}" value={q(title)} style="text;html=1;fontSize=22;fontStyle=1;fontColor=#14161B;align=left;" vertex="1" parent="1"><mxGeometry x="40" y="8" width="1400" height="36" as="geometry"/></mxCell>')
    legend = ("<b>범례</b><br>PK 기본키 · FK 외래키 · UK 후보키(유일)<br>NN NOT NULL<br>관계선: 1(부모) — 0..N(자식), 크로우풋 표기<br>"
              "<br>통제된 중복: bookings.total_amount, booking_seats.showtime_id, booking_seats.price_at_booking, showtimes.ends_at")
    textbox(parts, legend, 40, yB, 380, 150)
    return "\n".join(parts)


def build_constraints_page():
    parts = []
    parts.append(f'<mxCell id="{nid()}" value={q("물리적 데이터 모델 (Physical): 제약조건 · 인덱스 · 트리거")} style="text;html=1;fontSize=22;fontStyle=1;fontColor=#14161B;align=left;" vertex="1" parent="1"><mxGeometry x="40" y="8" width="1400" height="36" as="geometry"/></mxCell>')
    y = 60
    for t in TABLES:
        sm = summary(t)
        est = sum(1 + len(re.sub("<[^>]+>", "", ln)) // 120 for ln in sm.split("<br>"))
        h = max(40, 20 * est + 16)
        parts.append(f'<mxCell id="{nid()}" value={q(t)} style="rounded=0;whiteSpace=wrap;html=1;fillColor=#14161B;fontColor=#FFFFFF;fontStyle=1;fontSize=15;strokeColor=#FFFFFF;" vertex="1" parent="1"><mxGeometry x="40" y="{y}" width="190" height="{h}" as="geometry"/></mxCell>')
        parts.append(f'<mxCell id="{nid()}" value={q(sm)} style="text;html=1;whiteSpace=wrap;overflow=hidden;align=left;verticalAlign=middle;fontSize=13;fontColor=#14161B;fillColor=#F4F5F8;strokeColor=#FFFFFF;spacing=8;" vertex="1" parent="1"><mxGeometry x="230" y="{y}" width="1150" height="{h}" as="geometry"/></mxCell>')
        y += h + 4
    return "\n".join(parts)


pages = [("논리적 모델 (Logical)", build_page("logical")), ("물리적 모델 (Physical)", build_page("physical")), ("제약조건·인덱스·트리거", build_constraints_page())]
xml = ['<mxfile host="app.diagrams.net" agent="cinema-model-generator" version="24.0.0">']
for n, (name, body) in enumerate(pages):
    xml.append(f'<diagram id="page{n}" name={q(name)}><mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1920" pageHeight="1080" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>')
    xml.append(body)
    xml.append("</root></mxGraphModel></diagram>")
xml.append("</mxfile>")
open(OUT, "w", encoding="utf-8").write("\n".join(xml))
print("wrote", OUT)
