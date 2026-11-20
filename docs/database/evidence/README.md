# PostgreSQL 최종 검증 증빙

2026년 11월 21일(KST), `database-remediation`의 DB 구현 커밋 `65c9632a1becb1282ec020111c7c3c94ecff4a2b`를 PostgreSQL 18.7에서 검증했다. 임시 클러스터는 새로 초기화했고 Unix 소켓만 사용했다. 표준 런너와 원문 수집용 개별 단계는 같은 임시 클러스터의 서로 다른 새 UTF-8 데이터베이스에서 실행했다. 아래 로그는 실제 표준 출력과 표준 오류를 저장한 것이다. 배포용 사본에서는 로컬 운영체제 계정과 저장소 절대 경로를 가렸으며, 행 끝 공백과 파일 끝 빈 줄을 정리하였다. 검사 출력, 집계 및 종료 코드는 유지하였다.

| 파일 | 증빙 |
|---|---|
| [environment.log](environment.log) | 실행 시각, 브랜치, 커밋, 운영체제, PostgreSQL·Python·psycopg2 버전, 인코딩, 시간대 및 접속 방식 |
| [cluster_setup.log](cluster_setup.log) | 새 클러스터 초기화, 기동 및 종료 |
| [run_all.log](run_all.log) | 표준 런너의 전체 출력과 테스트 DB 정리 |
| [schema.log](schema.log), [seed.log](seed.log) | 원문 수집용 DB의 DDL 및 시드 적용 결과 |
| [catalog_counts.log](catalog_counts.log) | 시드 직후 테이블·행 수, 실제 제약 및 정의자 권한 함수 카탈로그 |
| [integrity.log](integrity.log), [reconciliation.log](reconciliation.log) | 통합 SQL 검사의 개별 출력, 대조 검사 및 P16의 예상 커밋 실패 |
| [concurrency.log](concurrency.log), [application_role.log](application_role.log) | 동시성 검사와 실제 권한 스크립트로 구성한 임시 역할 검사 |
| [exit_status.tsv](exit_status.tsv) | 런너와 개별 단계의 종료 코드 |

런너와 개별 동시성 실행에서는 요청 순서가 달라 C4 결과 분포가 서로 달랐다. 두 실행 모두 58개 동시성 검사를 통과했다. 대조 로그에 포함된 P16의 오류는 좌석 없는 예매의 커밋 거부를 확인하는 의도된 결과이며, 검사 종료 코드와 후속 남은 행 수로 통과를 확인한다.

## 발표용 터미널 화면 캡처

저장소 루트에서 필요한 명령을 실행해 **실제 출력 화면**을 캡처한다. 아래 명령은 저장된 증빙을 읽으므로 DB에 연결하지 않는다.

```bash
git branch --show-current
git rev-parse HEAD
cat docs/database/evidence/environment.log

cat docs/database/evidence/seed.log
sed -n '1,20p' docs/database/evidence/catalog_counts.log

grep -E 'BR-07 seat of another room|BR-04 overlapping screening|cancelled history still locks|expired booking cannot be paid|ALL 199' docs/database/evidence/integrity.log

grep -E 'C7 .*rejects|C8 .*commits expiration|C9 lock timeout|RESULT:' docs/database/evidence/concurrency.log

grep -E 'SUMMARY|P16.*MATCH' docs/database/evidence/reconciliation.log
cat docs/database/evidence/application_role.log docs/database/evidence/exit_status.tsv
tail -n 8 docs/database/evidence/run_all.log
```

캡처는 ① 실행 버전·커밋, ② 테이블 7개와 시드 행 수, ③ 잘못된 좌석·겹치는 상영·취소 이력 제약, ④ 격리 수준별 중복 방지와 잠금 후 만료, ⑤ 대조·권한 검사 및 종료 코드 순으로 구성한다. ERD 화면은 [개념](../erd/conceptual.svg), [논리](../erd/logical.svg), [물리](../erd/physical.svg)의 실제 SVG 또는 PNG를 사용한다. 캡처 이미지는 이 증빙 디렉터리에 생성하지 않았다.

실시간 재현이 필요한 경우 [격리 검증 절차](../postgresql_setup_guide.md)를 따른다. 사용 중인 데이터베이스나 기존 서버의 접속 정보를 재사용하지 않는다.
