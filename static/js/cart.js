import { api, button, emptyState, initChrome, link, money, node, perform, quantity, showError } from './common.js';

initChrome('cart');
const content = document.querySelector('#cart-content');
const notice = document.querySelector('#page-message');

function render(cart) {
  if (!cart.items.length) {
    emptyState(content, '장바구니가 비어 있습니다.', '마음에 드는 물건을 담아보세요.');
    return;
  }
  const grid = node('div', 'checkout-grid');
  const items = node('section', 'panel');
  items.append(node('h2', '', `담은 상품 ${cart.items.length}종`));
  for (const item of cart.items) {
    const row = node('article', 'cart-item');
    const title = node('div');
    const heading = node('h2');
    heading.append(link(item.product_name, `/products/${encodeURIComponent(item.product_id)}`));
    title.append(heading, node('p', 'hint', `개당 ${money(item.unit_price)} · 현재 재고 ${item.stock}개`));
    if (item.stock < item.quantity) title.append(node('p', 'hint', '재고가 부족합니다. 수량을 줄이거나 상품을 삭제해주세요.'));
    const controls = node('form', 'cart-item-controls');
    const field = node('div', 'field');
    const label = node('label', '', '수량');
    label.htmlFor = `qty-${item.product_id}`;
    const input = node('input');
    Object.assign(input, { id: label.htmlFor, type: 'number', min: '1', max: String(item.stock), step: '1', value: String(item.quantity), required: true });
    input.disabled = item.stock === 0;
    field.append(label, input);
    const save = button('수량 변경', 'button secondary');
    save.type = 'submit';
    save.disabled = item.stock === 0;
    const remove = button('삭제', 'text-button');
    controls.append(field, save, remove);
    row.append(title, node('span', 'cart-price', money(item.line_total)), controls);
    items.append(row);
    controls.addEventListener('submit', (event) => {
      event.preventDefault();
      perform(content, notice, async () => {
        const updated = await api(`/api/cart/items/${encodeURIComponent(item.product_id)}`, { method: 'PATCH', body: { quantity: quantity(input.value, item.stock) } });
        render(updated);
      });
    });
    remove.addEventListener('click', () => perform(content, notice, async () => {
      render(await api(`/api/cart/items/${encodeURIComponent(item.product_id)}`, { method: 'DELETE' }));
    }));
  }
  const summary = node('aside', 'panel summary');
  summary.append(node('h2', '', '주문 예상 금액'));
  const total = node('div', 'summary-line summary-total');
  total.append(node('span', '', '상품 합계'), node('strong', '', money(cart.total_amount)));
  summary.append(total, node('p', 'hint', '현재 상품 가격 기준이며 주문 시 금액이 확정됩니다.'));
  const checkout = button('주문하고 결제하기', 'button full');
  checkout.disabled = cart.items.some((item) => item.stock < item.quantity) || !Number.isSafeInteger(cart.total_amount);
  const refresh = button('가격·재고 새로고침', 'text-button');
  summary.append(checkout, refresh, link('계속 쇼핑', '/products', 'button secondary full'));
  checkout.addEventListener('click', () => perform(content, notice, async () => {
    const order = await api('/api/orders/from-cart', { method: 'POST', body: { cart_id: cart.id } });
    location.assign(`/payment?order_id=${encodeURIComponent(order.id)}`);
  }));
  refresh.addEventListener('click', () => perform(content, notice, async () => render(await api('/api/cart'))));
  grid.append(items, summary);
  content.replaceChildren(grid);
}

async function load() {
  try { render(await api('/api/cart')); }
  catch (error) { content.replaceChildren(); showError(notice, error); }
  finally { content.removeAttribute('aria-busy'); }
}
load();
