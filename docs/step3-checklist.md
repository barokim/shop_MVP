# STEP 3 — 상품·장바구니·주문·모의 결제 확인

사용자가 직접 실행하는 절차입니다. 작성자는 설치, SQL 실행, 서버 실행, 브라우저 조작 및 테스트를 수행하지 않았습니다.

## 적용 순서 — CMD

1. STEP 1/2의 ch2 테이블, .env, 인증 API가 준비되어 있어야 합니다. Supabase Data API의 Exposed schemas에 ch2가 포함되어 있어야 합니다.
2. 아래 CMD 명령으로 **추가 SQL만** 복사하고 Supabase SQL Editor에 붙여넣어 실행합니다.

```cmd
cd /d C:\AIO4\Day12_demo\project
chcp 65001 > nul
clip < "C:\AIO4\Day12_demo\project\sql\step3_functions.sql"
```

기존 DB에서는 schema.sql을 다시 실행하지 않습니다. 새 DB인 경우에만 schema.sql → seed.sql → step3_functions.sql 순서로 실행합니다. 추가 SQL은 데이터를 지우지 않고 요청 옵션 컬럼과 RPC 함수를 등록합니다. 전체가 한 트랜잭션이며 동일 버전은 다시 적용할 수 있습니다.

3. 서버가 실행 중이면 Ctrl+C로 종료한 뒤 다시 실행합니다. 의존성 추가는 없습니다.

