/**
 * 폴더 비교 결과 뷰
 * 트리 형태로 파일 목록과 상태를 표시한다.
 */

import { store } from '../store.js';

const STATUS_ICON  = { same: '=', different: '~', left_only: '←', right_only: '→' };
const STATUS_CLASS = { same: 'badge-same', different: 'badge-diff', left_only: 'badge-left', right_only: 'badge-right' };

let _container   = null;
let _statsBar    = null;
let _onOpenFile  = null;   // (entry) => void
let _flatEntries = [];     // 현재 표시 중인 평탄화 목록

export function initFolderDiffView(onOpenFile) {
  _container  = document.getElementById('folder-diff-view');
  _statsBar   = document.getElementById('statsbar');
  _onOpenFile = onOpenFile;

  store.subscribe(state => {
    if (state.currentView === 'folder') render();
  });
}

export function render() {
  const { compareResult, filterDiffOnly, expandedDirs, loading } = store.state;

  if (loading) {
    _container.innerHTML = `
      <div class="loading-overlay">
        <div class="spinner"></div>
        <span>비교 중…</span>
      </div>`;
    _statsBar.innerHTML = '';
    return;
  }

  if (!compareResult) {
    _container.innerHTML = `
      <div class="empty-state">
        <div class="icon">📂</div>
        <div>두 폴더를 선택하고 <strong>비교</strong> 버튼을 클릭하세요</div>
        <div class="hint">또는 경로를 입력하고 Enter를 누르세요</div>
      </div>`;
    _statsBar.innerHTML = '';
    return;
  }

  _renderStats(compareResult.stats);
  _flatEntries = _flatten(compareResult.entries, expandedDirs);

  if (filterDiffOnly) {
    _flatEntries = _flatEntries.filter(e => e.status !== 'same');
  }

  if (!_flatEntries.length) {
    _container.innerHTML = `
      <div class="empty-state">
        <div class="icon">✅</div>
        <div>두 폴더가 완전히 동일합니다</div>
      </div>`;
    return;
  }

  const tbody = _flatEntries.map((entry, i) => _rowHtml(entry, i)).join('');

  _container.innerHTML = `
    <table class="folder-table">
      <colgroup>
        <col class="col-status">
        <col class="col-name">
        <col class="col-size">
        <col class="col-size">
      </colgroup>
      <thead>
        <tr>
          <th></th>
          <th>이름</th>
          <th style="text-align:right">왼쪽 크기</th>
          <th style="text-align:right">오른쪽 크기</th>
        </tr>
      </thead>
      <tbody>${tbody}</tbody>
    </table>`;

  // 이벤트 위임
  _container.querySelector('tbody').addEventListener('click', e => {
    const row = e.target.closest('tr[data-idx]');
    if (!row) return;
    const idx = parseInt(row.dataset.idx, 10);
    const entry = _flatEntries[idx];
    if (!entry) return;

    if (e.target.closest('.toggle-dir')) {
      _toggleDir(entry);
      return;
    }
    if (entry.is_dir) {
      _toggleDir(entry);
    } else {
      store.update({ selectedRow: idx });
      _onOpenFile(entry);
    }
  });
}

function _rowHtml(entry, i) {
  const icon    = entry.is_dir ? '📁' : '📄';
  const sIcon   = STATUS_ICON[entry.status]  || '?';
  const sCls    = STATUS_CLASS[entry.status] || '';
  const indent  = entry.depth * 18;

  const toggleBtn = entry.is_dir
    ? `<span class="toggle-dir" style="cursor:pointer">
        ${store.state.expandedDirs.has(entry.rel_path) ? '▾' : '▸'}
       </span>`
    : '<span style="width:14px;display:inline-block"></span>';

  const nameHtml = `
    <span class="entry-name" style="padding-left:${indent}px">
      ${toggleBtn}
      <span class="entry-icon">${icon}</span>
      <span>${_esc(entry.name)}</span>
    </span>`;

  const lSize = entry.left_abs  ? '' : '-';
  const rSize = entry.right_abs ? '' : '-';

  return `
    <tr class="status-${entry.status}" data-idx="${i}">
      <td><span class="status-badge ${sCls}">${sIcon}</span></td>
      <td class="col-name">${nameHtml}</td>
      <td class="col-size text-dim">${lSize}</td>
      <td class="col-size text-dim">${rSize}</td>
    </tr>`;
}

function _toggleDir(entry) {
  const expanded = new Set(store.state.expandedDirs);
  if (expanded.has(entry.rel_path)) {
    expanded.delete(entry.rel_path);
  } else {
    expanded.add(entry.rel_path);
  }
  store.update({ expandedDirs: expanded });
  render();
}

function _renderStats(stats) {
  _statsBar.innerHTML = `
    <span class="stat stat-same">
      <span class="stat-dot"></span> 동일 <strong>${stats.same}</strong>
    </span>
    <span class="stat stat-diff">
      <span class="stat-dot"></span> 수정 <strong>${stats.different}</strong>
    </span>
    <span class="stat stat-left">
      <span class="stat-dot"></span> 왼쪽만 <strong>${stats.left_only}</strong>
    </span>
    <span class="stat stat-right">
      <span class="stat-dot"></span> 오른쪽만 <strong>${stats.right_only}</strong>
    </span>
    <span class="stats-spacer"></span>
    <button class="btn-filter ${store.state.filterDiffOnly ? 'active' : ''}"
            id="btn-filter-diff">
      diff만 표시
    </button>`;

  document.getElementById('btn-filter-diff').addEventListener('click', () => {
    store.update({ filterDiffOnly: !store.state.filterDiffOnly });
    render();
  });
}

function _flatten(entries, expanded) {
  const result = [];
  for (const e of entries) {
    result.push(e);
    if (e.is_dir && expanded.has(e.rel_path)) {
      result.push(..._flatten(e.children, expanded));
    }
  }
  return result;
}

function _esc(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
