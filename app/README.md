# AI-Marine Shop — STEP 5

Python/FastAPI/Uvicorn과 Supabase PostgreSQL의 `ch2` 스키마를 사용합니다. 인증·상품·장바구니·주문·모의 결제·회원정보·구매내역 API와 HTML/CSS/Vanilla JS 화면을 작성했습니다. 인증 화면 자동 이동/next 복귀와 배포 설정은 이후 단계에서 연결합니다. 코드·SQL·서버·테스트를 작성자가 직접 실행하지 않았습니다.

**STEP 3 적용:** 기존 DB에는 `sql/step3_functions.sql`만 추가 실행하세요. CMD 명령과 순서별 요청 본문은 [STEP 3 확인 절차](docs/step3-checklist.md)에 있습니다. 새 DB는 schema.sql → seed.sql → step3_functions.sql 순서입니다.

**STEP 4 적용:** STEP 3까지 적용한 DB에는 `sql/step4_functions.sql`만 추가 실행하세요. 테이블 생성용 schema.sql을 다시 실행하지 않습니다. [STEP 4 확인 절차](docs/step4-checklist.md)에 회원정보·구매내역·비밀번호 변경·탈퇴의 Swagger 요청 예시가 있습니다. 새 DB의 전체 적용 순서는 schema.sql → seed.sql → step3_functions.sql → step4_functions.sql입니다.

**STEP 5 화면:** 추가 SQL이나 설치 작업 없이 서버를 재시작하고 `http://127.0.0.1:8000`을 여세요. [화면 확인 절차](docs/step5-checklist.md)에 주소, 클릭 순서, 360px/768px/1200px 수동 체크리스트가 있습니다. 비로그인 화면 이동과 next 복귀는 STEP 6에서 연결합니다.

**브랜드:** AI-Marine Shop. 초록·파랑의 색상, 공통 헤더/푸터, 화면 제목을 적용했습니다. Render 콘솔에 입력할 환경변수와 서비스 설정은 [Render 배포 값 준비](docs/render-environment.md), 예시 값은 `.env.render.example`을 참고하세요. 실제 키는 Render Environment에만 입력하며 로컬 .env를 운영 예시로 덮어쓰지 않습니다.

## 폴더 구성

```text
project/
├─ app/
│  ├─ main.py
│  ├─ core/       # 환경 설정, 비밀번호 해시, JWT
│  ├─ db/         # 서버 전용 Supabase REST 연결
│  ├─ routers/    # 인증·상품·장바구니·주문·결제·회원정보·구매내역 HTTP API
│  ├─ schemas/    # 요청 검증 및 응답 모델
│  └─ services/   # 인증·상품 조회 및 장바구니/주문/결제/회원정보 RPC 호출
├─ static/css/   # 모바일 우선 공통 스타일
├─ static/js/    # 공통 fetch/DOM 유틸리티와 화면별 ES 모듈
├─ templates/    # FastAPI가 제공하는 HTML 화면 8개
├─ sql/
├─ docs/
├─ requirements.txt
├─ .env.example
└─ README.md
```

## 1. Supabase 준비

1. STEP 1의 `sql/schema.sql`과 `sql/seed.sql`을 순서대로 SQL Editor에서 실행합니다. 이미 생성했다면 스키마를 다시 실행하지 않습니다.
2. Supabase 프로젝트의 Data API 설정에서 Exposed schemas 목록에 **ch2를 추가**하고 저장합니다. 기존 노출 스키마는 제거할 필요가 없습니다. 설정 항목은 프로젝트 설정의 API/Data API 영역에서 찾을 수 있습니다.
3. `schema.sql`에 있는 `GRANT USAGE ON SCHEMA ch2 TO service_role` 및 테이블 권한 구문이 적용되어 있어야 합니다.
4. 프로젝트 URL과 서버 전용 **service_role 키**를 준비합니다. anon/publishable 키를 사용하지 않습니다. 이 구현은 `Authorization: Bearer`에도 같은 키를 사용하므로 legacy service_role JWT 키를 사용합니다.

스키마를 API에 노출해도 anon/authenticated 역할에는 테이블 권한이나 RLS 정책을 부여하지 않았으므로 직접 조회할 수 없습니다. 서버의 service_role은 RLS를 우회하므로 FastAPI가 인증과 소유권을 검사합니다. 브라우저에는 키를 전달하지 않습니다.

## 2. CMD 로컬 실행

VS Code에서 터미널 종류를 **Command Prompt(CMD)**로 선택하세요. Python 3.11 이상과 Windows Python Launcher(`py`)가 설치되어 있다고 가정합니다.

```cmd
cd /d C:\AIO4\Day12_demo\project
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
copy .env.example .env
```

`.env`가 이미 있다면 복사 명령을 생략하여 기존 설정을 보존하세요. 파일을 열어 다음 값을 수정합니다.

```cmd
notepad .env
```

| 변수 | 설정 |
|---|---|
| SUPABASE_URL | 본인 프로젝트 URL |
| SUPABASE_KEY | 서버 전용 service_role JWT 키 |
| SUPABASE_SCHEMA | ch2 |
| SECRET_KEY | 아래 명령으로 생성한 무작위 문자열 |
| APP_ORIGIN | http://127.0.0.1:8000 |
| COOKIE_SECURE | 로컬 HTTP는 false, 운영 HTTPS는 true |
| ACCESS_TOKEN_EXPIRE_MINUTES | 기본 60분 |

비밀키 생성 명령입니다. 출력값을 `.env`의 SECRET_KEY에 넣습니다. 키를 공유하거나 Git에 커밋하지 마세요.

```cmd
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

설정 저장 후 실행합니다.

```cmd
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

