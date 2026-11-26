# 데이터 모델 파일 (ER 모델링 도구 산출물)

교수님이 요구한 모델링 도구 파일(erwin 등)에 해당하는 산출물이다. erwin이 없어서 **draw.io (diagrams.net) 데스크톱 32.7.4**(무료, `winget install JGraph.Draw`)를 사용했다. draw.io는 범용 다이어그램 도구라 DB와 자동으로 동기화되지는 않는다. 대신 모델의 내용은 **실제 DB 카탈로그(마이그레이션 `0001`~`0006` 적용 결과)에서 뽑아 만들어** 문서와 DB에 어긋나지 않게 했다.

| 파일 | 내용 |
|---|---|
| `cinema_model.drawio` | 모델 원본 파일 (draw.io에서 열기). 페이지 3개: 논리적 모델, 물리적 모델, 제약조건·인덱스·트리거 |
| `cinema_model.pdf` | 0006 모델 3페이지 PDF |
| `cinema_model_logical.png` | 논리적 모델: 엔티티 7개, 속성의 한글 논리명과 물리명, PK/FK/UK, 관계(크로우풋 표기) |
| `cinema_model_physical.png` | 물리적 모델: 테이블 7개, 컬럼 타입, NOT NULL, PK/FK/UK, 관계 |
| `cinema_model_constraints.png` | 물리적 모델 보충: 테이블별 UNIQUE, FK, CHECK, EXCLUDE, 인덱스, 트리거 |
| `meta_query.sql`, `gen_drawio.py` | 모델을 다시 만드는 입력 쿼리와 생성 스크립트 |

## 열기

- draw.io 데스크톱 또는 https://app.diagrams.net 에서 `cinema_model.drawio`를 연다 (계정 불필요). 페이지 탭으로 논리/물리/제약 모델을 전환한다.
- 다른 도구를 쓰는 경우: 현재 DDL은 `backend/migrations/`, 문서는 `docs/database/`에 있다.

## 다시 만들기 (스키마가 바뀐 경우)

1. 격리 서버의 빈 DB에 `backend/migrations/0001`, `0003`, `0004`, `0005`, `0006`을 적용한다.
2. `psql -X -At -d <DB> -f database/model/meta_query.sql > meta.json`
3. `python database/model/gen_drawio.py meta.json database/model/cinema_model.drawio`
4. 이미지 내보내기: `draw.io.exe -x -f png -p <페이지 번호(1부터)> -s 2 -b 20 -o 출력.png cinema_model.drawio`, PDF는 `-f pdf --all-pages`.

## 한계

- 논리 모델의 한글 속성명은 문서(`docs/database/`)의 용어에 맞춰 `gen_drawio.py`에 적어 둔 것이다. DB에는 저장되어 있지 않다.
- 도구가 DB와 양방향으로 동기화하지 않으므로, 스키마를 바꾸면 위 절차로 다시 만들어야 한다.

0005 모델은 [보존본](../history/0005/README.md)에서 확인할 수 있다. 0006에서는 사용자 이름의 물리 타입과 CHECK만 바뀌므로 기존 개념 관계와 카디널리티를 유지했다.
