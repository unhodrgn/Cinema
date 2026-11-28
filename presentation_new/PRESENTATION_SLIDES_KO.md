# 발표 슬라이드 완성본 & 발표 대본 — Cinema Reservation System

**프로젝트명:** 영화관 예매 및 좌석 관리 시스템 (**Cinema Reservation System**)  
**기준 버전:** `2026-11-27` · commit `02ef682` (**Schema 0006** 반영 완료)  
**목표 시간:** **15분 발표** + 5~10분 질의응답(Q&A)  
**발표 구성:** 총 **16장** (표지 1 + 본문 10 + 실시간 시연 2 + AI 시대 팀 프로젝트 1 + 결론 1 + 감사 1)  
**팀원 및 역할 분담:**
- **B — 응용 프로그램 리드 (`응웬치롱`, AI소프트웨어학과):** 슬라이드 `01~05`, `09~12` (웹 UI 시연), `14`(후반), `15~16` — 약 **8분 30초**
- **A — 데이터베이스 리드 (`응오후인느`, 소프트웨어학과):** 슬라이드 `06~08`, `13` (SQL 시연), `14`(전반) — 약 **6분 30초**
*(※ 교수님 안내 기준에 따라 1인 대표 발표가 필요하면 1인이 전체 대본을 진행하고, 다른 1인이 시연 조작 및 Q&A를 분담할 수 있습니다.)*

---

## 슬라이드 제작 디자인 가이드 (PPT / Canva / Gamma 제작용)

| 항목 | 권장 사양 |
|---|---|
| **화면 비율** | `16:9` (1920 × 1080) |
| **추천 폰트 (한글)** | **Pretendard** 또는 **Noto Sans KR** (발표 PC 호환성 최우선 시 Windows 기본 **맑은 고딕 / Malgun Gothic** 사용) · 코드/SQL: **JetBrains Mono** 또는 **Consolas** |
| **컬러 팔레트** | • 배경: 라이트 톤 `#F8FAFC` (표지·감사 슬라이드만 다크 네이비 `#0F172A`)<br>• 메인 강조: 딥 네이비 `#1E293B` (신뢰감·아키텍처)<br>• 포인트(시네마/핵심): 크림슨 레드 `#DC2626` 또는 앰버 `#D97706`<br>• 성공/통과 배지: 에메랄드 `#059669` · 경고/차단 배지: 레드 `#B91C1C` |
| **시각 자료 경로 (저장소 내 즉시 활용 가능)** | • 논리 ERD: `database/model/cinema_model_logical.png`<br>• 물리 ERD: `database/model/cinema_model_physical.png`<br>• 제약·인덱스·트리거 요약: `database/model/cinema_model_constraints.png`<br>• 영화 포스터(배경/예시용): `frontend/public/images/posters/*.jpg` |
| **텍스트 원칙** | 슬라이드 본문은 **키워드·표·도식 중심**으로 간결하게 배치하고, 상세 설명은 아래 **발표 대본(`발표 대본`)**으로 구술 |

---

## 전체 타임테이블 (총 15:00)

| Slide | 제목 | 시간 | 누적 구간 | 발표자 |
|---|---|---:|---|---|
| **01** | 표지 — 프로젝트 및 팀 소개 | 0:30 | 00:00 – 00:30 | 응웬치롱 (B) |
| **02** | 프로젝트 배경 및 시스템 규모 | 0:35 | 00:30 – 01:05 | 응웬치롱 (B) |
| **03** | 초기 환경 설정 및 기술 스택 | 0:35 | 01:05 – 01:40 | 응웬치롱 (B) |
| **04** | 논리적·물리적 분리 아키텍처 | 0:50 | 01:40 – 02:30 | 응웬치롱 (B) |
| **05** | 업무 분석 및 6대 핵심 의사결정 (`BR-DL-001`) | 0:55 | 02:30 – 03:25 | 응웬치롱 (B) |
| **06** | 데이터 모델링 및 정규화 (1NF → 3NF) | 0:50 | 03:25 – 04:15 | 응오후인느 (A) |
| **07** | 물리 설계 및 PostgreSQL 무결성 엔진 | 1:00 | 04:15 – 05:15 | 응오후인느 (A) |
| **08** | 교차 검증 및 스키마 고도화 (`0001` → `0006`) | 0:50 | 05:15 – 06:05 | 응오후인느 (A) |
| **09** | 백엔드 REST API 및 다층 보안 설계 | 0:40 | 06:05 – 06:45 | 응웬치롱 (B) |
| **10** | 프런트엔드 SPA 및 사용자 경험 | 0:30 | 06:45 – 07:15 | 응웬치롱 (B) |
| **11** | 5계층 자동 검증 전략 및 결과 (`0006`) | 0:50 | 07:15 – 08:05 | 응웬치롱 (B) |
| **12** | **실시간 시연 ①** — 웹 애플리케이션 (고객 · 관리자) | 2:00 | 08:05 – 10:05 | 응웬치롱 (B) |
| **13** | **실시간 시연 ②** — SQL 상태 제어 · 예외 · 권한 검증 | 3:10 | 10:05 – 13:15 | 응오후인느 (A) |
| **14** | **[필수]** AI 시대에 팀 프로젝트가 왜 의미가 있는가? | 1:15 | 13:15 – 14:30 | A + B 공동 |
| **15** | 결론 및 향후 확장 계획 | 0:30 | 14:30 – 15:00 | 응웬치롱 (B) |
| **16** | 감사합니다 | — | — | 응웬치롱 (B) |

---

# SLIDE 01 — 표지 (Title Slide)