브라우저에서 **http://127.0.0.1:8000/docs**를 여세요. `localhost`로 바꾸면 APP_ORIGIN과 달라 변경 요청이 403이 될 수 있습니다. 설정을 바꾼 경우 서버를 재시작합니다. 종료는 CMD에서 `Ctrl+C`입니다.

## 3. Swagger 확인 순서

각 API의 Try it out → JSON 입력 → Execute 순서로 확인합니다.

### 회원가입

`POST /api/auth/signup`

```json
{
  "email": "demo@example.com",
  "password": "DemoPass123!",
  "name": "홍길동",
  "phone": "010-1234-5678",
  "address": "서울시 강남구 예시로 10"
}
```

기대 결과: **201**, 회원 ID·이메일·이름·연락처·주소·생성 시각. 비밀번호 해시는 응답에 없습니다. 가입은 자동 로그인을 하지 않습니다.

동일 이메일로 다시 가입하면 **409**입니다. 비밀번호가 8자 미만이거나 UTF-8 기준 72바이트를 넘으면 **422**입니다. 한글은 보통 글자당 3바이트이므로 바이트 제한도 함께 확인합니다.

### 로그인

`POST /api/auth/login`

```json
{
  "email": "demo@example.com",
  "password": "DemoPass123!"
}
```

기대 결과: **200**, 로그인 메시지와 회원정보. 브라우저가 `shop_access_token` 쿠키를 자동 저장하며 Swagger의 Authorize 버튼에 토큰을 넣을 필요가 없습니다. 토큰은 JSON 응답에 반환하지 않습니다. 잘못된 비밀번호는 **401**입니다.

### 로그아웃

로그인한 동일 브라우저에서 `POST /api/auth/logout`을 실행합니다. 요청 본문은 없습니다.

기대 결과: **200**, 로그아웃 메시지. 쿠키가 삭제되고 회원의 auth_version이 증가합니다. 다시 로그아웃하면 인증 쿠키가 없으므로 **401**입니다. 다른 기기의 기존 쿠키도 다음 인증 요청에서 거부됩니다.

### DB 확인

Supabase Table Editor에서 `ch2.users`를 확인하세요. 가입 행에 bcrypt 형식의 password_hash가 저장되고 원문 비밀번호가 없어야 합니다. 로그아웃 후 auth_version은 최초 1에서 2로 증가합니다. 추가 로그아웃을 수행한 경우 더 큰 값일 수 있습니다.

## 요청 → 처리 → 응답

- 가입: Pydantic 검증 → bcrypt 해시 → Supabase ch2.users INSERT → 201 회원정보.
- 로그인: 이메일 조회 → 비밀번호와 탈퇴 여부 확인 → 만료 있는 JWT 생성 → 200 및 HttpOnly 쿠키.
- 로그아웃: 쿠키 JWT 검증 → DB 인증 버전/탈퇴 확인 → 버전 증가 → 쿠키 삭제 및 200.
- 검증 실패는 422, 인증 실패는 401, 중복 이메일은 409, 요청 출처 위반은 403, DB 연결/설정 문제는 503으로 응답합니다.

## 보안 및 현재 범위

- 쿠키는 HttpOnly, SameSite=Lax이며 운영 환경에서는 Secure를 켭니다.
- 변경 요청의 Origin을 APP_ORIGIN과 비교합니다. 쿠키가 포함된 변경 요청에는 Origin이 필수이므로 별도 HTTP 클라이언트로 호출할 때도 같은 Origin 헤더를 넣어야 합니다. Swagger는 브라우저가 자동으로 보냅니다.
- SQL 문자열을 조합하지 않고 고정 테이블·컬럼과 PostgREST 쿼리 매개변수를 사용합니다.
- 검증 오류 응답에서 입력 원문을 제거하여 비밀번호 노출을 방지합니다.
- 회원정보·비밀번호 변경·탈퇴·구매내역은 STEP 4 API와 STEP 5 화면으로 제공합니다. 인증 실패 시 API는 401을 반환하고 현재 화면에는 로그인 링크를 표시합니다. 자동 화면 이동 및 내부 next 경로 검증은 STEP 6에서 연결합니다.
- 장바구니/주문/결제는 `sql/step3_functions.sql`의 RPC 함수로 처리합니다. 성공 기록·재고 차감·paid 전환이 단일 트랜잭션이며 실패 결과도 기록합니다. REST 요청 여러 개를 트랜잭션처럼 취급하지 않습니다.

## 문제를 알려주실 때

요청 API 경로, HTTP 상태코드, 응답의 detail, CMD 오류 메시지를 알려주세요. `.env`, Supabase 키, 비밀번호, 쿠키/JWT 값은 보내지 마세요.

- 403: 주소가 APP_ORIGIN과 같은지, 쿠키 요청에 Origin 헤더가 있는지 확인합니다.
- 503: URL/키, ch2의 Exposed schemas 등록, 스키마와 테이블 권한을 확인합니다. 설정이 맞는데도 실패하면 응답과 서버 오류를 바탕으로 원인을 확인합니다.
- 서버 시작 시 설정 오류: `.env` 위치와 필수 값, SECRET_KEY의 길이 및 예제값 교체 여부를 확인합니다.

가정: 회원가입 직후에는 자동 로그인하지 않고 별도 로그인 API를 호출합니다.

가정: 로그인 유효시간은 60분이며 자동 갱신 기능은 추가하지 않습니다.

가정: Windows CMD 및 Python 3.11 이상을 사용하며, 로컬 주소는 127.0.0.1:8000으로 통일합니다.

가정: 서버 전용 Supabase legacy service_role JWT 키와 Data API로 DB에 접근합니다.
