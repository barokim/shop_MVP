export class ApiError extends Error {
  constructor(status, payload, fallback = '요청을 처리하지 못했습니다.') {
    const labels = { email: '이메일', password: '비밀번호', current_password: '현재 비밀번호', new_password: '새 비밀번호', name: '이름', phone: '연락처', address: '주소', quantity: '수량' };
    let detail = payload?.detail;
    if (Array.isArray(detail)) {
      detail = detail.map((item) => `${labels[item.loc?.at(-1)] || '입력값'}: ${item.msg}`).join(' / ');
    }
    super(typeof detail === 'string' ? detail : fallback);
    this.status = status;
    this.payload = payload;
  }
}

export async function api(path, { method = 'GET', body, paymentResult = false } = {}) {
  let response;
  try {
    response = await fetch(path, {
      method, credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  } catch {
    throw new ApiError(0, null, '서버에 연결하지 못했습니다. 연결 상태를 확인해주세요.');
  }
  let data;
  try { data = await response.json(); }
  catch { throw new ApiError(response.status, null, '서버 응답을 읽지 못했습니다. 다시 시도해주세요.'); }
  // 저장된 모의 실패/재고 부족 결과는 HTTP 오류여도 결제 화면에서 표시합니다.
  if (!response.ok && !(paymentResult && [402, 409].includes(response.status) && data.payment && data.order)) {
    throw new ApiError(response.status, data);
  }
  return data;
}

export function node(tag, className = '', text = null) {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== null) result.textContent = String(text);
  return result;
}

export function link(text, href, className = '') {
  const result = node('a', className, text);
  result.href = href;
  return result;
}

export function button(text, className = 'button') {
  const result = node('button', className, text);
  result.type = 'button';
  return result;
}

export function message(target, text = '', kind = 'info') {
  target.replaceChildren();
  target.hidden = !text;
  target.className = `message ${kind}`;
  if (text) target.append(node('span', '', text));
}

export function showError(target, error) {
  message(target, error.message || '요청을 처리하지 못했습니다.', 'error');
  // 자동 이동과 next 복귀는 STEP 6에서 연결합니다. 현재는 로그인 링크를 안내합니다.
  if (error.status === 401) target.append(link('로그인하기', '/login'));
}

export async function perform(scope, target, action) {
  if (scope.dataset.busy === 'true') return false;
  const controls = scope.matches('button') ? [scope] : [...scope.querySelectorAll('button, input, textarea, select')];
  const disabled = controls.map((control) => control.disabled);
  scope.dataset.busy = 'true';
  scope.setAttribute('aria-busy', 'true');
  controls.forEach((control) => { control.disabled = true; });
  message(target);
  try { await action(); return true; }
  catch (error) { showError(target, error); return false; }
  finally {
    controls.forEach((control, index) => { control.disabled = disabled[index]; });
    scope.dataset.busy = 'false';
    scope.removeAttribute('aria-busy');
  }
}

export function money(value) {
  if (!Number.isSafeInteger(value) || value < 0) return '금액 확인 필요';
  return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', maximumFractionDigits: 0 }).format(value);
}

export function dateTime(value) {
  return new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Seoul' }).format(new Date(value));
}

export function validatePassword(value, minimum = 8) {
  if (Array.from(value).length < minimum || new TextEncoder().encode(value).length > 72) {
    throw new Error(`비밀번호는 ${minimum}자 이상, UTF-8 기준 72바이트 이하여야 합니다.`);
  }
}

export function quantity(value, max) {
  const result = Number(value);
  if (!Number.isInteger(result) || result < 1 || result > Math.min(max, 2147483647)) {
    throw new Error('수량은 현재 재고 이내의 양의 정수로 입력해주세요.');
  }
  return result;
}

export function isUuid(value) {
  return typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

export function emptyState(target, title, text, href = '/products', action = '상품 보러 가기') {
  const panel = node('div', 'empty');
  panel.append(node('h2', '', title), node('p', '', text), link(action, href, 'button secondary'));
  target.replaceChildren(panel);
}

export function productArt(product) {
  const type = { MUG: 'mug', BAG: 'bag', NOTE: 'note', BOTTLE: 'bottle', POUCH: 'pouch' }[product.sku.split('-')[0]] || 'mug';
  const art = node('div', `product-art art-${type}`);
  art.setAttribute('aria-hidden', 'true');
  art.append(node('div', 'art-shape'), node('span', 'sku', product.sku));
  return art;
}

export function orderLines(order) {
  const list = node('ul', 'order-lines');
  order.items.forEach((item) => {
    const row = node('li', 'order-line');
    row.append(node('strong', '', item.product_name), node('small', '', `${money(item.unit_price)} × ${item.quantity}개`), node('span', '', money(item.line_total)));
    list.append(row);
  });
  return list;
}

export function shippingInfo(order) {
  const box = node('div');
  box.append(node('p', '', `${order.recipient_name} · ${order.recipient_phone}`), node('p', 'address muted', order.shipping_address));
  return box;
}

export function initChrome(section) {
  const header = document.querySelector('#site-header');
  const inner = node('div', 'shell header-inner');
  const brand = link('AI-Marine Shop', '/products', 'brand');
  brand.append(node('small', '', 'GREEN & BLUE, EVERYDAY'));
  const desktop = node('nav', 'desktop-nav');
  desktop.setAttribute('aria-label', '주 메뉴');
  const mobile = node('nav', 'mobile-nav');
  mobile.setAttribute('aria-label', '모바일 주 메뉴');
  const entries = [['products', '상품', '/products'], ['cart', '장바구니', '/cart'], ['account', '회원정보', '/account']];
  for (const [key, title, href] of entries) {
    for (const nav of [desktop, mobile]) {
      const item = link(title, href);
      if (key === section) item.setAttribute('aria-current', 'page');
      nav.append(item);
    }
  }
  const actions = node('div', 'header-actions');
  actions.append(link('로그인', '/login', 'text-button'));
  inner.append(brand, desktop, actions);
  header.replaceChildren(inner);
  document.querySelector('#site-navigation').replaceChildren(mobile);
  const footer = document.querySelector('#site-footer');
  footer.className = 'site-footer';
  footer.append(node('div', 'shell', 'AI-Marine Shop · 초록과 파랑이 만나는 일상'));
  // 로그인 토큰은 읽거나 저장하지 않습니다. HttpOnly 쿠키는 브라우저가 전달합니다.
  api('/api/users/me').then(() => {
    const logout = button('로그아웃', 'text-button');
    logout.addEventListener('click', () => perform(logout, document.querySelector('#page-message'), async () => {
      await api('/api/auth/logout', { method: 'POST' });
      location.assign('/products');
    }));
    actions.replaceChildren(logout);
  }).catch(() => { /* 비로그인 상태에서도 공개 상품과 로그인 화면을 사용할 수 있습니다. */ });
}
