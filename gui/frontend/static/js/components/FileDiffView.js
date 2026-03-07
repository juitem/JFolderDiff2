/**
 * 파일 diff / 머지 뷰
 * 사이드-바이-사이드 diff 표시, 청크별 머지 결정, 저장 기능.
 */

import { store } from '../store.js';
import { api } from '../api.js';
import { notify } from './Notification.js';

let _container = null;

export function initFileDiffView() {
  _container = document.getElementById('file-diff-view');
}

export async function loadFileDiff(entry) {
  store.update({
    currentView:    'file',
    currentFile:    entry,
    fileDiff:       null,
    mergeDecisions: {},
    currentChunk:   0,
  });
  _renderShell(entry, null, true);

  try {
    const diff = await api.diff(entry.left_abs, entry.right_abs);
    store.update({ fileDiff: diff });
    // 초기 expandedDirs: 모두 접기 (폴더뷰로 돌아갈 때 유지)
    _renderShell(entry, diff, false);
  } catch (e) {
    notify(`diff 로드 실패: ${e.message}`, 'error');
    _renderShell(entry, null, false);
  }
}

export function renderFileDiff() {
  const { currentFile, fileDiff } = store.state;
  if (!currentFile) return;
  _renderShell(currentFile, fileDiff, false);
}

// ── 렌더링 ──────────────────────────────────────────────────────────────────

function _renderShell(entry, diff, loading) {
  const changeCount = diff ? diff.change_count : 0;
  const hasDecisions = Object.keys(store.state.mergeDecisions).length > 0;

  _container.innerHTML = `
    <div class="diff-header">
      <button class="btn-back" id="btn-diff-back">← 뒤로</button>
      <span class="diff-filename">${_esc(entry.name)}</span>
      ${changeCount > 0
        ? `<span class="diff-counter">${_currentChangeNum()}/${changeCount} diff</span>`
        : '<span class="text-dim" style="font-size:12px">동일한 파일</span>'
      }
      ${hasDecisions ? '<span class="modified-badge">● 미저장</span>' : ''}
      <span class="diff-header-spacer"></span>
      <button class="btn-save" id="btn-diff-save" ${!hasDecisions ? 'disabled' : ''}>저장</button>
    </div>
    <div class="merge-bar">
      <button class="btn-merge accept-all-l" id="btn-all-left">«전체 왼쪽 채택</button>
      <button class="btn-merge" id="btn-prev-chunk">이전</button>
      <button class="btn-merge" id="btn-next-chunk">다음</button>
      <button class="btn-merge accept-all-r" id="btn-all-right">전체 오른쪽 채택»</button>
      <span class="merge-bar-spacer"></span>
      ${diff?.left_path  ? `<span class="text-dim" style="font-size:11px;overflow:hidden;text-overflow:ellipsis;max-width:200px" title="${_esc(diff.left_path)}">${_esc(_shortPath(diff.left_path))}</span>` : ''}
      ${diff?.right_path ? `<span class="text-dim" style="font-size:11px;overflow:hidden;text-overflow:ellipsis;max-width:200px" title="${_esc(diff.right_path)}">← ${_esc(_shortPath(diff.right_path))}</span>` : ''}
    </div>
    <div class="diff-scroll" id="diff-scroll">
      ${loading
        ? `<div class="loading-overlay"><div class="spinner"></div><span>로딩 중…</span></div>`
        : diff
          ? (diff.error
              ? `<div class="empty-state"><div class="icon">⚠️</div><div>${_esc(diff.error)}</div></div>`
              : _diffTableHtml(diff))
          : `<div class="empty-state"><div class="icon">📄</div><div>파일을 불러오는 중…</div></div>`
      }
    </div>`;

  // 이벤트 바인딩
  document.getElementById('btn-diff-back').onclick   = _goBack;
  document.getElementById('btn-diff-save').onclick   = _save;
  document.getElementById('btn-prev-chunk').onclick  = () => _moveChunk(-1);
  document.getElementById('btn-next-chunk').onclick  = () => _moveChunk(1);
  document.getElementById('btn-all-left').onclick    = () => _acceptAll('left');
  document.getElementById('btn-all-right').onclick   = () => _acceptAll('right');

  if (diff && !diff.error) {
    _container.querySelector('#diff-scroll').addEventListener('click', e => {
      const ind = e.target.closest('.diff-indicator');
      if (!ind) return;
      const chunkIdx = parseInt(ind.dataset.chunk, 10);
      const dir = ind.dataset.dir;
      _acceptChunk(chunkIdx, dir);
    });

    // 현재 청크로 스크롤
    setTimeout(() => _scrollToCurrentChunk(), 50);
  }
}

