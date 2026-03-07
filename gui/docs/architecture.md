# GUI 아키텍처 설계

## 1. 전체 구조

```
gui/
├── backend/                    # FastAPI 백엔드
│   ├── main.py                 # 앱 시작점 + 정적 파일 서빙
│   ├── requirements.txt
│   ├── api/
│   │   ├── browse.py           # 파일시스템 탐색 엔드포인트
│   │   ├── compare.py          # 폴더/파일 비교 엔드포인트
│   │   └── merge.py            # 머지·저장 엔드포인트
│   ├── models/                 # TUI 모델 재사용 (복사)
│   │   ├── diff_engine.py
│   │   ├── folder_diff.py
│   │   └── merge_state.py
│   └── utils/
│       └── file_utils.py
├── frontend/                   # Vanilla JS SPA
│   ├── index.html
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── app.js          # 진입점 + 라우터
│           ├── store.js        # 전역 상태 관리
│           ├── api.js          # HTTP 클라이언트
│           └── components/
│               ├── PathBar.js          # 경로 선택 바
│               ├── FolderBrowser.js    # 파일시스템 탐색 모달
│               ├── FolderDiffView.js   # 폴더 비교 결과 뷰
│               ├── FileDiffView.js     # 파일 diff/머지 뷰
│               └── Notification.js    # 토스트 알림
└── docs/
    ├── requirements.md
    ├── architecture.md  ← 현재 파일
    ├── api-spec.md
    └── agent-roles.md
```

---

## 2. 레이어 다이어그램

```
┌─────────────────────────────────────────────┐
│  Browser (Vanilla JS + ES Modules)          │
│                                             │
│  app.js ──→ store.js ──→ components/        │
│      ↓                                      │
│  api.js  (fetch API)                        │
└───────────────────┬─────────────────────────┘
                    │ HTTP/JSON
┌───────────────────▼─────────────────────────┐
│  FastAPI Backend                            │
│                                             │
│  api/browse.py ──→ pathlib                  │
│  api/compare.py ──→ models/folder_diff.py   │
│                     models/diff_engine.py   │
│  api/merge.py  ──→ models/merge_state.py    │
│                     utils/file_utils.py     │
└─────────────────────────────────────────────┘
```

---

## 3. 화면 구성

### 3.1 폴더 비교 화면

```
┌─ Navbar ───────────────────────────────────────────────────────┐
│  FolderDiff                                              [?]   │
├─ PathBar ──────────────────────────────────────────────────────┤
│  [📁 /path/to/left ▾]      ←→      [📁 /path/to/right ▾] [비교]│
├─ StatsBar ─────────────────────────────────────────────────────┤
│  동일 3  │ 수정 2  │ 왼쪽만 1  │ 오른쪽만 1   [diff만 보기 ☐]  │
├─ FolderDiffView ───────────────────────────────────────────────┤
│  상태  이름                    크기(좌)   크기(우)              │
│  ────  ──────────────────────  ─────────  ─────────            │
│   ~   📁 subdir               -          -                     │
│   ~   📄   nested.txt         120 B      80 B                  │
│   ←   📄 left_only.txt        45 B       -                     │
│   ~   📄 modified.txt         200 B      180 B                 │
│   →   📄 right_only.txt       -          60 B                  │
│   =   📄 same.txt             100 B      100 B                 │
├─ Footer ───────────────────────────────────────────────────────┤
│  Enter: 열기  Tab: 다음 diff  f: 필터  r: 새로고침             │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 파일 diff 화면

```
┌─ Navbar ───────────────────────────────────────────────────────┐
│  ← 뒤로  📄 modified.txt  [2/3 diff]  [저장]  [미저장 ●]      │
├─ MergeBar ─────────────────────────────────────────────────────┤
│  [«전체 왼쪽]  [이전]  [다음]  [전체 오른쪽»]                  │
├─ FileDiffView ─────────────────────────────────────────────────┤
│  [→]  1│ First line         │  1│ First line            [←]   │
│  [→]  2│ Old second line    │  2│ New second line        [←]   │  ← 현재
│       3│ Third line         │  3│ Third line                   │
│  [→]  4│ Deleted line       │                            [←]   │
│       5│ Fifth line         │  4│ Fifth line                   │
├─ Footer ───────────────────────────────────────────────────────┤
│  n: 다음  p: 이전  →: 왼쪽 채택  ←: 오른쪽 채택  Ctrl+S: 저장 │
└────────────────────────────────────────────────────────────────┘
```

### 3.3 폴더 브라우저 모달

```
┌─ 폴더 선택 ────────────────────────────────┐
│  [홈] [/]  현재: /Users/juitem            │
│  ──────────────────────────────────────── │
│  [..] 상위 폴더                           │
│  📁 Desktop                               │
│  📁 Documents                             │
│  📁 Downloads                             │
│  📁 project-v1         ← 하이라이트       │
│  📁 project-v2                            │
│  📄 notes.txt                             │
│  ──────────────────────────────────────── │
│  경로: [/Users/juitem/project-v1        ] │
│                       [취소]  [선택]       │
└────────────────────────────────────────────┘
```

---

## 4. 상태 관리

프레임워크 없이 단순한 `Store` 클래스로 전역 상태를 관리합니다.

```js
// store.js
{
  leftPath: null,         // 선택된 왼쪽 경로
  rightPath: null,        // 선택된 오른쪽 경로
  compareResult: null,    // 폴더 비교 결과
  currentView: 'folder',  // 'folder' | 'file'
  currentFile: null,      // 현재 열린 파일 엔트리
  fileDiff: null,         // 파일 diff 데이터
  mergeDecisions: {},     // { chunkIdx: 'left'|'right' }
  filterDiffOnly: false,  // diff 항목만 표시 여부
  loading: false,
  notification: null,     // { message, type, id }
}
```

상태 변경 흐름:
```
사용자 이벤트
    → 이벤트 핸들러 (app.js)
    → store.update(partial)
    → 구독 컴포넌트가 re-render
```

---

## 5. 컴포넌트 책임

| 컴포넌트 | 책임 |
|----------|------|
| `PathBar` | 왼쪽·오른쪽 경로 표시 및 브라우저 모달 열기 |
| `FolderBrowser` | 파일시스템 탐색 모달, 경로 선택 |
| `FolderDiffView` | 폴더 비교 트리 목록, 통계 바, 필터 |
| `FileDiffView` | 사이드-바이-사이드 diff, 머지 버튼, 키보드 단축키 |
| `Notification` | 토스트 알림 표시·자동 소멸 |

---

## 6. 기술 스택

| 영역 | 선택 | 이유 |
|------|------|------|
| 백엔드 | FastAPI + Uvicorn | 빠른 개발, 자동 API 문서, 비동기 지원 |
| 백엔드 직렬화 | Pydantic v2 | 타입 안전, 자동 검증 |
| 프론트엔드 | Vanilla JS (ES2022+) | 빌드 도구 불필요, 의존성 Zero |
| 스타일 | CSS Custom Properties | 테마 변수 중앙 관리, 라이트 모드 전환 용이 |
| 폰트 | JetBrains Mono (Google Fonts) | 코드 가독성 |
| 아이콘 | Unicode 이모지 | 외부 의존성 없음 |

---

## 7. 보안

- 모든 파일 경로는 `pathlib.Path.resolve()`로 절대 경로 변환
- 경로가 허용 루트 외부를 벗어나면 403 반환 (경로 트래버설 방어)
- 쓰기 작업(머지 저장)은 POST 메서드로만 허용
- CORS는 개발 환경에서만 허용(기본: 같은 오리진만 허용)