- **배정 시간:** `0:30` (`00:00 – 00:30`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 다크 네이비(`#0F172A`) 풀 배경. 좌측에 제목·부제·핵심 한 줄 메시지, 하단에 2인 팀원 카드, 우측 배경에 영화 포스터(`frontend/public/images/posters/`) 또는 미니멀 좌석 격자 그래픽을 은은하게(투명도 15%) 배치.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**메인 제목:**
> **영화관 예매 및 좌석 관리 시스템**  
> Cinema Reservation System

**부제:**
> 데이터 무결성과 논리적·물리적 아키텍처 분리를 중심으로  
> **기획 → 설계 → 구현 → 검증**까지 완성한 데이터베이스 팀 프로젝트

**핵심 한 줄 요약 (배너):**
> *"단순한 예매 웹이 아니라, **중복 예매·시간 겹침·이력 유실이 구조적으로 불가능한** DB 중심 시스템"*

**팀원 및 역할:**
| 역할 | 이름 (소속) | 담당 영역 |
|---|---|---|
| **Database Lead (A)** | **응오후인느** (소프트웨어학과) | ERD·정규화, PostgreSQL 스키마·트리거·마이그레이션(`0001~0006`), SQL 시연 |
| **Application Lead (B)** | **응웬치롱** (AI소프트웨어학과) | 업무 분석, Flask REST API, React/TS SPA, Docker Compose, 통합 검증·웹 시연 |

**수행 기간:** `2026. 11. 17 – 2026. 11. 29`

### 발표 대본 (한국어)
> 안녕하십니까. **영화관 예매 및 좌석 관리 시스템** 프로젝트 발표를 맡은 AI소프트웨어학과 응웬치롱, 그리고 데이터베이스 설계를 맡은 소프트웨어학과 응오후인느입니다.
>
> 오늘 15분 발표에서는 단순한 기능 나열이 아니라, **왜 예매 업무에 강력한 DB 설계가 필요한지**부터 시작해 **초기 환경과 분리 아키텍처, 업무 규칙 합의, 6단계 스키마 고도화, 5계층 검증**, 그리고 **웹과 SQL 실시간 시연**까지 프로젝트의 전체 이야기를 순서대로 보여드리겠습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Chào hỏi tự tin, giới thiệu nhanh tên 2 bạn và chốt ngay mạch storytelling của bài (không liệt kê tính năng mà kể hành trình từ bài toán → thiết kế → nâng cấp → kiểm chứng → demo).

---

# SLIDE 02 — 프로젝트 배경 및 시스템 규모

- **배정 시간:** `0:35` (`00:30 – 01:05`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 좌우 2단 분할. 좌측은 4개 문제 카드(아이콘 + 붉은 강조), 우측은 시스템 규모 KPI 그리드(큰 숫자 6개 박스).

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `01. 프로젝트 배경 및 시스템 규모`  
**서브 헤드라인:** 영화관 예매는 단순 CRUD가 아닌 **동시성·시간 제약·이력 보존**이 얽힌 대표적 데이터 무결성 문제

**[좌측] 해결해야 할 4가지 핵심 데이터 문제**
1. **좌석 중복 예매 (Double Booking)**  
   두 고객이 같은 상영의 동일 좌석을 동시에 예매 요청
2. **미결제 좌석 무한 점유 (Hold Timeout)**  
   결제하지 않고 이탈한 예매가 좌석을 계속 막는 문제
3. **상영 일정 시간 겹침 (Schedule Overlap)**  
   동일 상영관에 상영 시간이 겹치는 일정 등록
4. **이력 유실 및 가격 왜곡 (History & Price Drift)**  
   취소 후 기록 삭제나 사후 단가 변경으로 인한 정산 불일치

**[우측] 승인된 시스템 규모 및 데모 데이터**
| 항목 | 규모 | 비고 |
|---|---|---|
| **영화관 / 상영관** | **1개관 / 5개 상영관** | `Hall 1` ~ `Hall 5` |
| **좌석 수** | **총 250석** | 관당 50석 (`A~E`행 × `1~10`번) |
| **샘플 영화** | **6편** | 포스터 및 6대 속성 포함 |
| **상영 일정** | **280회 (14일)** | 하루 20회 (`Asia/Seoul` 기준) |
| **계정 역할** | **2종** | `CUSTOMER`, `ADMIN` (`GUEST` 없음) |
| **데모 계정** | **3개** | `admin` 1명, `customer1·2` 2명 |

### 발표 대본 (한국어)
> 영화관 예매는 겉으로는 단순해 보이지만, 데이터베이스 관점에서는 네 가지 까다로운 무결성 문제를 동시에 풀어야 합니다.
>
> 첫째, 여러 사용자가 같은 좌석을 동시에 눌렀을 때 중복 예매를 막아야 하고, 둘째, 미결제 예매는 정확히 10분 뒤 자동으로 좌석을 해제해야 합니다. 셋째, 같은 상영관에서 상영 시간이 겹치지 않아야 하며, 넷째, 취소나 만료 후에도 좌석은 다시 열리되 예매 이력과 금액은 그대로 보존되어야 합니다.
>
> 본 시스템은 1개 영화관, 5개 상영관, 총 250석 규모로 설계했으며, 데모 데이터로 영화 6편과 14일간 280회 상영 일정을 구성했습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Nhấn mạnh 4 bài toán dữ liệu ngay từ đầu để mở đường cho các slide thiết kế DB phía sau. Lướt nhanh bảng quy mô trong 10 giây.

---

# SLIDE 03 — 초기 환경 설정 및 기술 스택

- **배정 시간:** `0:35` (`01:05 – 01:40`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 상단 6행 기술 스택 요약표 + 하단 3단계 가로 스텝 박스(`Step 1 → Step 2 → Step 3`)로 초기 환경 설정 흐름 시각화.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `02. 초기 환경 설정 및 기술 스택`  
**서브 헤드라인:** Docker Compose 기반 재현 가능한 실행 환경과 SQL 직접 제어 중심 스택

| 구분 | 기술 및 버전 | 선택 이유 및 역할 |
|---|---|---|
| **DBMS** | **PostgreSQL 18** (`btree_gist` 확장) | `tstzrange` 배제 제약, 행 잠금, 트리거·함수 기반 무결성 엔진 |
| **Backend** | **Python 3.12 · Flask 3.1.3 · `psycopg2 2.9.13`** | ORM 숨김 없이 트랜잭션 경계·`SQLSTATE` 직접 제어, 순수 JSON API |
| **Frontend** | **React 19.3 · TypeScript 5.9 · Vite 7.3** | 12개 화면 SPA, 정적 타입 검증 (+ 레거시 HTML/JS 폴백 UI 병행) |
| **컨테이너** | **Docker Compose v2** (`api`·`frontend`; DB는 Neon 클라우드, `db`·`test` 프로필은 로컬 대체/검증용) | 노트북 2컨테이너 · DB는 클라우드 · non-root 실행(`uid 10001`), `tmpfs` 검증 DB |
| **검증·모델링** | **pytest 9.2 · Node test · Playwright 1.65 · draw.io** | 5계층 자동 테스트 및 DB 카탈로그 기반 ER 모델 산출 |
| **협업 도구** | **Git / GitHub** (브랜치 · PR) + 계약 문서 | 역할 분담(`chia_viec.md`), PR 단위 교차 리뷰 |

**초기 환경 설정 3단계 (`README.md`)**
1. **환경 변수 생성:** `backend/.env.example` → `.env` 복사 후 `SECRET_KEY`, `DB_PASSWORD` 난수 생성 (Git 미포함)
2. **스택 기동 및 자동 마이그레이션:** `docker compose up --build -d --wait` → 빈 볼륨에서 `0001` → `compose-role` → `0002`~`0006` 순차 적용
3. **데모 시드 1회 적재:** `demo.sql` 실행 (7개 테이블 `EXCLUSIVE` 잠금으로 기존 데이터 덮어쓰기 원천 차단)

### 발표 대본 (한국어)
> 기술 스택과 초기 환경 설정입니다. DBMS는 시간 구간 배제 제약과 강력한 동시성 제어를 지원하는 **PostgreSQL 18**과 `btree_gist` 확장을 선택했습니다.
>
> 백엔드는 Python 3.12, Flask, 그리고 **`psycopg2`**를 사용해 ORM의 암묵적 동작 없이 트랜잭션과 PostgreSQL 오류 코드를 직접 다루도록 구성했고, 프런트엔드는 React 19와 TypeScript로 12개 화면을 구현했습니다.
>
> 모든 서비스는 **Docker Compose**로 묶어 `.env`에 키를 넣고 `docker compose up` 한 줄만 실행하면 `0001`부터 `0006` 마이그레이션과 런타임 권한 설정이 자동 완료되며, 협업은 Git/GitHub 브랜치와 Pull Request 기반으로 진행했습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Trả lời trực tiếp tiêu chí đầu tiên trong `important.md` (cấu hình ban đầu, DBMS, ngôn ngữ, framework, container, công cụ nhóm). Nhấn lý do chọn `psycopg2` thuần thay vì ORM.

---

# SLIDE 04 — 논리적·물리적 분리 아키텍처

- **배정 시간:** `0:50` (`01:40 – 02:30`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 상단에 Browser·Frontend·API(노트북)와 PostgreSQL(Neon 클라우드) 블록 다이어그램(화살표에 프로토콜·포트·권한 표기), 하단에 **물리적 분리 vs 논리적 분리** 2열 비교 카드 + 하단 검증 배지.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `03. 논리적·물리적 분리 아키텍처`  
**서브 헤드라인:** 클라이언트·API·DB를 **별도 프로세스·별도 컨테이너·별도 책임**으로 완전 격리

**[상단 아키텍처 다이어그램]**
```text
[ Browser ] ── 정적 파일 ──► [ Frontend Container :8080 ]   (frontend/server.py · React dist/)
     │                           • DB 드라이버·Flask 없음 · /config.js로 API 주소 동적 주입
     └── JSON / HTTP + CORS ──► [ Backend API Container :5000 ] (Flask · static/template=None)
         (Authorization: Bearer) • 인증·인가·검증·SQLSTATE 번역 · 쿠키 미사용
                                      │
                                      └── PostgreSQL 프로토콜 (인터넷 · SSL · cinema_api 권한)
                                      ▼
                                [ PostgreSQL 18 (Neon 클라우드, Singapore) ]
                                 • 노트북이 아닌 별도 서버 · SSL 필수 · 접속 문자열로 다른 기기에서도 접속 가능
```

**[하단 좌측] 물리적 분리 (Physical Separation)**
- **노트북(API·웹) / 클라우드(DB) 분리** + 개별 환경 설정
- **PostgreSQL은 Neon 클라우드 서버:** 다른 기기에서도 접속 문자열(SSL)로 DB에 직접 접속 가능 (cinema_api는 최소 권한)
- **런타임 주소 주입:** Frontend가 `/config.js`(`API_BASE_URL`)를 동적 생성 → 재빌드 없이 API 서버 분리 배포

**[하단 우측] 논리적 분리 (Logical Separation)**
- **Frontend (`frontend/`):** UI 렌더링·임시 좌석 선택·토큰 보관(`sessionStorage`)만 담당. **SQL·업무 판정 0줄**
- **Backend (`backend/app/`):** `api/v1` → `schemas` → `services` → `models` → `core` 계층화. HTML 렌더링 완전 비활성화
- **Database (`migrations/`):** 모든 불변 규칙·가격 계산·기한 판정(`clock_timestamp()`)을 DB가 단독 결정

**[하단 배지]** 자동 검증 완료: `test_process_separation.py` · `test_architecture_live.py` (실제 다중 프로세스 HTTP+CORS 검증)

### 발표 대본 (한국어)
> 이번 프로젝트의 핵심 요구사항 중 하나인 **논리적·물리적 분리 아키텍처**입니다.
>
> 그림처럼 프런트엔드와 백엔드 API는 노트북의 독립된 컨테이너로 실행되고, PostgreSQL은 노트북이 아니라 클라우드 서비스 Neon의 별도 서버에서 실행됩니다. API는 인터넷을 통해 SSL로 접속하며 제한된 `cinema_api` 역할만 사용합니다. 프런트엔드는 Python 표준 라이브러리 정적 서버만 돌리며 DB 라이브러리도, 백엔드 코드도 전혀 포함하지 않고 `/config.js`로 API 주소만 전달받습니다.
>
> 논리적으로도 Flask는 `static_folder=None`, `template_folder=None`으로 HTML 렌더링을 원천 차단해 순수 JSON만 반환하며, 프런트엔드는 업무 규칙을 결정하지 않고 모든 시간과 기한 판정은 PostgreSQL 시계에만 의존합니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Chỉ tay theo 3 khối trên sơ đồ từ trái sang phải (Frontend → API → DB). Nhấn mạnh chi tiết `static_folder=None` và PostgreSQL không mở port ra ngoài — giáo sư rất thích điểm này!

---

# SLIDE 05 — 업무 분석 및 6대 핵심 의사결정 (`BR-DL-001`)

- **배정 시간:** `0:55` (`02:30 – 03:25`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 상단 요약 배지(`14개 기능` · `15개 규칙 BR` · `3개 흐름도` · `7개 문서 DOC`), 중앙에 **D1~D6 의사결정 표**, 우측 하단에 **예매 상태 × 결제 상태 독립 모델** 미니 도식.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `04. 업무 분석 및 6대 핵심 의사결정 (BR-DL-001)`  
**서브 헤드라인:** 구현 전 모호한 업무 경계를 **문서화된 합의(D1~D6)**로 고정하여 DB·앱 충돌 예방

**업무 분석 체계:** `공통 2 (CM-01~02)` · `고객 9 (C-01~09)` · `관리자 3 (A-01~03)` = **총 14개 단위 업무** / **BR-01~15** / **흐름도 3종**

| 결정 | 핵심 합의 내용 | DB 및 시스템 설계 반영 |
|---|---|---|
| **D1** | **취소 시 좌석 해제 + 이력 보존** | `BOOKING_SEATS` 전체 삭제(좌석 즉시 해제), `BOOKINGS`·총액·결제상태(`PAID` 유지, 환불 범위 외) 보존 |
| **D2** | **이력 있는 상영 일정 변경·삭제 차단** | 상태 무관(`BOOKED`/`CANCELLED`/`EXPIRED`) 예매 1건이라도 있으면 5개 속성 수정 거부(`UC001`); 미시작·무예매만 삭제 허용 |
| **D3** | **미결제 10분 만료 (`EXPIRED`)** | `expires_at = booked_at + 10분`. 별도 크론 없이 **요청 시점 만료(`expire_overdue_bookings`)**로 원자적·멱등 처리 |
| **D4** | **비회원 조회 및 좌석 임시 선택 허용** | `C-02~C-05` 로그인 불필요(선택만으로 미점유); 예매 확정(`C-06`)부터 `CUSTOMER` 로그인 필수. `GUEST` 역할 미생성 |
| **D5** | **가입 최소 입력 & 영화 6대 속성** | 가입은 `계정 ID + 비밀번호`만(`CUSTOMER` 자동 지정, 0005~0006 통합 정책). 영화 6속성 + `poster_url` |
| **D6** | **상영 일정별 가격 & 스냅샷 저장** | 고정가 대신 상영별 `ticket_price`, 좌석 행에 단가 스냅샷(`price_at_booking`), 예매 행에 총액 저장 |

**독립 상태 모델:** `status ∈ {BOOKED, CANCELLED, EXPIRED}` × `payment_status ∈ {UNPAID, PAID}` *(단, `EXPIRED + PAID` 금지)*

### 발표 대본 (한국어)
> 설계에 들어가기 전, 전체 업무를 공통 2개, 고객 9개, 관리자 3개의 **총 14개 단위 업무**와 15개 업무 규칙으로 정리했습니다.
>
> 특히 DB 담당자와 앱 담당자 사이에 해석 차이가 생기기 쉬운 여섯 가지 경계 조건을 **`BR-DL-001` 의사결정 기록**으로 먼저 합의했습니다.
>
> 핵심은 두 가지입니다. 첫째, **D1과 D3**에 따라 예매 상태와 결제 상태를 독립 속성으로 분리해, 취소나 10분 만료가 발생하면 `booking_seats` 행만 삭제해 좌석을 즉시 풀고 `bookings` 본 정보와 금액은 이력으로 남깁니다. 또한 크론 잡 대신 **요청 시점 만료 처리**를 택해 조회·예매·결제 직전에 항상 최신 상태를 보장합니다. 둘째, **D2와 D6**로 예매 이력이 한 건이라도 생긴 상영 일정은 단가까지 포함해 수정할 수 없도록 이력 맥락을 고정했습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Đừng đọc từng chữ cả bảng D1–D6; tập trung giải thích nhóm **D1 + D3** (trạng thái độc lập + request-time expiry 10 phút) và **D2 + D6** (khóa lịch sử & giá snapshot), phần còn lại để người xem tự quét bảng. Kết thúc Slide 5 là chuyển mic cho Thành viên A!

---

# SLIDE 06 — 데이터 모델링 및 정규화 (1NF → 3NF)

- **배정 시간:** `0:50` (`03:25 – 04:15`) · **발표자:** 응오후인느 (A)
- **레이아웃 & 시각 자료:** 좌측(55%)에 **`database/model/cinema_model_logical.png`** 이미지 크게 배치, 우측(45%)에 정규화 단계 요약 + **통제된 중복(Controlled Redundancy)** 4행 핵심 표.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `05. 데이터 모델링 및 정규화 (1NF → 3NF)`  
**서브 헤드라인:** 7개 엔티티 3NF 정규화 + 동시성·이력 보존을 위한 **통제된 중복** 설계

**[좌측 시각 자료]**  
*(삽입: `database/model/cinema_model_logical.png` — 7개 엔티티: `users`, `movies`, `theater_rooms`, `seats`, `showtimes`, `bookings`, `booking_seats`)*

**[우측 상단] 정규화 핵심 설계 (`normalization.md`)**
- **1NF:** `seats='A1,A2'` 반복 그룹 제거 → `booking_seats` 원자 행 분리
- **2NF · 3NF:** 모든 비키 속성의 완전·직접 함수 종속 확보 (`seats`에 **전역 좌석 상태 컬럼 미보관** → 상영별 동적 판정)
- `booking_seats`의 `booking_id → showtime_id`는 후보키 `(showtime_id, seat_id)` 구성 속성이므로 **3NF 유지**

**[우측 하단] 의도적 저장 — 통제된 중복 (Controlled Redundancy)**
| 저장 컬럼 | 이유 | 일관성 보장 수단 |
|---|---|---|
| `bookings.total_amount` | 취소·만료로 좌석 행 삭제 후에도 총액 이력 유지 (`D1, D3`) | `COMMIT` 지연 제약 트리거 + 수정 불가 |
| `booking_seats.showtime_id` | MVCC 환경에서 `(상영, 좌석)` **즉시 UNIQUE** 강제 (`0003`) | 복합 FK `(booking_id, showtime_id)` |
| `booking_seats.price_at_booking` | 예매 시점 단가 스냅샷 보존 (`D6`) | 트리거로 상영 가격 일치 강제 |
| `showtimes.ends_at` | 영화 시간 수정 시 기존 상영 일정 불변 (`D2`) | 생략 시에만 자동 계산 후 고정 저장 |

### 발표 대본 (한국어)
> 이어서 데이터베이스 설계를 설명하겠습니다. 개념 모델에서 도출한 **7개 엔티티**를 논리 모델로 구체화하고 1NF부터 3NF까지 정규화를 검토했습니다.
>
> 먼저 물리 좌석 테이블인 `seats`에는 일부러 `AVAILABLE` 같은 상태 컬럼을 두지 않았습니다. 같은 좌석이라도 상영 일정마다 가용 여부가 다르기 때문에, 활성 `booking_seats` 존재 여부로 동적 판정합니다.
>
> 또한 `booking_seats`로 반복 그룹을 제거해 3NF를 확보하되, 업무 요구와 동시성 보장을 위해 네 가지 **통제된 중복**을 의도적으로 두었습니다. 대표적으로 취소 후에도 금액을 남기기 위한 `total_amount`, 그리고 서로 다른 트랜잭션 스냅샷에서도 중복 좌석을 즉시 차단하기 위해 `booking_seats`에 둔 `showtime_id`입니다. 모든 중복은 복합 외래키와 트리거가 자동으로 일관성을 강제합니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Chỉ vào ảnh `cinema_model_logical.png` khi nói đến `seats` (không có cột status) và `booking_seats` (FK kép). Khái niệm *Controlled Redundancy* (통제된 중복) là điểm cộng học thuật rất lớn trong môn CSDL!

---

# SLIDE 07 — 물리 설계 및 PostgreSQL 무결성 엔진

- **배정 시간:** `1:00` (`04:15 – 05:15`) · **발표자:** 응오후인느 (A)
- **레이아웃 & 시각 자료:** 좌측(45%)에 **`database/model/cinema_model_physical.png`** 또는 **`cinema_model_constraints.png`**, 우측(55%)에 **4대 무결성 엔진 기둥 카드** + 하단 숫자 배지(`9 Triggers · 5 Functions · 7 Indexes`).

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `06. 물리 설계 및 PostgreSQL 무결성 엔진`  
**서브 헤드라인:** *"앱 코드가 실수하거나 우회되어도, DB가 마지막 방어선으로 모든 규칙을 강제"*

**[좌측 시각 자료]**  
*(삽입: `database/model/cinema_model_physical.png` 또는 `database/model/cinema_model_constraints.png`)*

**[우측] PostgreSQL 18 기반 4대 핵심 방어 장치**
1. **선언적 시간 겹침 차단 (`BR-04`)**  
   `EXCLUDE USING gist (room_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)`  
   → 동시 입력에도 경합 없이 `23P01` 거부 · **연속 상영(12:00 종료 / 12:00 시작) 허용**
2. **이중 잠금 + 즉시 UNIQUE 중복 예매 방지 (`BR-08`)**  
   `showtimes FOR UPDATE` 행 잠금 + `bookings FOR SHARE` + 복합 FK + **`UNIQUE(showtime_id, seat_id)`**  
   → 동시 요청 시 단 1건만 성공, 나머지는 `UC002` 반환
3. **9개 트리거 + 4개 원자적 트랜잭션 함수**  
   - `create_booking` · `pay_booking` · `cancel_booking` · `expire_overdue_bookings` (**`FOR UPDATE SKIP LOCKED`**로 경합 없이 만료)
   - **상태 머신 트리거(`trg_bookings_validate`):** 불법 전이(`UC007`), 상영 후 예매·취소(`UC004`/`UC005`), 기한 초과 결제(`UC006`) 차단
   - **지연 제약 트리거(`DEFERRABLE INITIALLY DEFERRED`):** `COMMIT` 시 `BOOKED`의 좌석 ≥ 1 및 `총액 = Σ 단가` 검증
4. **인덱스 최적화 & 최소 권한 역할 (`cinema_api`)**  
   - 부분 인덱스 `idx_bookings_pending_expiry (expires_at) WHERE status='BOOKED' AND payment_status='UNPAID'` 등 **7개 인덱스**
   - `cinema_api`는 `bookings DELETE/TRUNCATE`, `users/seats UPDATE` 권한 없음 → **`42501` 차단**

### 발표 대본 (한국어)
> 저희 프로젝트만의 핵심 기술인 **PostgreSQL 무결성 엔진**입니다. 앱 레벨의 단순 조회 후 저장 방식은 동시 요청에 취약하기 때문에, 핵심 불변 규칙을 모두 데이터베이스 내부에 구현했습니다.
>
> 첫째, 같은 상영관의 시간 겹침은 `btree_gist` 기반의 **`EXCLUDE` 배제 제약**으로 선언적으로 막았습니다. 반열린 구간 `[starts_at, ends_at)`을 사용해 직전 상영이 끝나는 시각에 바로 다음 상영을 배치할 수 있습니다.
>
> 둘째, 중복 좌석 예매는 상영 행 `FOR UPDATE` 잠금과 복합 외래키, 그리고 `UNIQUE(showtime_id, seat_id)` 인덱스로 이중 차단했습니다.
>
> 셋째, 예매·결제·취소·만료는 모두 **4개의 원자적 DB 함수**로 묶었고, `expire_overdue_bookings`는 `FOR UPDATE SKIP LOCKED`를 적용해 동시에 결제 중인 행을 방해하지 않으면서 만료 대상만 정리합니다. 마지막으로 지연 제약 트리거가 `COMMIT` 직전에 좌석 수와 총액 일치를 최종 보증합니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Đây là slide đinh về mặt kỹ thuật DB (1 phút đầy đặn). Nói chậm, rõ ở 4 từ khóa vàng: `EXCLUDE USING gist`, `UNIQUE(showtime_id, seat_id)`, `FOR UPDATE SKIP LOCKED`, và `DEFERRABLE INITIALLY DEFERRED`.

---

# SLIDE 08 — 교차 검증 및 스키마 고도화 (`0001` → `0006`)

- **배정 시간:** `0:50` (`05:15 – 06:05`) · **발표자:** 응오후인느 (A)
- **레이아웃 & 시각 자료:** 가로 타임라인 / 진화 로드맵 (상단: `11/20 인수인계 대조: 13 Mismatch → 0` 강조 박스 + 하단: `0001` → `0002` → `0003` → `0004` → `0005` → `0006` 6단계 카드).

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `07. 교차 검증 및 스키마 고도화 (0001 → 0006)`  
**서브 헤드라인:** *"한 번에 완벽했던 설계가 아니라, 교차 대조와 적대적 검증으로 찾아낸 결함을 6번에 걸쳐 보강"*

**[상단 하이라이트] 11/20 1차 인수인계 교차 대조 (`handover_reconciliation_report.md`)**
- 1차 DDL은 자체 테스트 7/7 통과했지만, 앱 리드(B)의 독립 프로브 대조에서 **13건 불일치** 발견  
  *(예: `EXPIRED`·`expires_at` 누락, `D2` 트리거에 `ticket_price` 잠금 누락, 미승인 15분 청소 버퍼 `X1`)*
- `DB-01~11` 일괄 수정으로 **31/31 MATCH (0 Mismatch)** 달성 + 알파벳 순 트리거 실행 오류(`IMMEDIATE`) 수정(`trg_bookings_z_consistency`)

**[하단] 실전 검증으로 이어진 6단계 마이그레이션 진화**
| 버전 | 발견한 실전 결함 / 요구 | 해결 구현 |
|---|---|---|
| **`0001`** | 11/20 13건 대조 결과 반영 | 정규화 기준 스키마·트리거·4개 함수 통합 (`baseline`) |
| **`0002`** | 미시작·무예매 영화/상영 조건부 삭제 지원 | `cinema_api`에 `movies`, `showtimes` `DELETE` 권한 부여 |
| **`0003`** | MVCC 스냅샷 간극 + 50석 최대 금액 오버플로우 위험 | `booking_seats.showtime_id` 즉시 UNIQUE, 첫 예매 버전 트리거, `total_amount` → **`numeric(12,2)`** (최대 약 50억) |
| **`0004`** | PostgreSQL `numeric` 특성상 **`'NaN' >= 0`이 `TRUE` 통과** | 3개 금액 컬럼에 `NOT IN ('NaN', 'Infinity', '-Infinity')` CHECK 추가 |
| **`0005`** | 적대적 점검 시 `Customer1`·전각 `ａｄｍｉｎ` 중복 가입 가능 | API NFKC 정규화 + DB **`lower(username)` 고유 인덱스** (기존 충돌 시 자동 수정 없이 안전 중단) |
| **`0006`** | 공백·제어문자·보이지 않는 문자(`c u s t o m e r`, `\u200b`) 우회 및 `varchar(60)` 끝 공백 절삭 문제 | **Unicode 15.0 단일 생성기**로 JS·Python·PG(`cinema_username_is_valid`) 3계층 동일 정책 적용 + `varchar` 타입 전환 |

### 발표 대본 (한국어)
> 이 슬라이드는 저희 설계의 견고성이 어떻게 만들어졌는지 보여줍니다.
>
> 11월 20일 1차 DB를 넘겼을 때 자체 테스트는 모두 통과했지만, 앱 담당자가 `D1~D6` 기준으로 독립 검증 프로브를 돌리면서 **13개의 불일치**가 드러났습니다. `EXPIRED` 상태 누락, 단가 잠금 누락, 미승인 15분 버퍼 등이었고, 이를 `DB-01`부터 `11`까지 정리해 기준선 `0001`을 확정했습니다. 또한 PostgreSQL에서 같은 이벤트의 `AFTER` 트리거가 알파벳 순으로 실행돼 발생하는 순서 결함도 발견해 `z_consistency`로 바로잡았습니다.
>
> 이후 실전 테스트와 적대적 점검을 거치며 다섯 번의 마이그레이션을 추가했습니다. `0003`에서는 MVCC 환경의 중복 좌석 간극을 막고 총액 컬럼을 `numeric(12,2)`로 확장했고, `0004`에서는 PostgreSQL에서 `'NaN' >= 0`이 참으로 평가되는 함정을 막았습니다. 마지막으로 `0005`와 `0006`에서는 대소문자·전각·보이지 않는 문자를 악용한 계정 ID 우회를 차단하고, 하나의 생성 스크립트로 프런트·백엔드·DB가 정확히 같은 Unicode 15.0 규칙을 쓰도록 통일했습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Slide này cực kỳ đắt giá vì cho thấy trình độ thực chiến của nhóm! Nhấn 3 điểm bất ngờ khiến giáo sư gật gù: **13 Mismatch → 0**, bẫy **`'NaN' >= 0` là TRUE**, và **`0006` đồng bộ 3 tầng từ Unicode 15.0 + `varchar` chống cắt khoảng trắng cuối**. Xong Slide 8 chuyển lại cho Thành viên B!

---

# SLIDE 09 — 백엔드 REST API 및 다층 보안 설계

- **배정 시간:** `0:40` (`06:05 – 06:45`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 좌측에 28개 API 엔드포인트 그룹 요약 표, 우측에 **5대 보안·안정성 방어선** 아이콘 카드.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `08. 백엔드 REST API 및 다층 보안 설계`  
**서브 헤드라인:** 28개 순수 JSON 엔드포인트 · **Fail-Closed 인가** · 안전한 오류 번역 · 자동 트랜잭션 재시도

**[좌측] 28개 REST API 구성 (`docs/api/api_contract.md`)**
| 영역 | 수량 | 주요 엔드포인트 | 인가 정책 |
|---|:---:|---|---|
| **헬스·메타** | 3 | `/api`, `/health`, `/health/db` | `PUBLIC` |
| **인증** | 4 | `/api/auth/{register, login, me, logout}` | `PUBLIC` / `AUTH` |
| **공개 조회** | 5 | `/api/movies*`, `/api/screenings*`, `.../seats` | `PUBLIC` (`D4`) |
| **고객 예매** | 5 | `/api/bookings*`, `.../pay`, `.../cancel` | `CUSTOMER` |
| **관리자** | 11 | `/api/admin/{movies, screenings, bookings}*` | `ADMIN` |

**[우측] 백엔드 5대 방어 메커니즘 (`backend/app/core/`)**
1. **Fail-Closed 라우트 정책 (`security.py`):** 모든 라우트에 `@policy` 필수 선언 — 누락 시 **`create_app()`이 서버 기동 자체를 거부**
2. **Stateless 토큰 + 매 요청 실시간 DB 검증:** `itsdangerous` 토큰(8시간)엔 `user_id`만 보관, 매 요청 `users` 조회로 권한 변경·삭제 즉시 반영
3. **비밀번호 보호 & 타이밍 공격 차단:** `pbkdf2:sha256:600000` 솔트 해시 + 없는 계정에도 더미 해시 검증(`verify_against_dummy`)으로 동일 응답(`401`)
4. **표준 `SQLSTATE` 번역 (`errors.py`):** `UC001~UC011`, `23P01`, `23505`, `23514`만 고정 JSON 에러로 매핑 — SQL·컬럼명·스택 트레이스 노출 0
5. **트랜잭션 자동 재시도 & SQLi 차단:** `40001`/`40P01` 발생 시 새 트랜잭션으로 **최대 3회 재시도**(`run_retryable_transaction`); 100% 파라미터 바인딩(AST 정적 검사) + 엄격한 CORS·보안 헤더

### 발표 대본 (한국어)
> 이 데이터베이스 위에서 동작하는 백엔드는 총 **28개의 순수 JSON REST API**로 구성됩니다.
>
> 가장 신경 쓴 부분은 **Fail-Closed 보안 설계**입니다. 모든 라우트는 네 가지 권한 정책 중 하나를 반드시 선언해야 하며, 하나라도 빠뜨리면 Flask 서버 자체가 기동되지 않습니다. Bearer 토큰에는 역할 정보를 넣지 않고 `user_id`만 서명해 매 요청마다 DB에서 현재 계정을 다시 확인합니다.
>
> 또한 PostgreSQL 오류는 `pgcode`로만 번역해 내부 SQL이나 제약명이 클라이언트로 새지 않게 막았고, 직렬화 실패 `40001`이나 데드락 `40P01`이 발생하면 `run_retryable_transaction`이 새 트랜잭션으로 최대 3회까지 안전하게 재시도합니다. 모든 SQL 쿼리는 100% 파라미터 바인딩을 사용하며 AST 테스트로 강제합니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Giữ nhịp gọn 40 giây. Đừng đọc từng endpoint — chỉ lướt 4 cụm chính rồi nhấn mạnh 3 cơ chế nổi bật: **Fail-Closed startup guard**, **SQLSTATE mapping không lộ DB**, và **retryable transaction cho `40001`/`40P01`**.

---

# SLIDE 10 — 프런트엔드 SPA 및 사용자 경험

- **배정 시간:** `0:30` (`06:45 – 07:15`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 좌측에 12개 화면 흐름 요약 + 주요 UX/보안 포인트 4개, 우측에 실제 웹 UI 스크린샷 2장 콜라주 *(추천 캡처: `http://localhost:8080/` 홈 + `http://localhost:8080/seats.html?screening_id=...` 좌석 선택 화면)*.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `09. 프런트엔드 SPA 및 사용자 경험`  
**서브 헤드라인:** React 19 + TypeScript 12개 화면 · 끊김 없는 비회원→예매 흐름 · 클라이언트 보안

**핵심 구현 포인트 (`frontend/src/` & `frontend/server.py`)**
1. **비회원 좌석 선택 → 로그인 후 복원 (`D4`):**  
   비로그인 상태에서 다중 좌석 선택 → `login.html?next=...` (`encodeURIComponent` 보존) → 가입·로그인 후 **선택 좌석 그대로 복귀**
2. **실시간 10분 카운트다운 & 중복 클릭 방지 (`UI-01`):**  
   서버 `expires_at` 기준 카운트다운 + 만료 시 서버 재확인(`confirmExpiry`); `useRef` 동기 잠금(`inFlight`)으로 더블클릭·연타·새로고침 중복 요청 차단
3. **XSS·경로 탐색 원천 차단 (`SEC-01`):**  
   `innerHTML` 미사용(전부 텍스트 렌더링) + `frontend/server.py` 엄격한 `CSP` (`script-src 'self'`), `..`/심볼릭 링크 차단, 금액 부동소수점 미사용(문자열 포맷)
4. **반응형 & 레거시 폴백:**  
   `320px`(모바일) ~ `1440px`(데스크톱) 검증 완료 · `CINEMA_LEGACY_UI=1`로 순수 HTML/JS 폴백 UI 즉시 전환

### 발표 대본 (한국어)
> 프런트엔드는 React 19와 TypeScript로 12개 화면을 구현했습니다.
>
> 사용자 흐름에서 세 가지에 집중했습니다. 첫째, 비회원이 여러 좌석을 고른 뒤 로그인이나 회원가입을 거쳐도 선택 상태가 유지되도록 연결했습니다. 둘째, 결제 화면에서는 서버의 `expires_at` 기준으로 10분 카운트다운을 보여주고, `useRef` 동기 잠금으로 더블클릭이나 네트워크 재시도에도 중복 예매가 발생하지 않게 막았습니다. 셋째, `innerHTML`을 전혀 쓰지 않고 정적 서버의 엄격한 CSP를 적용해 XSS를 차단했으며, 320픽셀 모바일부터 데스크톱까지 반응형 레이아웃을 검증했습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Slide ngắn 30 giây, tập trung làm nền cho phần Test (Slide 11) và Live Demo Web (Slide 12).

---

# SLIDE 11 — 5계층 자동 검증 전략 및 결과 (`0006`)

- **배정 시간:** `0:50` (`07:15 – 08:05`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 상단 큰 KPI 숫자 4개 카드(**`1,415` pytest** · **`177 + 31` SQL 검증** · **`16/16` 동시성** · **`121 + 8` FE/E2E**), 하단 5계층 상세 표 + 실행 명령어 1줄.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `10. 5계층 자동 검증 전략 및 결과 (Schema 0006)`  
**서브 헤드라인:** 단일 명령 `docker compose --profile test run --build --rm verify`로 격리 DB(`tmpfs`)에서 전 계층 검증

| 검증 계층 | 도구 및 대상 | 최종 검증 결과 (`0006`) | 핵심 검증 범위 |
|---|---|---|---|
| **1. SQL 무결성·대조** | `integrity_tests.sql`, `reconciliation_probes.sql`, `money_domain.sql` | **177** 무결성 · **31/31 MATCH** · **5개 Mutation 검증** 통과 | `D1~D6`, 트리거 순서, `NaN`/무한대 차단, 50석 최대 금액(`4,999,999,999.50`) |
| **2. 다중 세션 동시성** | `test_booking_concurrency.py` (`C1~C6`) | **16/16 PASS** | 8세션 1좌석 경합, 40결제 vs 2만료(10분 경계), 20결제 vs 취소, 5병렬 만료 |
| **3. 백엔드 API·보안** | `pytest` (32개 테스트 파일) | **1,415 PASS, 1 SKIP** *(55.21초)* | 권한 매트릭스, SQLi/XSS(AST 검사), **`0001→0006` 업그레이드**, **28개 계정 ID 매트릭스(`U-01~U-28`)** |
| **4. 프런트 단위·타입** | `npm test` (Node) · `tsc --noEmit` | **121/121 PASS** · 타입 오류 0 | 좌석·마감·포맷·보안 URL·계정 ID 정책 JS 일치 |
| **5. 브라우저 E2E·복원** | Playwright (Chromium) · `pg_dump`/`pg_restore` | **6/6 React E2E** + **2/2 Legacy E2E** + **덤프·업그레이드 복원 PASS** | 모바일(`320/375px`)·데스크톱(`1440px`), `UI-01` 더블클릭/뒤로가기, `SEC-01` XSS, `0005→0006` 복원 정합성 |

### 발표 대본 (한국어)
> 구현한 시스템은 수동 확인에만 의존하지 않고, **5계층 자동 검증 파이프라인**으로 검증했습니다.
>
> SQL 계층에서는 177개 무결성 검사와 31개 대조 프로브를 통과했고, 일부러 트리거를 망가뜨려 테스트가 실제로 실패하는지 확인하는 **5개 변이 검증**까지 수행했습니다. 동시성 계층에서는 8개 세션이 한 좌석을 동시에 노리거나 40개 결제와 2개 만료가 10분 경계에서 충돌하는 6개 시나리오 `16/16`을 모두 통과했습니다.
>
> 최신 `0006` 기준 Docker Compose 통합 검증에서 **pytest 1,415건 통과**, **Node 단위 테스트 121건**, **Playwright 실제 브라우저 E2E 6건과 레거시 2건**, 그리고 `0005`에서 `0006`으로의 무중단 복원 및 덤프 정합성까지 모두 확인했습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Nhấn mạnh số liệu cập nhật mới nhất `0006` (`1,415` pytest, `16/16` concurrency, `28` ca username matrix, `6+2` Playwright, và `5` mutation checks). Xong slide này chuyển thẳng sang màn hình trình duyệt cho **Live Demo 1**!

---

# SLIDE 12 — 실시간 시연 ①: 웹 애플리케이션 (2분)

- **배정 시간:** `2:00` (`08:05 – 10:05`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 시연 시작 전 5초간 시나리오 로드맵을 화면에 띄운 뒤 즉시 브라우저(`http://localhost:8080`)로 전환. 좌측 `고객 시나리오 (60초)` / 우측 `관리자 시나리오 (60초)` 2단 카드.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `11. 실시간 시연 ① — 웹 애플리케이션 (Docker Compose)`  
**실행 환경:** `http://localhost:8080` (React SPA) ↔ `http://localhost:5000/health/db` (Flask + PostgreSQL 18)

**[시나리오 A · 고객 흐름 — 60초]**
1. **비로그인 탐색 (`D4`):** 영화 상세 → 내일 상영 일정 → 좌석 **`A1, A2`** 선택
2. **로그인 연속성:** `Proceed to booking` → `customer1` 로그인 → **선택 좌석 그대로 유지**
3. **예매 확정 & 10분 기한 (`D3, D6`):** `BOOKED / UNPAID`, 총액 `₩24,000` (데모 단가 ₩12,000 × 2), 카운트다운 확인
4. **모의 결제 & 취소 (`D1`):** `Pay Now` → `PAID` 전환 → `My Bookings`에서 **취소** → `CANCELLED / PAID` 이력 보존 + 좌석표에서 **`A1, A2` 즉시 재오픈 확인**

**[시나리오 B · 관리자 흐름 & D2 보호 — 60초]**
1. **영화 등록 (`A-01`):** `admin` 로그인 → `Movies (Admin)`에서 신규 영화 등록
2. **시간 겹침 차단 (`BR-04`):** `Screenings (Admin)`에서 `Hall 1` 동일 시간대 등록 시도 → **`409 screening_overlap` 차단** 후 정상 등록
3. **이력 있는 상영 보호 (`D2`):** 방금 취소 이력이 생긴 상영의 가격 변경 시도 → **`409 screening_has_bookings` 차단**
4. **전체 이력 조회 (`A-03`):** `All Bookings`에서 `CANCELLED` 필터링으로 보존된 이력 확인

### 발표 대본 (한국어 — 브라우저 조작과 함께 구술)
> 지금부터 Docker Compose 3개 컨테이너 위에서 실행 중인 웹 애플리케이션을 직접 시연하겠습니다.
>
> 먼저 비로그인 상태에서 영화와 내일 상영 일정을 열고 `A1, A2` 두 좌석을 고르겠습니다. 예매 버튼을 누르면 로그인 화면으로 이동하는데요, `customer1`으로 로그인하면 조금 전 고른 두 좌석이 그대로 유지된 채 돌아옵니다. 예매를 확정하면 `BOOKED / UNPAID` 상태로 `₩24,000`과 10분 결제 카운트다운이 표시됩니다.
>
> `Pay Now`로 모의 결제를 완료해 `PAID`로 바꾼 뒤, `My Bookings`에서 예매를 취소하겠습니다. 보시면 `CANCELLED`와 `PAID` 이력, 총액이 그대로 남고, 다시 좌석 배치도로 돌아가면 `A1, A2`가 즉시 예매 가능 상태로 풀린 것을 확인할 수 있습니다.
>
> 이제 미리 열어 둔 관리자 탭(`admin`)으로 넘어가겠습니다. 새 영화를 하나 추가한 뒤, 상영 일정 관리에서 일부러 같은 상영관의 겹치는 시간으로 등록해 보겠습니다. PostgreSQL의 `EXCLUDE` 제약이 즉시 겹침을 차단합니다. 마지막으로 방금 취소 이력이 남았던 상영의 가격 수정을 시도하면 **D2 규칙**에 따라 차단되고, `All Bookings`에서 `CANCELLED` 필터로 해당 이력을 조회할 수 있습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> **Lưu ý vàng:** Mở sẵn 2 cửa sổ trình duyệt trước giờ G (1 tab thường `http://localhost:8080`, 1 tab ẩn danh đã mở sẵn `/admin-movies.html` đăng nhập `admin`). Nếu thao tác gọn, chỉ mất đúng 1:50–2:00 rồi chuyển ngay terminal cho Thành viên A!

---

# SLIDE 13 — 실시간 시연 ②: SQL 데이터 제어 · 예외 · 권한 검증 (3분 10초)

- **배정 시간:** `3:10` (`10:05 – 13:15`) · **발표자:** 응오후인느 (A)
- **레이아웃 & 시각 자료:** 시연 전 5초간 3개 스크립트 요약 카드를 띄운 뒤, 미리 열어 둔 `db` 컨테이너 터미널(`/tmp/demo`)에서 3개 스크립트를 순서대로 실행.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `12. 실시간 시연 ② — SQL 데이터 제어 · 예외 · 권한 검증`  
**실행 환경:** 격리 DB `cinema_test_demo` (Schema `0006` + `guard.sql` 보호 · 모든 주 스크립트 끝 `ROLLBACK`으로 원상 복구)

| 순서 (시간) | 준비 스크립트 (`database/demo/`) | 즉시 증명 항목 |
|---|---|---|
| **① 상태 변경** (~0:55) | **`main.sql`** | • 6편/250석/280회 확인 → `create_booking` 2석 (`BOOKED/UNPAID`, `24,000.00`)<br>• `pay_booking` → `cancel_booking` → **`CANCELLED/PAID`, `active_seats = 0`**<br>• 다른 고객(user 3)이 해제된 1번 좌석 **재예매 성공** |
| **② 예외 차단** (~0:50) | **`exceptions.sql`** | API를 거치지 않은 직접 SQL에서도 DB가 즉시 차단:<br>• 중복 좌석 **`UC002`** · 다른 상영관 좌석 **`UC003`**<br>• 상영 시간 겹침 **`23P01`** · `'NaN'` 및 `-1` 가격 **`23514`** (`0004`) |
| **③ 권한 검증** (~1:05) | **`permissions_grants.sql`** | • `cinema_api` 속성 확인 (`LOGIN`, 비슈퍼유저) 및 **7개 테이블 권한표**<br>• 트랜잭션 내 `REVOKE INSERT ON showtimes` (`t → f`) 후 `GRANT` 복구<br>• `SET LOCAL ROLE cinema_api` 전환 후 **`DELETE bookings` / `UPDATE seats` / `UPDATE users`** → 모두 **`42501` (`insufficient_privilege`)** 거부 |
| **예비 (Q&A)** | `concurrency_{prepare,a,b}.sql` | 2개 터미널 동시 경합: 세션 A 커밋 전까지 B 대기 → A 커밋 직후 B **`UC002`** 거부 |

### 발표 대본 (한국어 — 터미널 실행과 함께 구술)
> 다음으로 교수님께서 강조하신 **데이터 제어·예외 상황·권한 검증**을 미리 준비한 SQL 스크립트로 직접 보여드리겠습니다. 웹 운영 DB를 건드리지 않도록 격리된 `cinema_test_demo` DB에서 실행하며, 세 스크립트 모두 마지막에 `ROLLBACK`으로 깔끔하게 되돌립니다.
>
> 첫 번째로 **`main.sql`**입니다. *(실행)* 6개 영화, 250개 좌석, 280개 상영을 확인한 뒤 고객 2가 2개 좌석을 예매해 `BOOKED / UNPAID`, `24,000원`이 생성됩니다. 이어서 결제 후 취소하면 `bookings`에는 `CANCELLED / PAID`와 `24,000원`이 그대로 남지만 `active_seats`는 0이 되며, 곧바로 고객 3이 같은 1번 좌석을 다시 예매하는 데 성공합니다.
>
> 두 번째로 **`exceptions.sql`**입니다. *(실행)* 백엔드 API를 통하지 않고 SQL로 직접 위반을 시도해도, 중복 좌석은 `UC002`, 다른 관 좌석은 `UC003`, 같은 관 시간 겹침은 `23P01`, 그리고 `NaN`과 음수 가격은 `0004` 제약에 의해 `23514`로 모두 차단됩니다.
>
> 세 번째로 **`permissions_grants.sql`**입니다. *(실행)* 앱이 사용하는 런타임 역할 `cinema_api`는 슈퍼유저 권한이 없는 일반 로그인 역할이며, 7개 테이블별 최소 권한 표를 보실 수 있습니다. 여기서 `REVOKE INSERT ON showtimes`를 실행하면 즉시 권한이 `true`에서 `false`로 바뀌고, `GRANT`로 복구됩니다. 마지막으로 `SET LOCAL ROLE cinema_api`로 전환해 `bookings` 삭제, `seats` 수정, `users` 권한 상승을 시도하면 세 명령 모두 **`42501` 권한 부족 오류**로 거부되는 것을 확인하실 수 있습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Phóng to font terminal (`Ctrl + +`) lên ít nhất `16–18pt` trước giờ thuyết trình để cả lớp & giáo sư nhìn rõ các dòng `NOTICE: 예상된 오류: UC002 / UC003 / 23P01 / 23514` và `42501`! Kịch bản `concurrency_a/b.sql` để dành riêng cho Q&A nếu giáo sư hỏi thêm.

---

# SLIDE 14 — [필수] AI가 모든 것을 다 해주는 시대에 팀 단위 프로젝트가 왜 의미가 있는가?

- **배정 시간:** `1:15` (`13:15 – 14:30`) · **발표자:** 응오후인느 (A: 항목 1~2, ~0:40) → 응웬치롱 (B: 항목 3 + 결론 메시지, ~0:35)
- **레이아웃 & 시각 자료:** 상단에 질문 원문과 **핵심 답변 배너**, 중앙에 **우리 팀의 실제 경험 3개 카드** (숫자·실제 산출물명 강조), 하단에 한 줄 결론 박스.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `13. AI가 모든 것을 다 해주는 시대에 팀 단위 프로젝트가 왜 의미가 있는가?`  
**핵심 결론:** ***"의미가 있다 — 오히려 역할이 '코드 분업'에서 '규칙 합의 · 사각지대 교차 검증 · 최종 책임'으로 더 중요해졌다."***

**[실제 Cinema 프로젝트 수행 경험 기반 3가지 근거]**

| # | 팀 프로젝트만의 본질적 가치 | 우리 프로젝트의 실제 증거 |
|---|---|---|
| **1** | **업무 경계 결정과 계약 수립** *(Decision Ownership)* | AI는 SQL과 React를 순식간에 생성하지만, *취소 시 좌석 삭제 여부(`D1`)*·*10분 만료(`D3`)*·*`GUEST` 제외(`D4`)*를 대신 결정하지 못함 → A·B 역할 분리 덕분에 **`BR-DL-001`**과 두 연동 계약을 명문화 |
| **2** | **'그럴듯한 환각'을 깨는 교차 검증** *(Cross-Review)* | 11/20 1차 DB는 깔끔해 보였고 자체 테스트도 통과했지만, 상대 팀원의 독립 프로브 대조로 **13개 업무 불일치**(누락된 `EXPIRED`·단가 잠금·미승인 15분 버퍼)를 발견 → 혼자 AI를 쓸 때 빠지기 쉬운 확증 편향 극복 |
| **3** | **경계 결함 발굴과 끝까지 책임지는 태도** *(Accountability)* | 알파벳 순 트리거 오류, MVCC 중복 간극(`0003`), PostgreSQL `'NaN' >= 0` 함정(`0004`), 계정 ID 공백·전각 우회(`0005~0006`)는 **DB와 앱 두 시각이 서로 밀어붙이며 검증**한 끝에 찾아낸 결과 |

**[하단 결론 메시지]**
> *"AI는 코드를 빠르게 생성할 수 있지만, **무엇이 옳은 업무 규칙인지 합의하고, 계층 간 사각지대를 교차 검증하며, 최종 운영 결과에 책임지는 일**은 여전히 팀의 몫입니다."*

### 발표 대본 (한국어)
> **[응오후인느 (A) — 0:40]**  
> 마지막으로 과제에서 제시된 질문, **"AI가 모든 것을 다 해주는 시대에 팀 단위 프로젝트가 왜 의미가 있는가?"**에 대해 저희 팀의 실제 경험으로 답하고자 합니다. 결론부터 말씀드리면 **여전히 큰 의미가 있으며, 그 본질이 바뀌었습니다.**
>
> 첫째, AI는 지시가 명확하면 코드를 빠르게 짜지만, 어떤 업무 규칙을 선택할지는 결정하지 못합니다. 저희는 DB 리드와 앱 리드로 역할을 나눴기 때문에 구현 전에 `D1`부터 `D6`까지의 규칙과 연동 계약을 문서로 합의할 수밖에 없었습니다.
>
> 둘째, 혼자 AI를 쓰면 겉으로 잘 도는 코드를 그대로 믿기 쉽습니다. 실제로 11월 20일 1차 스키마는 자체 테스트를 모두 통과했지만, 팀원이 독립 프로브로 교차 대조하면서 **13개의 업무 불일치**를 잡아낼 수 있었습니다.
>
> **[응웬치롱 (B) — 0:35]**  
> 셋째, 저희가 해결한 트리거 실행 순서 문제나 MVCC 중복 간극(`0003`), PostgreSQL의 `'NaN' >= 0` 함정(`0004`), 그리고 계정 ID 공백·유니코드 우회(`0005~0006`)는 AI가 먼저 알려준 것이 아니라, 서로 다른 계층을 책임진 두 사람이 끝까지 적대적으로 검증하며 찾아낸 결함들입니다.
>
> 따라서 AI 시대의 팀 프로젝트는 단순히 코딩을 나눠 하는 연습이 아니라, **올바른 문제를 정의하고, 계약을 지키며, 서로의 사각지대를 교차 검증해 시스템 전체에 책임지는 훈련**이라는 점에서 더 큰 의미를 가진다고 생각합니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Đây là slide thể hiện chiều sâu tư duy nên hai bạn chia nhau nói cực kỳ tự nhiên và chân thực! Nhìn trực tiếp vào giáo sư ở câu chốt cuối cùng.

---

# SLIDE 15 — 결론 및 향후 확장 계획

- **배정 시간:** `0:30` (`14:30 – 15:00`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 좌우 2단 분할 — 좌측 `달성 성과 (체크리스트 4개)`, 우측 `향후 확장 방향 (MVP 범위 외 3개)`.

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

**슬라이드 제목:** `14. 결론 및 향후 확장 계획`

**[좌측] 프로젝트 핵심 달성 성과**
- ✅ **DB 중심 무결성 엔진:** PostgreSQL 18 (`0001~0006`), 7테이블 3NF, 9트리거, 5함수, `cinema_api` 최소 권한 분리
- ✅ **완전 분리 3계층 아키텍처:** 노트북 컨테이너 (`frontend:8080` · `api:5000`) + 클라우드 DB (Neon PostgreSQL 18)
- ✅ **전 기능 완성:** 14개 업무, 28개 REST API, 12개 React/TS 화면 (+ 레거시 UI 폴백), 12종 산출물 정합성 확보
- ✅ **5계층 자동 검증 통과:** pytest `1,415` · SQL `177+31` · 동시성 `16/16` · Node `121` · Playwright `6+2` · 덤프/업그레이드 복원

**[우측] 향후 확장 계획 (승인된 MVP 범위 외)**
- **실제 결제 게이트웨이 & 환불 상태 모델:** `CANCELLED + PAID` 이력 기반 정산·환불 워크플로우 연동
- **서버 측 토큰 폐기 & 운영 보안 강화:** Redis 블랙리스트 기반 로그아웃 즉시 무효화, HTTPS 리버스 프록시, 요청 속도 제한
- **서비스 확장:** 다중 영화관 지점 관리, 동적 상영관 좌석 편집, 매점 콤보 주문 및 알림 연동

### 발표 대본 (한국어)
> 정리하겠습니다. 본 프로젝트는 영화관 예매 업무를 기획·규칙 합의부터 3NF 모델링, PostgreSQL 무결성 엔진, 3계층 분리 아키텍처, 그리고 5계층 자동 검증까지 일관되게 완성했습니다.
>
> 향후에는 이 견고한 데이터 기반 위에 실제 결제·환불 연동, Redis 기반 토큰 폐기, 그리고 다중 지점 확장으로 발전시킬 수 있습니다.

### Ghi chú nhịp nói (Tiếng Việt)
> Gọn trong 25–30 giây để chốt vừa khít mốc 15:00 rồi bấm qua Slide 16.

---

# SLIDE 16 — 감사합니다 (Ending Slide)

- **배정 시간:** 종료 (`15:00`) · **발표자:** 응웬치롱 (B)
- **레이아웃 & 시각 자료:** 표지(Slide 01)와 통일된 다크 네이비(`#0F172A`) 미니멀 배경. 중앙에 깔끔하게 **`감사합니다`**만 배치 (Q&A 텍스트 미포함).

### 슬라이드 화면 텍스트 (PPT 그대로 입력)

> # **감사합니다**
> Thank you for listening.

### 발표 대본 (한국어)
> 이상으로 영화관 예매 및 좌석 관리 시스템 발표를 마치겠습니다. 경청해 주셔서 감사합니다. 질문 있으시면 답변드리겠습니다.

---

# 부록: Q&A 핵심 예상 질문 & 한국어 답변 카드 (5~10분 대비)

*(발표자 참고용 — 슬라이드에 넣지 않고 Q&A 시 즉시 꺼내서 답변)*

| # | 예상 질문 | 한국어 핵심 답변 (담당) |
|---|---|---|
| **Q1** | 왜 10분 만료 처리를 크론 잡(배치 스케줄러) 대신 요청 시점(`expire_overdue_bookings`)으로 구현했나요? | *(A)* 외부 스케줄러 장애나 실행 주기 지연 없이 **마이크로초 단위 정확성**을 보장하기 위해서입니다. 좌석 조회·예매·결제·취소·이력 조회 직전에 같은 트랜잭션에서 `FOR UPDATE SKIP LOCKED`로 만료 처리하므로 멱등하면서도 동시 결제를 막지 않습니다. |
| **Q2** | `booking_seats`에 `showtime_id`를 중복 저장하면 3NF 위반 아닌가요? | *(A)* `booking_id → showtime_id` 때문에 BCNF는 아니지만, `showtime_id`가 새 후보키 `(showtime_id, seat_id)`의 일부이므로 **3NF는 위반하지 않습니다**. MVCC 환경에서 즉시 UNIQUE 인덱스로 중복 좌석을 막기 위한 통제된 중복(`0003`)이며, 복합 FK `(booking_id, showtime_id)`로 부모와 불일치를 원천 차단했습니다. |
| **Q3** | 정확히 10분이 지난 시점(`>= expires_at`)에 결제 버튼을 누르면 어떻게 되나요? | *(A/B)* `pay_booking()`이 `FOR UPDATE`로 예매 행을 잠근 뒤 `clock_timestamp() >= expires_at`을 감지하면 결제를 거부하고, 같은 트랜잭션에서 상태를 `EXPIRED`로 바꾸고 좌석을 해제한 뒤 `'EXPIRED'`를 반환합니다. Flask는 이를 **정상 `COMMIT`**하여 만료를 영구 반영한 뒤 사용자에게 안내합니다. |
| **Q4** | 영화의 상영 시간(`duration_minutes`)을 수정하면 이미 등록된 상영 일정의 종료 시각도 바뀌나요? | *(A)* 바뀌지 않습니다. `ends_at`을 비워 등록할 때만 트리거가 `starts_at + duration_minutes`로 계산해 **고정 저장**합니다. 이후 영화 시간을 고쳐도 기존 일정과 D2 이력 맥락은 유지되고, 새로 등록하는 상영에만 반영됩니다. |
| **Q5** | `ticket_price >= 0` CHECK가 있는데 왜 `0004_finite_money.sql`이 별도로 필요했나요? | *(A)* PostgreSQL의 `numeric` 타입은 `'NaN'`을 모든 유한 숫자보다 큰 값으로 정렬하기 때문에 **`'NaN'::numeric >= 0`이 `TRUE`로 통과**합니다. 그래서 `NOT IN ('NaN', 'Infinity', '-Infinity')` 제약을 3개 금액 컬럼에 추가했습니다. |
| **Q6** | `0006`에서 `users.username`을 왜 `varchar(60)`에서 `varchar`로 바꿨나요? | *(A)* SQL 표준과 PostgreSQL 특성상 `varchar(60)`은 60자를 넘는 **끝 공백을 CHECK 검사 전에 조용히 잘라낼 수** 있습니다. 컬럼을 `varchar`로 바꾸고 `cinema_username_is_valid()` CHECK 함수가 직접 길이(1~60)와 공백 금지·NFKC·Unicode 15.0 형식을 검사하도록 해 직접 SQL 우회까지 막았습니다. |
| **Q7** | 왜 SQLAlchemy 같은 ORM 대신 `psycopg2`를 직접 사용했나요? | *(B)* 데이터베이스 중심 프로젝트로서 트랜잭션 경계(`with transaction():`), 4개 DB 함수 호출, `SQLSTATE`(`UC001~UC011`, `40001`, `40P01`) 처리를 숨김없이 명확하게 제어하기 위해서입니다. 모든 쿼리는 파라미터 바인딩을 사용하며 AST 테스트로 검증합니다. |
| **Q8** | 동시성 충돌로 `40001`이나 데드락 `40P01`이 발생하면 앱은 어떻게 처리하나요? | *(B)* `run_retryable_transaction()`이 실패한 트랜잭션을 롤백하고 **완전히 새로운 트랜잭션으로 최대 3회까지 전체 작업을 재시도**합니다(예매·결제·취소 적용). 반면 이미 남이 잡은 좌석(`UC002`)은 재시도하지 않고 `409 seat_unavailable`을 반환해 재선택을 유도합니다. |
| **Q9** | 프런트엔드와 백엔드/DB가 정말 분리되어 있다는 근거는 무엇인가요? | *(B)* 노트북의 2개 컨테이너(`api`, `frontend`)와 클라우드 Neon의 PostgreSQL로 분리 운영되며, 프런트엔드는 Python 표준 정적 서버로 DB 드라이버나 Flask 코드가 전혀 없고 `/config.js`로 API 주소만 받습니다. API는 `static_folder=None, template_folder=None`으로 순수 JSON만 반환하며, DB는 별도 클라우드 서버에서 SSL로만 접속하고, 앱은 최소 권한의 `cinema_api` 역할만 사용합니다. |
| **Q10** | 권한 분리는 어디에서 어떻게 검증되나요? (웹 관리자 페이지 vs SQL 권한) | *(A/B)* **2중 방어(Defense in Depth)**로 구현했습니다. 앱 계층에서는 Fail-Closed `@policy`로 `CUSTOMER`와 `ADMIN`을 엄격히 분리하고(매 요청 DB 역할 재조회), DB 계층에서는 런타임 역할 `cinema_api`에 최소 권한만 부여해(`bookings DELETE`, `users/seats UPDATE` 차단 — `42501`) 앱 계정이 탈취돼도 이력 삭제나 권한 상승이 불가능합니다. |
