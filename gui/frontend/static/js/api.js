/**
 * FolderDiff API 클라이언트
 * api-spec.md 의 엔드포인트를 래핑한다.
 */

const BASE = '';  // 같은 오리진 (FastAPI가 정적 파일 서빙)

async function _get(path, params = {}) {
  const url = new URL(BASE + path, location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined) url.searchParams.set(k, v);
  });
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function _post(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  /** 파일시스템 경로 탐색 */
  browse(path) {
    return _get('/api/browse', { path });
  },

  /** 두 폴더 비교 */
  compare(left, right) {
    return _get('/api/compare', { left, right });
  },

  /** 두 파일 diff */
  diff(left, right) {
    return _get('/api/diff', { left, right });
  },

  /** 머지 결정 적용 및 저장 */
  merge(leftPath, rightPath, decisions) {
    return _post('/api/merge', {
      left_path: leftPath,
      right_path: rightPath,
      decisions,
    });
  },
};
