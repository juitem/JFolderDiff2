/**
 * 전역 상태 관리 (단방향 데이터 흐름)
 *
 *  store.update(partial) → 구독자 콜백 호출 → 컴포넌트 re-render
 */

const _state = {
  leftPath:       localStorage.getItem('leftPath')  || '',
  rightPath:      localStorage.getItem('rightPath') || '',
  compareResult:  null,     // API /compare 응답
  currentView:    'folder', // 'folder' | 'file'
  currentFile:    null,     // FolderEntryDTO
  fileDiff:       null,     // API /diff 응답
  mergeDecisions: {},       // { chunkIdx(str): 'left' | 'right' }
  filterDiffOnly: false,
  expandedDirs:   new Set(),
  loading:        false,
  selectedRow:    -1,       // 폴더 뷰 선택된 행 인덱스
  currentChunk:   0,        // 파일 diff 현재 청크 인덱스 (change_chunks 내)
};

const _listeners = [];

export const store = {
  get state() { return _state; },

  update(partial) {
    Object.assign(_state, partial);

    // 경로 변경 시 localStorage 저장
    if ('leftPath'  in partial) localStorage.setItem('leftPath',  _state.leftPath);
    if ('rightPath' in partial) localStorage.setItem('rightPath', _state.rightPath);

    _listeners.forEach(fn => fn(_state));
  },

  subscribe(fn) {
    _listeners.push(fn);
    return () => {
      const idx = _listeners.indexOf(fn);
      if (idx !== -1) _listeners.splice(idx, 1);
    };
  },

  /** 변경된 청크 인덱스 목록 */
  get changeChunks() {
    if (!_state.fileDiff) return [];
    return _state.fileDiff.chunks
      .filter(c => c.tag !== 'equal')
      .map(c => c.index);
  },

  /** 현재 포커스된 변경 청크의 실제 chunk index */
  get currentChunkIdx() {
    const cc = this.changeChunks;
    if (!cc.length) return -1;
    return cc[Math.min(_state.currentChunk, cc.length - 1)];
  },
};
