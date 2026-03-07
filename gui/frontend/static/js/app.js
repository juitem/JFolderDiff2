/**
 * FolderDiff GUI — 메인 앱
 * 컴포넌트를 초기화하고, 이벤트를 조율한다.
 */

import { api } from './api.js';
import { store } from './store.js';
import { notify } from './components/Notification.js';
import { initFolderBrowser, openFolderBrowser } from './components/FolderBrowser.js';
import { initFolderDiffView, render as renderFolder } from './components/FolderDiffView.js';
import { initFileDiffView, loadFileDiff, renderFileDiff, handleFileDiffKey } from './components/FileDiffView.js';

// ── 초기화 ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initFolderBrowser();
  initFolderDiffView(openFile);
  initFileDiffView();

  bindPathBar();
  bindViewSwitch();

  // 저장된 경로 복원
  const { leftPath, rightPath } = store.state;
  _setInputVal('input-left',  leftPath);
  _setInputVal('input-right', rightPath);

  // 뷰 상태 구독
  store.subscribe(state => {
    document.getElementById('folder-diff-view').classList.toggle('hidden', state.currentView !== 'folder');
    document.getElementById('file-diff-view').classList.toggle('hidden',   state.currentView !== 'file');
  });
  // 초기 뷰 적용
  document.getElementById('folder-diff-view').classList.remove('hidden');
  document.getElementById('file-diff-view').classList.add('hidden');

  // 전역 키보드 처리
  document.addEventListener('keydown', onGlobalKey);

  // 저장된 경로가 있으면 자동 비교
  if (leftPath && rightPath) compare();
});

// ── 경로 바 ──────────────────────────────────────────────────────────────────

function bindPathBar() {
  // 직접 입력 → Enter
  document.getElementById('input-left').addEventListener('keydown', e => {
    if (e.key === 'Enter') { store.update({ leftPath: e.target.value.trim() }); compare(); }
  });
  document.getElementById('input-right').addEventListener('keydown', e => {
    if (e.key === 'Enter') { store.update({ rightPath: e.target.value.trim() }); compare(); }
  });

  // 폴더 브라우저 버튼
  document.getElementById('btn-browse-left').addEventListener('click', () => {
    openFolderBrowser(store.state.leftPath || '~', path => {
      store.update({ leftPath: path });
      _setInputVal('input-left', path);
    });
  });
  document.getElementById('btn-browse-right').addEventListener('click', () => {
    openFolderBrowser(store.state.rightPath || '~', path => {
      store.update({ rightPath: path });
      _setInputVal('input-right', path);
    });
  });

  // 비교 버튼
  document.getElementById('btn-compare').addEventListener('click', () => {
    store.update({
      leftPath:  document.getElementById('input-left').value.trim(),
      rightPath: document.getElementById('input-right').value.trim(),
    });
    compare();
  });
}

function bindViewSwitch() {
  // 폴더뷰 ↔ 파일뷰 전환은 store 구독으로 처리
}

// ── 비교 ─────────────────────────────────────────────────────────────────────

async function compare() {
  const { leftPath, rightPath } = store.state;
  if (!leftPath || !rightPath) {
    notify('왼쪽과 오른쪽 경로를 모두 입력하세요', 'warning');
    return;
  }

  store.update({ loading: true, currentView: 'folder', compareResult: null });
  renderFolder();

  try {
    const result = await api.compare(leftPath, rightPath);
    // 초기 펼침 상태: 모든 폴더 펼치기
    const expanded = new Set();
    _collectDirs(result.entries, expanded);
    store.update({ compareResult: result, expandedDirs: expanded, loading: false });
    renderFolder();
  } catch (e) {
    store.update({ loading: false });
    notify(`비교 실패: ${e.message}`, 'error');
    renderFolder();
  }
}

function _collectDirs(entries, set) {
  for (const e of entries) {
    if (e.is_dir) {
      set.add(e.rel_path);
      _collectDirs(e.children, set);
    }
  }
}

// ── 파일 열기 ────────────────────────────────────────────────────────────────

async function openFile(entry) {
  await loadFileDiff(entry);
}

// ── 키보드 단축키 ────────────────────────────────────────────────────────────

function onGlobalKey(e) {
  // 입력 필드 포커스 중이면 무시
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

  // 파일 diff 화면 단축키
  if (handleFileDiffKey(e)) return;

  // 폴더 화면 단축키
  if (store.state.currentView === 'folder') {
    if (e.key === 'r') { e.preventDefault(); compare(); }
    if (e.key === 'f') { store.update({ filterDiffOnly: !store.state.filterDiffOnly }); renderFolder(); }
  }
}

// ── 유틸 ─────────────────────────────────────────────────────────────────────

function _setInputVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val || '';
}
