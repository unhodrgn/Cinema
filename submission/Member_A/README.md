# 영화관 예매 시스템 — Member A 데이터베이스 제출 패키지

대상 브랜치는 database-remediation이며, 데이터베이스 기준 커밋은 121854a0e006d824dd4aba7274deec7524da9694이다. 이 패키지는 Member A의 모델, 용어사전, DDL, 시드, 권한, 검증 증빙, 시연 및 Member B 연동 계약을 제공한다. 기존 애플리케이션 코드는 저장소에서 참조하며 변경된 연동의 완료나 출시를 주장하지 않는다.

## 제출 요구사항 대응

| 폴더 | 제출 내용 |
|---|---|
| 01_개념적_데이터_모델 | 개념 설명 PDF·Markdown, Draw.io·SVG·PNG |
| 02_논리적_데이터_모델_및_정규화 | 논리 관계·키·정규화 PDF·Markdown, 논리 ERD |
| 03_물리적_데이터_모델 | PostgreSQL 자료형·제약·인덱스·트리거·함수 PDF·Markdown, 물리 ERD |
| 04_용어사전 | 필수 용어사전 PDF·Markdown |
| 05_도메인_정의서 | 데이터 도메인 PDF·Markdown |
| 06_테이블_기술서 | 일곱 테이블 상세 PDF·Markdown |
| 07_PostgreSQL_구현 | 수정 없이 복사한 DDL·시드·권한 SQL, 의존성 목록 및 DB 안내 PDF·Markdown |
| 08_데이터베이스_검증 | 검증 보고서 PDF·Markdown, 표준 테스트 소스, 실제 로그와 종료 코드 |
| 09_시연용_SQL | 초기화·검증·정리 명령, SQL 시연 단계, 안내 PDF·Markdown 및 실제 실행 로그 |
| 10_설치_및_연동_가이드 | 신규 설치 안내, Flask 연동 계약, Member B 인수인계 및 15분 팀 발표 원고의 PDF·Markdown |

## 패키지에서 SQL 실습

저장소를 사용하는 경우 시연 안내의 명령을 저장소 루트에서 그대로 실행한다. 이 패키지만 가지고 실행할 때는 다음 명령으로 새 작업 디렉터리에 원본의 상대 경로를 복원한다. PostgreSQL 도구와 psycopg2가 설치된 Python 환경을 사용한다.

```bash
# 패키지 루트에서 실행
work="$(mktemp -d /tmp/cinema-submission-work.XXXXXX)"
mkdir -p "$work/database"
cp -R "07_PostgreSQL_구현/database/." "$work/database/"
cp -R "08_데이터베이스_검증/database/tests" "$work/database/"
cp -R "09_시연용_SQL/database/demo" "$work/database/"
cp "07_PostgreSQL_구현/requirements.txt" "$work/"
cd "$work"
bash database/demo/verify.sh
```

위 조립 절차의 동작은 별도의 작업 디렉터리에서 검증하였으며 로그는 09의 database/demo/standalone_verification.log에 있다. 시연 런너는 새 UTF-8 서버와 DB를 기동하고 시연 DB를 삭제한 뒤 임시 서버만 중지한다. 기존 서버나 DB를 사용하지 않는다. 08의 DB 테스트는 10의 설치 안내에 있는 별도 격리 검증 절차로 실행한다.

## 남은 통합 승인 조건

Member B는 회차별 좌석 조회 함수, 40001 재시도, 55P03 오류 처리, EXPIRED 커밋, 좌석별 단가·이력 UI를 연동하고 전용 앱 로그인으로 브라우저 회귀를 확인해야 한다. 이 패키지는 DB 측 연동 자료다. 통합 애플리케이션 배포본과 팀 발표 슬라이드는 팀에서 최종 구성한다. 대학 지정 템플릿이나 별도 스크린샷은 포함하지 않았다. 실행 증빙은 실제 출력 로그로 확인한다.