```cmd
cd /d C:\AIO4\Day12_demo\project
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

4. http://127.0.0.1:8000/docs 에서 각 API의 Try it out → Execute로 확인합니다. 주소가 APP_ORIGIN과 같아야 합니다.

## API 목록

| 메서드 | 경로 | 인증 | 결과 |
|---|---|---|---|
| GET | /api/products?offset=0&limit=20 | 불필요 | 상품 배열, 200 |
| GET | /api/products/{product_id} | 불필요 | 상품 상세, 200 |
| GET | /api/cart | 필요 | 현재 장바구니, 200 |
| POST | /api/cart/items | 필요 | 추가/동일 상품 수량 합산 후 장바구니, 200 |
| PATCH | /api/cart/items/{product_id} | 필요 | 수량을 입력값으로 교체 후 장바구니, 200 |
| DELETE | /api/cart/items/{product_id} | 필요 | 삭제 후 장바구니, 200 |
| POST | /api/orders/from-cart | 필요 | 지정 cart_id를 주문으로 확정, 200 |
| POST | /api/orders/buy-now | 필요 | 선택 상품의 별도 주문 생성, 201 |
| GET | /api/orders/{order_id} | 필요 | 본인 주문 상세, 200 |
| POST | /api/orders/{order_id}/payments | 필요 | 모의 결제 결과, 200/402/409 |

장바구니 항목 경로에는 **product_id**를 넣습니다. order_items의 id가 아닙니다. 미로그인 API는 401을 반환하며 로그인 화면 이동은 STEP 6에서 연결합니다.

## A. 공개 상품과 인증

| 순서 | 요청 | 기대 결과 |
|---|---|---|
| 1 | 로그아웃 상태에서 GET /api/products | 200, 상품 목록 및 가격·재고 |
| 2 | 재고 있는 상품의 id로 GET /api/products/{product_id} | 200, 선택 상품 상세 |
| 3 | GET /api/cart | 401 |
| 4 | STEP 2의 POST /api/auth/login | 200, 인증 쿠키 자동 저장 |
| 5 | GET /api/cart | 200, 기존 장바구니 또는 items=[] |

신규 회원이면 먼저 가입하세요. 상품 UUID는 목록 응답에서 복사합니다.

## B. 장바구니 CRUD

재고가 2개 이상인 상품을 선택합니다. `상품_UUID`는 실제 값으로 교체합니다.

`POST /api/cart/items`

```json
{"product_id": "상품_UUID", "quantity": 2}
```

| 순서 | 요청 | 기대 결과 |
|---|---|---|
| 1 | 위 본문으로 상품 추가 | 200, quantity=2 (기존 항목이 있으면 합산) |
| 2 | PATCH /api/cart/items/{product_id}, 본문 {"quantity":1} | 200, quantity=1 |
| 3 | GET /api/cart | 수량 1 및 현재 가격으로 계산한 total_amount |
| 4 | DELETE /api/cart/items/{product_id} | 200, 해당 항목 제거 |
| 5 | 같은 상품을 quantity=1로 다시 추가 | 200, 주문 확인용 상품이 담김 |

응답의 id를 **cart_id**로 기록하세요. is_estimate=true인 total_amount는 현재 가격의 예상 합계입니다. DB의 cart 총액은 설계대로 0입니다. 신규 회원의 빈 장바구니는 id=null일 수 있고 상품을 추가하면 ID가 생성됩니다.

수량 0/음수/소수/문자열은 422입니다. 재고를 넘는 추가/변경은 409이며 품절 상품도 담을 수 없습니다. 삭제는 DELETE를 사용합니다.

## C. 장바구니 → 주문

`POST /api/orders/from-cart`

```json
{"cart_id": "앞에서_받은_cart_UUID"}
```

기대 결과는 200, status=pending, is_estimate=false입니다. 응답 id를 **order_id**, total_amount를 **결제 금액**으로 기록하세요. 회원의 이름·연락처·주소 및 현재 상품 단가·상품명을 복사하며 재고는 아직 줄지 않습니다.

같은 cart_id로 다시 요청하면 기존 주문을 반환합니다. 새 주문은 만들지 않습니다. 이후 GET /api/cart는 새 장바구니가 아직 없으면 items=[], id=null을 반환합니다. 다시 상품을 담으면 새 cart ID가 생성됩니다.

GET /api/orders/{order_id}로 주문을 다시 확인할 수 있습니다. 빈 장바구니 주문은 409이며 cart 상태가 유지됩니다.

## D. 모의 실패 → 재시도 → 성공

한 번의 결제 시도마다 새 요청 키를 만듭니다. 아래 CMD를 실행하면 UUID가 출력됩니다.

```cmd
.venv\Scripts\python.exe -c "import uuid; print(uuid.uuid4())"
```

`POST /api/orders/{order_id}/payments`에 아래 본문을 넣습니다. **amount는 반드시 C 단계의 total_amount로 바꾸세요.** 12000은 예시입니다.

```json
{
  "idempotency_key": "생성한_UUID_A",
  "amount": 12000,
  "simulate_success": false
}
```

| 순서 | 요청 | 기대 결과 |
|---|---|---|
| 1 | 위 본문으로 실패 결제 | 402, payment.status=failed, 사유=모의 결제 실패, order.status=pending |
| 2 | 같은 본문 재전송 | 402, replayed=true, 처음 payment.id와 같음 |
| 3 | 키 A는 유지하고 simulate_success만 true로 변경 | 409, 같은 키의 요청 내용 변경 거절 |
| 4 | **새 키 B**로 simulate_success=true | 200, payment.status=succeeded, order.status=paid |
| 5 | 성공한 B 본문 그대로 재전송 | 200, replayed=true, payment.id 동일, 추가 차감 없음 |
| 6 | paid 주문에 **새 키 C**로 결제 | 409, 새 결제 차단 |
| 7 | GET /api/products/{product_id} | 성공 주문 수량만큼 재고 감소 |

실패 결제는 재고를 차감하지 않습니다. 실패 후 새 시도를 하려면 새 키가 필요합니다. 네트워크 오류로 응답을 못 받았다면 **같은 키와 같은 본문**으로 재전송하세요.

기존 실패 키를 다른 결제로 주문이 결제된 뒤 재전송하면 payment에는 당시 실패 결과가, order에는 현재 paid 상태가 표시될 수 있습니다. replayed는 결제 결과의 재사용 여부입니다.

## E. 바로 결제용 주문

장바구니에 상품을 담아 둔 뒤 다른 상품을 아래 요청으로 주문해 보세요.

`POST /api/orders/buy-now`

```json
{"product_id": "선택한_상품_UUID", "quantity": 1}
```

201, 별도 pending 주문이 생성되고 기존 장바구니는 유지됩니다. 반환된 order_id와 total_amount로 D 단계의 결제 API를 호출합니다. 이 API는 결제 화면에서 사용할 주문을 먼저 만듭니다.

바로 주문 요청을 새로 보내면 별도 pending 주문이 생성됩니다. 화면 연결 시 중복 클릭을 막고 응답받은 주문 ID를 결제에 사용합니다. 결제 중복은 위의 요청 키로 방지합니다.

## F. 오류·소유권

| 요청 | 기대 결과 |
|---|---|
| POUCH-001처럼 stock=0인 상품으로 바로 주문 | 409, 주문 생성 안 됨 |
| 수량 0/음수 또는 UUID 형식 오류 | 422 |
| 존재하지 않는 올바른 형식 UUID의 상품 조회 | 404 |
| 장바구니에 없는 상품 변경/삭제 | 404 |
| 주문과 다른 amount로 결제 | 409, 새 결제 기록 없음 |
| 회원 A의 주문을 회원 B로 조회/결제 | 404, 주문 변경 없음 |
| 같은 결제 키를 다른 주문에 재사용 | 409, 두 번째 주문 결제 안 됨 |
| 로그아웃 후 장바구니/주문/결제 요청 | 401 |

회원 B는 별도 브라우저 프로필/시크릿 창에서 가입·로그인하여 확인하세요.

## G. 주문 후 재고 소진 (선택)

샘플 재고를 소진시키는 수동 시나리오입니다. seed.sql을 재실행해도 기존 재고는 복구되지 않습니다.

1. 테스트용 상품의 재고 N(1 이상)을 확인합니다.
2. 회원 A와 B가 각각 **결제 전에** 같은 상품 N개로 바로 주문합니다. 둘 다 pending이며 재고를 예약하지 않습니다.
3. A가 정상 결제하면 stock=0이 됩니다.
4. B가 새 키로 결제하면 409, payment.status=failed, failure_reason=재고 부족, order.status=pending이어야 합니다.
5. B의 요청은 실패 기록만 남기고 재고를 차감하지 않습니다. 동일 키 재전송도 같은 결과를 반환합니다.

동시 결제도 상품 행 잠금 안에서 검증·차감하도록 작성했습니다. 이는 설계 설명이며 부하 테스트 실행 결과는 아닙니다.

## Supabase 확인

- ch2.orders: cart → pending → paid, 배송지 및 확정 금액.
- ch2.order_items: 주문 시점 unit_price/product_name 보존.
- ch2.payments: 실패/성공 기록과 requested_success, 같은 키 중복 없음.
- ch2.products: 성공 시에만 재고 감소, stock >= 0.

503이면 추가 SQL 실행 여부와 ch2 노출 설정부터 확인하세요. SQL 마지막의 NOTIFY는 RPC 캐시를 갱신합니다. 계속 실패하면 API·HTTP 상태·응답 detail 또는 SQL Editor 오류를 전달해주세요. 비밀키·비밀번호·쿠키는 제외합니다.

## 가정

가정: 가격은 원화 정수이며 주문 확정 시점 가격을 결제까지 유지합니다.

가정: 장바구니 수량도 재고를 초과할 수 없으며, 담기와 주문 생성은 재고를 예약하지 않습니다.

가정: 배송지는 회원정보에서 복사하며 별도 배송지 입력 기능을 추가하지 않습니다.

가정: simulate_success로 모의 성공/실패를 선택하며 실제 PG와 통신하지 않습니다.

가정: 재고 부족은 409, 모의 실패는 402이며 모두 실패 기록을 저장하고 pending을 유지합니다.

가정: 주문 생성 실패·인증 실패·금액 불일치 등 결제 전 검증 거절은 결제 시도로 저장하지 않습니다.
