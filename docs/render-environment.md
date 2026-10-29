# AI-Marine Shop — Render 배포 값 준비

현재 구현은 FastAPI가 HTML·CSS·Vanilla JS와 API를 함께 제공하는 단일 Python Web Service입니다. 아래는 사용자가 Render 콘솔에 입력할 설정 안내이며 작성자가 설치·빌드·배포하거나 서버를 실행한 결과가 아닙니다. STEP 6의 인증 화면 자동 이동/next 복귀는 아직 연결하지 않았습니다. render.yaml을 포함한 전체 배포 단계는 별도 단계입니다.

## 서비스 설정

| 항목 | 입력 값 |
|---|---|
| Service Type | Web Service |
| Name | ai-marine-shop (예시 이름, 사용 가능 여부는 Render에서 확인) |
| Language / Runtime | Python 3 |
| Root Directory | 저장소에 project 폴더가 있으면 project, 저장소 루트에 app 폴더와 requirements.txt 파일이 있으면 공란 |
| Build Command | pip install -r requirements.txt |
| Start Command | uvicorn app.main:app --host 0.0.0.0 --port $PORT |

Build Command와 Start Command는 **Render 콘솔에 입력**합니다. Windows CMD에서 `$PORT`를 실행하는 명령이 아닙니다. Start Command에는 --reload를 붙이지 않습니다. PORT는 Render의 기본값을 사용하므로 별도로 등록할 필요가 없습니다.

공식 근거: [FastAPI 배포](https://render.com/docs/deploy-fastapi), [PORT 및 기본 환경변수](https://render.com/docs/environment-variables).

## Environment — Key / Value

아래 7개를 Render 서비스의 Environment에 등록합니다. 아래 설명이나 예시 문자열을 그대로 넣지 말고 본인 프로젝트의 실제 값으로 교체하세요. 입력 값 앞뒤에 따옴표를 붙이지 않습니다.

| Key | Value 입력 기준 |
|---|---|
| SUPABASE_URL | 로컬에서 연결에 성공한 프로젝트 기본 URL. https://실제프로젝트식별자.supabase.co 형식이며 /rest/v1, /products, 대시보드 경로를 포함하지 않음 |
| SUPABASE_KEY | 현재 로컬에서 연결에 성공한 동일 프로젝트의 서버 전용 legacy service_role JWT 키. anon/publishable 키와 구분 |
| SUPABASE_SCHEMA | ch2 |
| SECRET_KEY | 운영용으로 별도 생성한 32자 이상의 무작위 문자열. Supabase JWT Secret이나 API 키를 복사하는 항목이 아님 |
| APP_ORIGIN | 사용자가 접속할 실제 HTTPS 주소. 예: https://실제서비스주소.onrender.com. /products 같은 경로는 포함하지 않음 |
| COOKIE_SECURE | true |
| ACCESS_TOKEN_EXPIRE_MINUTES | 60 |

Render에서 표시하는 실제 서비스 URL을 APP_ORIGIN에 넣어야 합니다. ai-marine-shop이라는 서비스 이름이나 도메인을 이미 확보한 것으로 가정하지 않습니다. 도메인이 변경되면 이 값도 변경하여 재배포합니다. 커스텀 도메인을 사용할 때는 그 도메인을 넣고 같은 주소로 접속합니다. 현재 코드는 한 개의 요청 출처를 허용합니다.

운영 예시 파일은 `.env.render.example`입니다. 이 파일은 참고용이며 Render가 자동으로 읽는 설정 파일이 아닙니다. Render Environment에 값을 입력하고 저장/재배포하세요. 로컬 `.env`는 APP_ORIGIN=http://127.0.0.1:8000, COOKIE_SECURE=false를 유지합니다.

### 운영 SECRET_KEY 생성 — 사용자가 CMD에서 실행

```cmd
cd /d C:\AIO4\Day12_demo\project
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

출력 문자열을 Render SECRET_KEY의 Value에 넣습니다. 비밀키는 Git, 화면 HTML/JS, 채팅에 넣지 않습니다. Render 계정 API Key나 실제 PG 키는 이 앱의 실행에 필요하지 않습니다.

## Supabase 준비

- 현재 로컬에서 연결에 성공한 Supabase 프로젝트를 그대로 사용하는 것으로 가정합니다.
- ch2 스키마와 상품 데이터, step3_functions.sql, step4_functions.sql이 이미 적용되어 있어야 합니다.
- Data API Exposed schemas에 ch2를 유지하고 service_role의 스키마/테이블/함수 권한을 유지합니다.
- 배포했다고 기존 schema.sql을 다시 실행하지 않습니다. 새 DB를 사용할 때만 schema.sql → seed.sql → step3_functions.sql → step4_functions.sql 순서로 적용합니다.
- 현재 자체 회원/JWT 인증을 사용하므로 Supabase Auth의 Site URL/Redirect URL을 로그인용으로 변경할 필요는 없습니다.

## 배포를 진행할 때 확인할 항목

- 저장소에 app, static, templates, requirements.txt가 포함되어 있는지 확인합니다.
- .env, .venv와 실제 비밀키가 저장소에 포함되지 않도록 합니다.
- 배포 후 실제 HTTPS URL에서 상품 조회와 로그인/로그아웃을 직접 확인합니다.
- 변경 요청이 403이면 APP_ORIGIN과 브라우저 접속 주소가 정확히 같은지 확인합니다.
- DB 요청이 503이면 Render 로그의 SUPABASE_ERROR 상태·코드를 확인합니다. 실제 키는 공유하지 않습니다.
- HTTPS 운영에서는 COOKIE_SECURE=true, HTTP 로컬에서는 false를 사용합니다.

가정: 프론트엔드와 API는 같은 Render 서비스/도메인에서 제공하며 별도 CORS 설정은 추가하지 않습니다.

가정: 이번 변경은 이름·색상과 배포 값 준비이며, 자동 로그인 화면 이동/next 복귀와 전체 배포 단계는 별도 승인을 받아 진행합니다.
