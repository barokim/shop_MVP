# 테이블 정의서

`NN`은 NOT NULL입니다. `—`는 지정 없음입니다. 모든 시간은 타임존을 포함하는 `timestamptz`이며 표시는 애플리케이션에서 한국 시간으로 변환합니다. 모든 FK는 삭제 시 RESTRICT를 적용합니다. SQL이 실제 제약의 기준입니다.

## users

| 컬럼 | 자료형 | NN | PK/FK/UNIQUE | 기본값 | 의미·제약 |
|---|---|---|---|---|---|
| id | uuid | O | PK | gen_random_uuid() | 회원 식별자 |
| email | text | O | UNIQUE | — | 소문자·양끝 공백 제거 형태, 기본 이메일 형식, 최대 254자 |
| password_hash | text | O | — | — | bcrypt 해시 |
| name | text | O | — | — | 공백 제외 1~100자 |
| phone | text | O | — | — | 공백 제외 1~30자, 선행 0 보존 |
| address | text | O | — | — | 공백 제외 1~500자 |
| auth_version | integer | O | — | 1 | 양수, 기존 인증 무효화용 |
| deleted_at | timestamptz | X | — | — | NULL: 활성, 값 존재: 탈퇴 |
| created_at | timestamptz | O | — | now() | 생성 시각 |
| updated_at | timestamptz | O | — | now() | UPDATE 트리거로 갱신 |

## products

| 컬럼 | 자료형 | NN | PK/FK/UNIQUE | 기본값 | 의미·제약 |
|---|---|---|---|---|---|
| id | uuid | O | PK | gen_random_uuid() | 상품 식별자 |
| sku | text | O | UNIQUE | — | 샘플 중복 방지 및 상품 구분 코드, 1~50자 |
| name | text | O | — | — | 공백 제외 1~200자 |
| description | text | O | — | 빈 문자열 | 상세 설명 |
| price | bigint | O | — | — | 현재 단가, 원화 정수, 양수 |
| stock | integer | O | — | 0 | 재고, 0 이상 |
| created_at | timestamptz | O | — | now() | 생성 시각 |
| updated_at | timestamptz | O | — | now() | UPDATE 트리거로 갱신 |

## orders

| 컬럼 | 자료형 | NN | PK/FK/UNIQUE | 기본값 | 의미·제약 |
|---|---|---|---|---|---|
| id | uuid | O | PK | gen_random_uuid() | 장바구니/주문 식별자 |
| user_id | uuid | O | FK → users.id | — | 소유 회원 |
| status | text | O | 부분 UNIQUE(user_id) | cart | cart / pending / paid, cart만 회원당 1개 |
| total_amount | bigint | O | — | 0 | 0 이상, cart는 0, 확정 주문은 양수 |
| recipient_name | text | X | — | — | pending/paid에서 필수, 공백 제외 1~100자 |
| recipient_phone | text | X | — | — | pending/paid에서 필수, 공백 제외 1~30자 |
| shipping_address | text | X | — | — | pending/paid에서 필수, 공백 제외 1~500자 |
| ordered_at | timestamptz | X | — | — | cart는 NULL, pending/paid에서 필수 |
| paid_at | timestamptz | X | — | — | paid에서만 필수, 그 외 NULL |
| created_at | timestamptz | O | — | now() | 생성 시각 |
| updated_at | timestamptz | O | — | now() | UPDATE 트리거로 갱신 |

부분 UNIQUE는 status 컬럼 자체의 중복 제한이 아니라 `WHERE status = 'cart'` 조건의 user_id 인덱스입니다.

## order_items

| 컬럼 | 자료형 | NN | PK/FK/UNIQUE | 기본값 | 의미·제약 |
|---|---|---|---|---|---|
| id | uuid | O | PK | gen_random_uuid() | 항목 식별자 |
| order_id | uuid | O | FK → orders.id, 복합 UNIQUE | — | 소속 장바구니/주문 |
| product_id | uuid | O | FK → products.id, 복합 UNIQUE | — | 원상품 |
| quantity | integer | O | — | — | 양수 |
| unit_price | bigint | O | — | — | 양수, 주문 확정 시점 단가 보존 |
| product_name | text | O | — | — | 주문 확정 시점 상품명, 공백 제외 1~200자 |
| created_at | timestamptz | O | — | now() | 생성 시각 |
| updated_at | timestamptz | O | — | now() | UPDATE 트리거로 갱신 |

복합 UNIQUE(order_id, product_id)로 동일 주문에 같은 상품을 중복 행으로 저장하지 않습니다. 상품 개수는 quantity로 변경합니다. 단가와 상품명은 cart에서 임시 저장하고 주문 확정 시 다시 저장한 뒤 고정합니다.

## payments

| 컬럼 | 자료형 | NN | PK/FK/UNIQUE | 기본값 | 의미·제약 |
|---|---|---|---|---|---|
| id | uuid | O | PK | gen_random_uuid() | 모의 결제 결과 식별자 |
| order_id | uuid | O | FK → orders.id, 부분 UNIQUE | — | succeeded일 때 주문당 1개 |
| idempotency_key | uuid | O | UNIQUE | — | 요청 측에서 만든 중복 처리 방지 키 |
| amount | bigint | O | — | — | 결제 시도 금액, 원화 정수, 양수 |
| status | text | O | — | — | succeeded / failed |
| requested_success | boolean | O | — | true | 결제 요청의 모의 성공 옵션, 같은 키로 옵션 변경 방지 |
| failure_reason | text | X | — | — | failed이면 공백 아닌 사유 필수, 성공이면 NULL |
| created_at | timestamptz | O | — | now() | 최종 결과 저장 시각 |

즉시 결과가 결정되는 모의 결제이므로 별도 진행 중 상태나 PG 거래번호는 두지 않습니다. 재시도는 새로운 행으로 기록하며 기존 결과를 덮어쓰지 않습니다.

## 인덱스 및 무결성 범위

- 모든 PK/UNIQUE에는 PostgreSQL이 인덱스를 생성합니다.
- orders(user_id, ordered_at DESC): 장바구니를 제외한 회원별 주문 조회.
- order_items(order_id, product_id) UNIQUE 인덱스: 주문별 항목 조회에도 사용.
- order_items(product_id): 상품 FK 조회 지원.
- payments(order_id, created_at DESC): 주문별 결제 시도 조회.
- 회원별 장바구니 1개 및 주문별 성공 결제 1개는 부분 UNIQUE 인덱스로 강제합니다.
- 여러 테이블을 함께 검증해야 하는 총액 일치·재고 차감·상태 전이는 `sql/step3_functions.sql`의 DB 함수에서 트랜잭션으로 처리합니다.
