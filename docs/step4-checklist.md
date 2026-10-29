# STEP 4 — 회원정보·비밀번호·탈퇴·구매내역 확인

사용자가 직접 실행하는 절차입니다. 작성자는 설치, SQL 실행, 서버 실행, 브라우저 조작 및 테스트를 수행하지 않았습니다. 탈퇴 확인은 다른 시나리오를 모두 확인한 뒤 마지막에 진행하세요.

## 1. 적용 방법 — CMD

STEP 3까지의 SQL과 API가 준비되어 있어야 합니다. 이번에는 **step4_functions.sql만** SQL Editor의 새 쿼리에 붙여넣어 전체 실행하세요. CREATE TABLE이 있는 schema.sql을 다시 실행하지 않습니다.

```cmd
cd /d C:\AIO4\Day12_demo\project
chcp 65001 > nul
clip < "C:\AIO4\Day12_demo\project\sql\step4_functions.sql"
```

이 SQL은 기존 테이블과 데이터를 유지하고 함수만 추가합니다. STEP 3의 필수 함수가 없으면 먼저 step3_functions.sql을 실행하라는 오류를 냅니다. 동일 버전의 STEP 4 SQL은 재실행할 수 있습니다.

새 DB는 schema.sql → seed.sql → step3_functions.sql → step4_functions.sql 순서입니다. ch2는 Supabase Data API의 Exposed schemas에 포함되어 있어야 합니다. 함수 실행 권한은 service_role에만 부여합니다.

실행 중인 서버는 Ctrl+C로 종료하고 아래 CMD 명령으로 다시 실행합니다. 추가 패키지 설치나 .env 변경은 없습니다.

