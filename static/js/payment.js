import { api, button, initChrome, isUuid, link, message, money, node, orderLines, perform, shippingInfo, showError } from './common.js';

initChrome('cart');
const notice = document.querySelector('#page-message');
const content = document.querySelector('#payment-content');
const orderId = new URLSearchParams(location.search).get('order_id');
const storageKey = `shop.payment.${orderId}`;
let order;

function readAttempt() {
  // JWT/개인정보는 저장하지 않습니다. 응답 유실 시 중복 결제를 막는 요청 정보만 보존합니다.
  let raw;
  try { raw = sessionStorage.getItem(storageKey); }
  catch { throw new Error('결제 요청을 보존할 수 없습니다. 브라우저의 사이트 저장소 허용 설정을 확인해주세요.'); }
  if (!raw) return null;
  let saved;
  try { saved = JSON.parse(raw); } catch { saved = null; }
  if (!saved || !isUuid(saved.idempotency_key) || !Number.isSafeInteger(saved.amount) || saved.amount <= 0 || typeof saved.simulate_success !== 'boolean') {
    throw new Error('저장된 결제 정보를 읽을 수 없습니다. 구매내역에서 결제 상태를 확인해주세요.');
  }
  return saved;
}

function saveAttempt(attempt) {
  try { sessionStorage.setItem(storageKey, JSON.stringify(attempt)); }
  catch { throw new Error('결제 요청을 보존하지 못해 결제를 시작하지 않았습니다. 사이트 저장소 설정을 확인해주세요.'); }
}

function clearAttempt() {
  try { sessionStorage.removeItem(storageKey); }
  catch { /* 이미 결과를 받은 요청은 남아 있어도 같은 키로만 재전송되므로 중복 결제되지 않습니다. */ }
}

function showOrder() {
  const grid = node('div', 'checkout-grid');
  const information = node('section', 'panel');
  information.append(node('h2', '', '주문 상품'), node('p', 'purchase-id', `주문번호 ${order.id}`), orderLines(order));
  information.append(node('h2', '', '배송지'), shippingInfo(order));
  const summary = node('aside', 'panel summary');
  summary.append(node('h2', '', '결제 금액'));
  const total = node('div', 'summary-line summary-total');
  total.append(node('span', '', '상품 합계'), node('strong', '', money(order.total_amount)));
  summary.append(total);

  if (order.status === 'paid') {
    summary.append(node('p', 'badge', '결제 완료'), link('상품목록으로', '/products', 'button full'), link('구매내역 보기', '/purchases', 'button secondary full'));
  } else {
    const pending = readAttempt();
    const short = order.items.some((item) => item.quantity > item.stock);
    if (short) information.append(node('p', 'message error', '현재 재고가 부족한 상품이 있습니다. 상품목록에서 재고를 확인해주세요.'));
    const form = node('form');
    const choices = node('fieldset');
    choices.append(node('legend', '', '모의 결제 결과'));
    for (const [value, text] of [['success', '성공'], ['failure', '실패']]) {
      const label = node('label', 'check-label');
      const input = node('input');
      Object.assign(input, { type: 'radio', name: 'outcome', value, required: true });
      input.checked = pending ? (value === 'success') === pending.simulate_success : value === 'success';
      input.disabled = Boolean(pending);
      label.append(input, node('span', '', text));
      choices.append(label);
    }
    form.append(choices, node('p', 'hint', '실제 결제나 카드 정보 입력은 없습니다.'));
    if (pending) form.append(node('p', 'hint', '이전 결제의 결과를 확인하지 못했습니다. 같은 결제를 다시 확인해주세요.'));
    const submit = button(pending ? '이전 결제 결과 확인' : `${money(order.total_amount)} 결제하기`, 'button full');
    submit.type = 'submit';
    submit.disabled = !Number.isSafeInteger(order.total_amount) || (!pending && short);
    form.append(submit);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const success = form.querySelector('input[name="outcome"]:checked')?.value === 'success';
      await perform(content, notice, async () => {
        const fresh = await api(`/api/orders/${encodeURIComponent(orderId)}`);
        if (fresh.status === 'paid') {
          clearAttempt();
          location.assign('/products?notice=payment-complete');
          return;
        }
        if (fresh.total_amount !== order.total_amount) throw new Error('주문 금액이 달라졌습니다. 주문·재고 새로고침 후 확인해주세요.');
        let attempt = readAttempt();
        if (!attempt) {
          if (!crypto.randomUUID) throw new Error('이 브라우저에서는 결제를 시작할 수 없습니다. 최신 브라우저를 사용해주세요.');
          attempt = { idempotency_key: crypto.randomUUID(), amount: order.total_amount, simulate_success: success };
          // 요청 전 저장하며, 통신 오류가 나면 지우지 않고 동일 요청으로 재확인합니다.
          saveAttempt(attempt);
        }
        const result = await api(`/api/orders/${encodeURIComponent(orderId)}/payments`, { method: 'POST', body: attempt, paymentResult: true });
        order = result.order;
        clearAttempt();
        if (result.payment.status === 'succeeded' || order.status === 'paid') {
          location.assign('/products?notice=payment-complete');
        } else {
          message(notice, `${result.payment.failure_reason}로 결제하지 못했습니다. 재고를 확인하거나 다시 시도해주세요.`, 'error');
        }
      });
      try { showOrder(); } catch (error) { showError(notice, error); }
    });
    summary.append(form);
    const refresh = button('주문·재고 새로고침', 'text-button');
    refresh.addEventListener('click', async () => {
      await perform(content, notice, async () => {
        order = await api(`/api/orders/${encodeURIComponent(orderId)}`);
        if (order.status === 'paid') clearAttempt();
      });
      try { showOrder(); } catch (error) { showError(notice, error); }
    });
    summary.append(refresh, link('상품목록으로', '/products', 'button secondary full'));
  }
  grid.append(information, summary);
  content.replaceChildren(grid);
}

async function load() {
  try {
    if (!isUuid(orderId)) throw new Error('주문 정보가 없습니다. 장바구니 또는 상품상세에서 주문을 먼저 생성해주세요.');
    order = await api(`/api/orders/${encodeURIComponent(orderId)}`);
    if (order.status === 'paid') clearAttempt();
    showOrder();
  } catch (error) {
    content.replaceChildren(link('장바구니로 이동', '/cart', 'button secondary'));
    showError(notice, error);
  } finally { content.removeAttribute('aria-busy'); }
}
load();
