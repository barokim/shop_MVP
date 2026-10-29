import { api, initChrome, message, perform, validatePassword } from './common.js';

initChrome('');
const notice = document.querySelector('#page-message');
const notices = {
  registered: '회원가입이 완료되었습니다. 로그인해주세요.',
  'password-changed': '비밀번호가 변경되었습니다. 새 비밀번호로 로그인해주세요.',
  'account-deleted': '회원 탈퇴가 완료되었습니다.',
};
const noticeKey = new URLSearchParams(location.search).get('notice');
const text = Object.hasOwn(notices, noticeKey) ? notices[noticeKey] : null;
if (text) message(notice, text, 'success');

const login = document.querySelector('#login-form');
login?.addEventListener('submit', (event) => {
  event.preventDefault();
  const values = new FormData(login);
  perform(login, notice, async () => {
    const password = values.get('password');
    validatePassword(password, 1);
    await api('/api/auth/login', { method: 'POST', body: { email: values.get('email').trim(), password } });
    login.reset();
    // STEP 5는 로그인 후 상품목록으로 이동합니다. next 검증/복귀는 STEP 6 범위입니다.
    location.assign('/products');
  });
});

const signup = document.querySelector('#signup-form');
signup?.addEventListener('submit', (event) => {
  event.preventDefault();
  const values = new FormData(signup);
  perform(signup, notice, async () => {
    const password = values.get('password');
    validatePassword(password);
    if (password !== values.get('password_confirm')) throw new Error('비밀번호 확인이 일치하지 않습니다.');
    const body = { email: values.get('email').trim(), password };
    for (const key of ['name', 'phone', 'address']) {
      body[key] = values.get(key).trim();
      if (!body[key]) throw new Error('이름, 연락처, 주소를 모두 입력해주세요.');
    }
    await api('/api/auth/signup', { method: 'POST', body });
    signup.reset();
    location.assign('/login?notice=registered');
  });
});
