import { api, dateTime, emptyState, initChrome, money, node, orderLines, shippingInfo, showError } from './common.js';

initChrome('account');
const notice = document.querySelector('#page-message');
const list = document.querySelector('#purchase-list');
const rawPage = Number(new URLSearchParams(location.search).get('page') || 1);
const page = Number.isInteger(rawPage) && rawPage > 0 && rawPage <= 1000000 ? rawPage : 1;
const limit = 10;

function purchaseCard(order) {
  const card = node('article', 'panel purchase');
  const heading = node('div', 'row');
  const left = node('div');
  left.append(node('span', 'badge', '결제 완료'), node('p', 'hint', dateTime(order.paid_at)));
  heading.append(left, node('strong', '', money(order.total_amount)));
  const preview = order.items[0]?.product_name || '주문 상품';
  card.append(heading, node('h2', '', order.items.length > 1 ? `${preview} 외 ${order.items.length - 1}종` : preview), node('span', 'purchase-id', `주문번호 ${order.id}`));
  const details = node('details');
  const summary = node('summary', '', '주문 상세 보기');
  const body = node('div');
  let loaded = false;
  let loading = false;
  details.append(summary, body);
  details.addEventListener('toggle', async () => {
    if (!details.open || loaded || loading) return;
    loading = true;
    body.replaceChildren(node('p', 'loading', '상세를 불러오는 중입니다.'));
    body.setAttribute('aria-busy', 'true');
    try {
      const detail = await api(`/api/users/me/purchases/${encodeURIComponent(order.id)}`);
      body.replaceChildren(orderLines(detail), node('h3', '', '주문 당시 배송지'), shippingInfo(detail));
      loaded = true;
    } catch (error) {
      body.replaceChildren(node('p', 'muted', '상세를 불러오지 못했습니다. 닫았다가 다시 열어주세요.'));
      showError(notice, error);
    } finally { loading = false; body.removeAttribute('aria-busy'); }
  });
  card.append(details);
  return card;
}

async function load() {
  try {
    const result = await api(`/api/users/me/purchases?offset=${(page - 1) * limit}&limit=${limit}`);
    document.querySelector('#purchase-count').textContent = `총 ${result.total}건`;
    list.replaceChildren();
    if (!result.items.length) {
      if (result.total) emptyState(list, '이 페이지에 주문이 없습니다.', '첫 페이지에서 구매내역을 확인하세요.', '/purchases', '첫 페이지로');
      else emptyState(list, '아직 구매내역이 없습니다.', '결제를 완료하면 이곳에서 확인할 수 있습니다.');
    } else result.items.forEach((order) => list.append(purchaseCard(order)));
    document.querySelector('#purchase-pager').hidden = result.total <= limit && page === 1;
    document.querySelector('#page-number').textContent = `${page} / ${Math.max(1, Math.ceil(result.total / limit))}`;
    document.querySelector('#previous-page').disabled = page === 1;
    document.querySelector('#next-page').disabled = page * limit >= result.total;
    document.querySelector('#previous-page').onclick = () => location.assign(`/purchases?page=${page - 1}`);
    document.querySelector('#next-page').onclick = () => location.assign(`/purchases?page=${page + 1}`);
  } catch (error) { list.replaceChildren(); showError(notice, error); }
  finally { list.removeAttribute('aria-busy'); }
}
load();
