/**
 * 폴더 브라우저 모달
 * 사용자가 파일시스템을 탐색하여 폴더를 선택할 수 있는 다이얼로그.
 */

import { api } from '../api.js';
import { notify } from './Notification.js';

let _overlay     = null;
let _crumb       = null;
let _list        = null;
let _pathInput   = null;
let _btnSelect   = null;
let _onSelect    = null;   // (path: string) => void
let _currentPath = '';
let _selectedIdx = -1;
let _entries     = [];

export function initFolderBrowser() {
  _overlay   = document.getElementById('modal-overlay');
  _crumb     = document.getElementById('modal-crumb');
  _list      = document.getElementById('modal-list');
  _pathInput = document.getElementById('modal-path-input');
  _btnSelect = document.getElementById('btn-modal-select');

  // 닫기
  _overlay.addEventListener('click', e => {
    if (e.target === _overlay) close();
  });
  document.getElementById('btn-modal-cancel').addEventListener('click', close);
  document.getElementById('btn-modal-home').addEventListener('click', () => navigate('~'));
  document.getElementById('btn-modal-root').addEventListener('click', () => navigate('/'));

  // 경로 직접 입력
  _pathInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') navigate(_pathInput.value.trim());
  });

  // 선택 확인
  _btnSelect.addEventListener('click', _confirmSelect);

  // 모달 내 키보드
  _overlay.addEventListener('keydown', _handleKey);
}

/** 모달 열기 */
export function openFolderBrowser(initialPath, onSelect) {
  _onSelect = onSelect;
  _overlay.classList.add('open');
  _overlay.focus();
  navigate(initialPath || '~');
}

/** 모달 닫기 */
export function close() {
  _overlay.classList.remove('open');
  _onSelect = null;
}

async function navigate(path) {
  try {
    const data = await api.browse(path);
    _currentPath = data.path;
    _entries = data.entries;
    _selectedIdx = -1;
    _pathInput.value = _currentPath;
    _render(data);
  } catch (e) {
    notify(`탐색 실패: ${e.message}`, 'error');
  }
}

function _render(data) {
  _crumb.textContent = _currentPath;
  _crumb.title       = _currentPath;

  _list.innerHTML = '';

  // 상위 폴더 항목
  if (data.parent) {
    const el = _makeEntry('..', '📁 상위 폴더', true, null);
    el.addEventListener('click', () => navigate(data.parent));
    _list.appendChild(el);
  }

  data.entries.forEach((entry, idx) => {
    const icon = entry.is_dir ? '📁' : '📄';
    const sizeStr = entry.is_dir ? '' : _fmtSize(entry.size);
    const el = _makeEntry(entry.name, `${icon} ${entry.name}`, entry.is_dir, sizeStr);

    el.dataset.idx = idx;
    el.addEventListener('click', () => {
      if (entry.is_dir) {
        navigate(entry.path);
      } else {
        _selectIdx(idx);
      }
    });
    el.addEventListener('dblclick', () => {
      if (!entry.is_dir) _confirmSelect();
    });

    _list.appendChild(el);
  });
}

function _makeEntry(name, label, isDir, sizeStr) {
  const el = document.createElement('div');
  el.className = 'modal-entry' + (isDir ? ' is-dir' : '');
  el.innerHTML = `<span>${_esc(label)}</span>
    ${sizeStr ? `<span class="entry-size">${_esc(sizeStr)}</span>` : ''}`;
  return el;
}

function _selectIdx(idx) {
  _selectedIdx = idx;
  const items = _list.querySelectorAll('.modal-entry[data-idx]');
  items.forEach((el, i) => el.classList.toggle('selected', i === idx));
  if (_entries[idx]) _pathInput.value = _entries[idx].path;
}

function _confirmSelect() {
  const path = _pathInput.value.trim();
  if (path && _onSelect) {
    _onSelect(path);
    close();
  }
}

function _handleKey(e) {
  if (e.key === 'Escape') { close(); return; }

  const items = [..._list.querySelectorAll('.modal-entry[data-idx]')];
  if (!items.length) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    _selectIdx(Math.min(_selectedIdx + 1, items.length - 1));
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    _selectIdx(Math.max(_selectedIdx - 1, 0));
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (_selectedIdx >= 0 && _entries[_selectedIdx]) {
      const entry = _entries[_selectedIdx];
      if (entry.is_dir) navigate(entry.path);
      else _confirmSelect();
    } else {
      _confirmSelect();
    }
  }
}

function _fmtSize(bytes) {
  if (bytes === null || bytes === undefined) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

function _esc(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
