# PostgreSQL 데이터베이스

이 디렉터리는 영화관 예매 시스템의 기준 DDL, 시드, 권한 및 테스트를 제공한다. 개선판 DB는 PostgreSQL 18.7의 신규 UTF-8 데이터베이스에서 검증했다. 배포 전 Member B의 좌석 조회 전환과 응용 프로그램 통합 검증이 필요하다.

| 파일 | 용도 |
|---|---|
| schema.sql | 일곱 테이블, 제약, 인덱스, 트리거 및 업무 함수. 신규 빈 DB에 한 번 적용한다. |
| seed.sql | 데모 계정 3개, 영화 5편, 상영관 5개, 좌석 250개, 서울 시간 기준 7일 동안 상영 일정 140개를 구성한다. |
| grant_application_role.sql | 전용 앱 역할에 필요한 객체 및 열 권한과 업무 함수 실행 권한을 부여한다. |
| tests/run_all.sh | 신규 폐기용 UTF-8 DB에서 하위 테스트를 실행한다. |
| tests/integrity_tests.sql | 무결성 SQL 검사 199건. |
| tests/reconciliation_probes.sql | 대조 검사 31건과 별도 커밋 실패 확인. |
| tests/test_concurrency.py | PostgreSQL 세션 간 동시성 검사 58건. |
| tests/test_application_role.py | 임시 앱 역할로 업무 실행과 권한 제한을 검증한다. |

설치 순서는 신규 UTF-8 DB 생성 → 스키마 → 시드 → 권한 스크립트다. 위치, 소유자 및 접속 설정은 [PostgreSQL 설치 안내서](../10_설치_및_연동_가이드/postgresql_setup_guide.md)를 따른다. [검증 결과](../08_데이터베이스_검증/database_test_documentation.md), [Flask 연동 계약](../10_설치_및_연동_가이드/postgresql_flask_integration_contract.md), [Member B 인수인계](../10_설치_및_연동_가이드/member_b_integration_handover.md)를 함께 제공한다. 역사적 인수인계 ZIP 및 기존 [대조 보고서](https://github.com/unhodrgn/Cinema-Reservation-System/blob/121854a0e006d824dd4aba7274deec7524da9694/docs/database/handover_reconciliation_report.md)는 이전 기준의 참고 자료다.

## 제출 자료 확인

- [개념 모델](../01_개념적_데이터_모델/conceptual_data_model.md), [논리 모델](../02_논리적_데이터_모델_및_정규화/logical_data_model.md), [물리 모델](../03_물리적_데이터_모델/physical_data_model.md)에 편집용 ERD와 SVG·PNG가 있다.
- [정규화](../02_논리적_데이터_모델_및_정규화/normalization.md), [용어사전](../04_용어사전/glossary.md), [도메인 정의](../05_도메인_정의서/domain_definition.md), [테이블 기술서](../06_테이블_기술서/table_description.md)를 제공한다.
- DB 인수인계 목록의 모델, DDL, 시드 및 검증 보고서는 저장소에서 확인할 수 있다. 원본 실행 로그와 발표용 캡처 명령은 [검증 증빙](../08_데이터베이스_검증/evidence/README.md)에 있다. 별도 스크린샷 제출 형식은 수업 지침을 확인한다. 기존 DB 이전 스크립트와 신규 API의 브라우저 통합 검증은 현재 제출물에 포함되지 않는다.