```cmd
cd /d C:\AIO4\Day12_demo\project
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

http://127.0.0.1:8000/docs 의 **회원정보·구매내역** 항목에서 Try it out → Execute로 확인합니다. 주소는 APP_ORIGIN과 같아야 합니다.

## 2. API 목록

| 메서드 | 경로 | 요청 본문/쿼리 | 성공 응답 |
|---|---|---|---|
| GET | /api/users/me | 없음 | 200, 본인 회원정보 |
| PATCH | /api/users/me | name/phone/address 중 1개 이상 | 200, 수정한 회원정보 |
| PATCH | /api/users/me/password | current_password, new_password | 200, 변경 메시지 및 쿠키 삭제 |
| DELETE | /api/users/me | current_password | 200, 탈퇴 메시지 및 쿠키 삭제 |
| GET | /api/users/me/purchases | offset=0, limit=20 | 200, items/total/offset/limit |
| GET | /api/users/me/purchases/{order_id} | 경로의 주문 UUID | 200, 결제 완료 주문 상세 |

모두 로그인이 필요합니다. 회원 ID는 요청에서 받지 않고 인증 쿠키에서 확인합니다. 비밀번호 해시와 auth_version은 응답에 포함하지 않습니다.

## 3. 회원정보 조회·수정

1. STEP 2의 POST /api/auth/login으로 로그인합니다.
2. GET /api/users/me를 호출하여 id/email/name/phone/address/created_at/updated_at을 확인합니다.
3. PATCH /api/users/me에 아래 본문을 입력합니다.

```json
{
  "name": "김회원",
  "phone": "010-9876-5432",
  "address": "서울시 마포구 예시로 20"
}
```

4. 200과 변경한 값이 반환되어야 합니다. 다시 GET으로 저장 여부를 확인합니다.
5. 아래처럼 주소만 보내면 이름과 연락처는 유지되어야 합니다.

```json
{"address": "서울시 서초구 예시로 30"}
```

| 추가 확인 | 기대 결과 |
|---|---|
| 앞뒤 공백이 있는 이름 | 공백을 제거하여 저장 |
| 빈 본문 {} | 422 |
| {"name":"   "} 또는 {"name":null} | 422, 기존 값 유지 |
| {"email":"other@example.com"} | 422, 이메일 변경 불가 |
| {"user_id":"다른_회원_UUID"} | 422, 회원 ID 지정 불가 |
| 로그아웃 후 GET/PATCH | 401 |

기존 주문의 배송지와 상품 단가·상품명은 수정되지 않습니다. STEP 3의 기존 주문 ID로 GET /api/orders/{order_id}를 호출하여 확인할 수 있습니다. 새로 만드는 주문에는 수정한 회원정보가 복사됩니다.

## 4. 구매내역

STEP 3에서 결제 성공 주문을 하나 이상 만든 뒤 확인합니다.

| 순서 | 요청 | 기대 결과 |
|---|---|---|
| 1 | GET /api/users/me/purchases | 200, 본인의 paid 주문만 items에 포함 |
| 2 | offset=0, limit=1로 조회 | items 최대 1개, total은 전체 paid 주문 수 |
| 3 | offset을 total보다 크게 지정 | 200, items=[] |
| 4 | 목록의 id로 GET /api/users/me/purchases/{order_id} | 200, 주문 당시 상품명·단가·수량·배송지·금액·결제 완료 시각 |
| 5 | 본인의 pending 주문 ID로 구매내역 상세 요청 | 404 |
| 6 | 회원 B로 로그인하여 회원 A의 paid 주문 상세 요청 | 404 |
| 7 | limit=0 또는 101, offset=-1 | 422 |

목록은 paid_at 내림차순, 같은 시각이면 ID 내림차순입니다. 구매가 없으면 items=[], total=0입니다. 페이지 기본 크기는 20, 최대 100입니다. 상품의 stock 값은 현재 재고이며 주문 당시 재고의 스냅샷은 아닙니다.

회원 B는 별도 브라우저 프로필/시크릿 창에서 가입·로그인합니다. 다른 회원의 주문과 존재하지 않거나 미결제인 주문은 모두 구매내역 상세에서 동일한 404로 처리합니다.

## 5. 비밀번호 변경

PATCH /api/users/me/password에 아래 본문을 넣습니다. current_password는 현재 실제 비밀번호로 바꾸세요.

```json
{
  "current_password": "DemoPass123!",
  "new_password": "ChangedPass456!"
}
```

| 확인 순서 | 기대 결과 |
|---|---|
| 잘못된 current_password로 먼저 요청 | 400, 현재 로그인과 비밀번호 유지 |
| new_password가 8자 미만 또는 UTF-8 72바이트 초과 | 422, 변경 안 됨 |
| 올바른 본문으로 변경 | 200, 쿠키 삭제, auth_version 증가 |
| 직후 GET /api/users/me | 401 |
| 기존 비밀번호로 로그인 | 401 |
| 새 비밀번호로 로그인 | 200 |
| 새 로그인 후 GET /api/users/me/purchases | 기존 구매내역 유지 |

새 비밀번호는 bcrypt 해시로만 저장합니다. 해시 갱신과 auth_version 증가는 같은 트랜잭션입니다. 다른 기기의 기존 로그인도 다음 인증 요청에서 401로 거부됩니다.

## 6. 회원 탈퇴 — 마지막에 확인

먼저 구매내역에서 paid 주문 ID를 기록해 두세요. 비밀번호를 변경했다면 새 비밀번호로 로그인한 상태에서 진행합니다.

DELETE /api/users/me의 요청 본문:

```json
{"current_password": "ChangedPass456!"}
```

| 확인 순서 | 기대 결과 |
|---|---|
| 잘못된 현재 비밀번호로 먼저 탈퇴 요청 | 400, 탈퇴 안 됨 |
| 올바른 현재 비밀번호로 탈퇴 | 200, 쿠키 삭제 |
| 탈퇴 후 GET /api/users/me 또는 구매내역 | 401 |
| 탈퇴한 이메일/비밀번호로 로그인 | 401 |
| 같은 이메일로 회원가입 | 409 |

Supabase Table Editor에서 **조회만** 하여 다음 항목을 확인하세요.

- ch2.users: 회원 행이 남아 있고 deleted_at에 시각이 저장되며 auth_version이 증가합니다.
- ch2.orders: 기록한 주문 ID가 유지됩니다.
- ch2.order_items: 해당 주문의 상품 행이 유지됩니다.
- ch2.payments: 해당 주문의 결제 결과가 유지됩니다.

탈퇴는 개인정보 익명화나 회원 복구 기능을 포함하지 않습니다. 기존 회원정보와 주문 스냅샷을 유지하며 계정을 비활성화합니다. 탈퇴 후에는 본인 구매내역 API로 조회할 수 없습니다.

## 7. 요청 흐름과 동시성

- 회원정보: JWT 인증 → DB 회원 잠금 및 인증 버전 재확인 → 조회/선택 필드 수정 → 안전한 회원정보 응답.
- 비밀번호 변경/탈퇴: 현재 비밀번호 bcrypt 검증 → DB 회원 잠금 → 검증한 해시와 인증 버전 재확인 → 변경 및 버전 증가 → 쿠키 삭제.
- 구매내역: JWT 인증 → DB 회원 잠금 및 상태 확인 → 본인 paid 주문만 조회 → 페이지/상세 응답.
- 탈퇴·비밀번호 변경·결제는 같은 회원 행을 먼저 잠급니다. 먼저 완료한 트랜잭션 이후에 인증 버전을 재확인하여 무효화된 요청의 후속 처리를 막도록 작성했습니다.

400은 현재 비밀번호 불일치, 401은 로그인 필요/인증 만료, 404는 구매내역 없음, 422는 잘못된 입력, 503은 DB 연결/함수/권한 설정 문제입니다. 위 흐름은 정적 설계 설명이며 실행 검증 결과는 아닙니다.

## 8. 가정 및 피드백

가정: 이메일은 로그인 식별자로 유지하며 이름·연락처·주소만 수정합니다.

가정: 비밀번호 변경과 탈퇴 모두 현재 비밀번호를 다시 입력합니다.

가정: 비밀번호 변경 후 모든 기기의 기존 로그인을 무효화하고 재로그인합니다.

가정: 구매내역에는 paid 주문만 포함하며 pending 주문은 기존 주문 상세 API에서 확인합니다.

가정: soft delete는 데이터 보존과 로그인 차단으로 처리하며 별도 회원 복구 기능은 없습니다.

오류가 있으면 API 경로, HTTP 상태, 응답 detail 또는 SQL Editor 오류를 알려주세요. 비밀번호·비밀키·쿠키·JWT·password_hash는 보내지 마세요.
