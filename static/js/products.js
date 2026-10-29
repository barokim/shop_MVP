import { api, button, emptyState, initChrome, isUuid, link, message, money, node, perform, productArt, quantity, showError } from './common.js';

initChrome('products');
const notice = document.querySelector('#page-message');

async function loadProducts() {
  const list = document.querySelector('#product-list');
  const rawPage = Number(new URLSearchParams(location.search).get('page') || 1);
  const page = Number.isInteger(rawPage) && rawPage > 0 && rawPage <= 1000000 ? rawPage : 1;
  const limit = 12;
  try {
    // 1개 더 읽어 다음 페이지 유무만 확인합니다. 별도 검색/정렬 기능은 추가하지 않습니다.
    const products = await api(`/api/products?offset=${(page - 1) * limit}&limit=${limit + 1}`);
    const shown = products.slice(0, limit);
    list.replaceChildren();
    document.querySelector('#product-count').textContent = `현재 페이지 ${shown.length}개`;
    if (!shown.length) emptyState(list, '표시할 상품이 없습니다.', '다른 페이지를 확인해주세요.', '/products', '첫 페이지로');
    for (const product of shown) {
      const card = node('article', 'product-card');
      const destination = link('', `/products/${encodeURIComponent(product.id)}`);
      const info = node('div', 'product-info');
      info.append(node('h3', 'product-name', product.name), node('p', 'product-price', money(product.price)));
      info.append(node('span', product.stock ? 'badge' : 'badge sold-out', product.stock ? `재고 ${product.stock}개` : '품절'));
      destination.append(productArt(product), info);
      card.append(destination);
      list.append(card);
    }
    const pager = document.querySelector('#product-pager');
    pager.hidden = page === 1 && products.length <= limit;
    document.querySelector('#page-number').textContent = `${page} 페이지`;
    document.querySelector('#previous-page').disabled = page === 1;
    document.querySelector('#next-page').disabled = products.length <= limit;
    document.querySelector('#previous-page').onclick = () => location.assign(`/products?page=${page - 1}`);
    document.querySelector('#next-page').onclick = () => location.assign(`/products?page=${page + 1}`);
    if (new URLSearchParams(location.search).get('notice') === 'payment-complete') {
      message(notice, '결제가 완료되었습니다. 회원정보의 구매내역에서 주문을 확인할 수 있습니다.', 'success');
    }
  } catch (error) {
    list.replaceChildren();
    showError(notice, error);
  } finally { list.removeAttribute('aria-busy'); }
}

async function loadDetail() {
  const target = document.querySelector('#product-detail');
  try {
    const id = location.pathname.split('/').filter(Boolean).at(-1);
    if (!isUuid(id)) throw new Error('상품 주소가 올바르지 않습니다.');
    const product = await api(`/api/products/${encodeURIComponent(id)}`);
    document.title = `${product.name} | AI-Marine Shop`;
    const grid = node('div', 'detail-grid');
    const info = node('section');
    info.append(node('p', 'eyebrow', 'GREEN & BLUE, EVERYDAY'), node('h1', '', product.name));
    info.append(node('span', product.stock ? 'badge' : 'badge sold-out', product.stock ? `재고 ${product.stock}개` : '품절'));
    info.append(node('p', 'detail-price', money(product.price)), node('p', 'detail-description', product.description));
    const form = node('form');
    const field = node('div', 'field');
    const label = node('label', '', '수량');
    label.htmlFor = 'quantity';
    const input = node('input');
    Object.assign(input, { id: 'quantity', name: 'quantity', type: 'number', min: '1', max: String(product.stock), step: '1', value: '1', required: true });
    field.append(label, input);
    const actions = node('div', 'actions');
    const add = button('장바구니 담기', 'button secondary');
    add.type = 'submit';
    const buy = button('바로 결제');
    const unavailable = product.stock < 1 || !Number.isSafeInteger(product.price);
    input.disabled = add.disabled = buy.disabled = unavailable;
    actions.append(add, buy);
    form.append(field, actions);
    if (unavailable) form.append(node('p', 'hint', product.stock < 1 ? '현재 품절된 상품입니다.' : '이 상품의 금액을 확인할 수 없습니다.'));
    const afterAdd = node('div', 'actions');
    afterAdd.hidden = true;
    afterAdd.append(link('장바구니로 이동', '/cart', 'button'), link('계속 쇼핑', '/products', 'button secondary'));
    info.append(form, afterAdd);
    grid.append(productArt(product), info);
    target.replaceChildren(grid);

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      perform(form, notice, async () => {
        await api('/api/cart/items', { method: 'POST', body: { product_id: product.id, quantity: quantity(input.value, product.stock) } });
        message(notice, '장바구니에 담았습니다.', 'success');
        afterAdd.hidden = false;
      });
    });
    buy.addEventListener('click', () => {
      if (!form.reportValidity()) return;
      perform(form, notice, async () => {
        const order = await api('/api/orders/buy-now', { method: 'POST', body: { product_id: product.id, quantity: quantity(input.value, product.stock) } });
        location.assign(`/payment?order_id=${encodeURIComponent(order.id)}`);
      });
    });
  } catch (error) { target.replaceChildren(); showError(notice, error); }
  finally { target.removeAttribute('aria-busy'); }
}

if (document.body.dataset.page === 'products') loadProducts();
else loadDetail();