function _diffTableHtml(diff) {
  if (!diff.aligned.length) return `<div class="empty-state"><div class="icon">✅</div><div>동일한 파일입니다</div></div>`;

  const currentChunkIdx = store.currentChunkIdx;
  const decisions = store.state.mergeDecisions;

  const rows = diff.aligned.map(row => {
    const isChange  = row.tag !== 'equal';
    const isCurrent = isChange && row.chunk_idx === currentChunkIdx;
    const decision  = decisions[String(row.chunk_idx)];

    let rowCls = `chunk-${row.tag}`;
    if (isCurrent) rowCls += ' chunk-current';
    if (decision === 'left')  rowCls += ' chunk-decided-left';
    if (decision === 'right') rowCls += ' chunk-decided-right';

    const lNo = row.left_lineno  != null ? row.left_lineno  : '';
    const rNo = row.right_lineno != null ? row.right_lineno : '';

    // 인디케이터 (변경 청크에만)
    const lInd = isChange && !decision
      ? `<span class="diff-indicator" data-chunk="${row.chunk_idx}" data-dir="left" title="왼쪽 채택 →">→</span>`
      : (decision === 'left' ? '<span style="color:var(--green);font-size:10px">✓</span>' : '');
    const rInd = isChange && !decision
      ? `<span class="diff-indicator" data-chunk="${row.chunk_idx}" data-dir="right" title="오른쪽 채택 ←">←</span>`
      : (decision === 'right' ? '<span style="color:var(--blue);font-size:10px">✓</span>' : '');

    return `
      <tr class="${rowCls}" data-chunk="${row.chunk_idx}">
        <td class="diff-lineno">${lNo}</td>
        <td class="diff-indicator-cell">${lInd}</td>
        <td class="left-cell">${_esc(row.left_text)}</td>
        <td class="diff-sep"></td>
        <td class="diff-lineno">${rNo}</td>
        <td class="diff-indicator-cell">${rInd}</td>
        <td class="right-cell">${_esc(row.right_text)}</td>
      </tr>`;
  }).join('');

  return `
    <table class="diff-table">
      <colgroup>
        <col style="width:52px">
        <col style="width:18px">
        <col>
        <col style="width:1px">
        <col style="width:52px">
        <col style="width:18px">
        <col>
      </colgroup>
      <tbody>${rows}</tbody>
    </table>`;
}

// ── 액션 ────────────────────────────────────────────────────────────────────

function _goBack() {
  if (Object.keys(store.state.mergeDecisions).length > 0) {
    if (!confirm('저장하지 않은 변경이 있습니다. 돌아가시겠습니까?')) return;
  }
  store.update({ currentView: 'folder', currentFile: null, fileDiff: null, mergeDecisions: {} });
}

function _moveChunk(dir) {
  const cc = store.changeChunks;
  if (!cc.length) return;
  const next = Math.max(0, Math.min(cc.length - 1, store.state.currentChunk + dir));
  store.update({ currentChunk: next });
  renderFileDiff();
  setTimeout(() => _scrollToCurrentChunk(), 30);
}

function _acceptChunk(chunkIdx, direction) {
  const decisions = { ...store.state.mergeDecisions, [String(chunkIdx)]: direction };
  store.update({ mergeDecisions: decisions });
  renderFileDiff();
}

function _acceptAll(direction) {
  const decisions = {};
  store.changeChunks.forEach(idx => { decisions[String(idx)] = direction; });
  store.update({ mergeDecisions: decisions });
  renderFileDiff();
  notify(`전체 ${direction === 'left' ? '왼쪽' : '오른쪽'} 채택됨`, 'info');
}

async function _save() {
  const { currentFile, fileDiff, mergeDecisions } = store.state;
  if (!fileDiff || !Object.keys(mergeDecisions).length) return;

  try {
    const result = await api.merge(fileDiff.left_path, fileDiff.right_path, mergeDecisions);
    notify(result.message, 'success');
    store.update({ mergeDecisions: {} });

    // diff 재계산
    const newDiff = await api.diff(currentFile.left_abs, currentFile.right_abs);
    store.update({ fileDiff: newDiff, currentChunk: 0 });
    renderFileDiff();
  } catch (e) {
    notify(`저장 실패: ${e.message}`, 'error');
  }
}

function _scrollToCurrentChunk() {
  const scroll = document.getElementById('diff-scroll');
  if (!scroll) return;
  const idx = store.currentChunkIdx;
  if (idx < 0) return;
  const row = scroll.querySelector(`tr[data-chunk="${idx}"]`);
  if (row) {
    row.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
}

// ── 키보드 단축키 ────────────────────────────────────────────────────────────

export function handleFileDiffKey(e) {
  if (store.state.currentView !== 'file') return false;

  // Ctrl+S: 저장
  if (e.ctrlKey && e.key === 's') { e.preventDefault(); _save(); return true; }

  switch (e.key) {
    case 'Escape': _goBack(); return true;
    case 'n': case 'j': _moveChunk(1);  return true;
    case 'p': case 'k': _moveChunk(-1); return true;
    case 'ArrowRight': {
      const idx = store.currentChunkIdx;
      if (idx >= 0) _acceptChunk(idx, 'left');
      return true;
    }
    case 'ArrowLeft': {
      const idx = store.currentChunkIdx;
      if (idx >= 0) _acceptChunk(idx, 'right');
      return true;
    }
    case 'u': {
      const idx = store.currentChunkIdx;
      if (idx >= 0) {
        const decisions = { ...store.state.mergeDecisions };
        delete decisions[String(idx)];
        store.update({ mergeDecisions: decisions });
        renderFileDiff();
      }
      return true;
    }
  }
  return false;
}

// ── 유틸 ────────────────────────────────────────────────────────────────────

function _currentChangeNum() {
  return store.state.currentChunk + 1;
}

function _shortPath(fullPath) {
  const parts = fullPath.split('/');
  return parts.length > 3 ? '…/' + parts.slice(-2).join('/') : fullPath;
}

function _esc(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/ /g, '\u00a0');
}
