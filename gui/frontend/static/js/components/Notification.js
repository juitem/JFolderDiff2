/**
 * 토스트 알림 컴포넌트
 * 화면 우상단에 자동 소멸하는 알림을 표시한다.
 */

let _container = null;

function _ensure() {
  if (!_container) {
    _container = document.getElementById('notifications');
  }
}

/**
 * @param {string} message
 * @param {'info'|'success'|'error'|'warning'} type
 * @param {number} duration  ms
 */
export function notify(message, type = 'info', duration = 3000) {
  _ensure();

  const icons = { success: '✓', error: '✗', warning: '⚠', info: 'ℹ' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || ''}</span><span>${_esc(message)}</span>`;

  _container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('fade-out');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  }, duration);
}

function _esc(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
