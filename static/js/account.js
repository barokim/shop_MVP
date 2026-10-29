import { api, initChrome, message, perform, showError, validatePassword } from './common.js';

initChrome('account');
const content = document.querySelector('#account-content');
const profile = document.querySelector('#profile-form');
const password = document.querySelector('#password-form');
const deletion = document.querySelector('#delete-form');

function fill(member) {
  document.querySelector('#member-name').textContent = member.name;
  document.querySelector('#member-email').textContent = member.email;
  for (const key of ['name', 'phone', 'address']) profile.elements.namedItem(key).value = member[key];
}

profile.addEventListener('submit', (event) => {
  event.preventDefault();
  const values = new FormData(profile);
  const notice = document.querySelector('#profile-message');
  perform(content, notice, async () => {
    const body = {};
    for (const key of ['name', 'phone', 'address']) {
      body[key] = values.get(key).trim();
      if (!body[key]) throw new Error('이름, 연락처, 주소를 모두 입력해주세요.');
    }
    fill(await api('/api/users/me', { method: 'PATCH', body }));
    message(notice, '회원정보가 저장되었습니다. 기존 주문의 배송지는 유지됩니다.', 'success');
  });
});

password.addEventListener('submit', (event) => {
  event.preventDefault();
  const values = new FormData(password);
  perform(content, document.querySelector('#password-message'), async () => {
    const current = values.get('current_password');
    const next = values.get('new_password');
    validatePassword(current, 1);
    validatePassword(next);
    if (next !== values.get('new_password_confirm')) throw new Error('새 비밀번호 확인이 일치하지 않습니다.');
    await api('/api/users/me/password', { method: 'PATCH', body: { current_password: current, new_password: next } });
    password.reset();
    location.assign('/login?notice=password-changed');
  });
});

deletion.addEventListener('submit', (event) => {
  event.preventDefault();
  const values = new FormData(deletion);
  perform(content, document.querySelector('#delete-message'), async () => {
    if (!values.has('confirmed')) throw new Error('탈퇴 안내를 확인해주세요.');
    const current = values.get('current_password');
    validatePassword(current, 1);
    await api('/api/users/me', { method: 'DELETE', body: { current_password: current } });
    deletion.reset();
    location.assign('/login?notice=account-deleted');
  });
});

async function load() {
  try { fill(await api('/api/users/me')); content.hidden = false; }
  catch (error) { showError(document.querySelector('#page-message'), error); }
  finally { document.querySelector('#account-loading').hidden = true; }
}
load();
