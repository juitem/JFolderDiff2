# 아키텍처 설계

## 디렉터리 구조

```
FolderDiff/
├── main.py                          # CLI 진입점 (인수 파싱, 경로 검증)
├── requirements.txt
├── docs/                            # 문서
├── src/
│   ├── app.py                       # Textual 앱 루트
│   ├── models/
│   │   ├── diff_engine.py           # 줄 단위 diff 계산
│   │   ├── folder_diff.py           # 폴더 트리 비교
│   │   └── merge_state.py           # 머지 결정 상태 관리
│   ├── utils/
│   │   └── file_utils.py            # 파일 I/O, 인코딩, 바이너리 감지
│   ├── widgets/
│   │   └── diff_view_widget.py      # 사이드-바이-사이드 diff 위젯
│   └── screens/
│       ├── folder_screen.py         # 폴더 비교 화면
│       └── file_screen.py           # 파일 diff/머지 화면
└── tests/
    ├── conftest.py
    ├── fixtures/                    # 테스트용 샘플 파일
    ├── test_diff_engine.py
    ├── test_folder_diff.py
    ├── test_merge_state.py
    └── test_file_utils.py
```

## 레이어 구성

```
[main.py]  ─→  [FolderDiffApp]
                     │
              ┌──────┴──────┐
              ▼             ▼
       [FolderScreen]  [FileScreen]
              │             │
              │      [DiffViewWidget]
              │             │
         [models]      [models]
    folder_diff.py   diff_engine.py
                     merge_state.py
                          │
                     [file_utils.py]
```

## 핵심 모듈

### `diff_engine.py`

- `compute_diff(left, right)` — `difflib.SequenceMatcher`로 청크 목록 생성
- `build_aligned_lines(chunks)` — 사이드-바이-사이드 표시용 정렬 행 생성
  - `replace` 청크: `max(left_lines, right_lines)` 행으로 패딩
  - `delete` 청크: 오른쪽 `lineno = None`, 텍스트 = `""`
  - `insert` 청크: 왼쪽 `lineno = None`, 텍스트 = `""`
- `get_change_chunks(chunks)` — 변경 청크 인덱스 목록 반환

### `folder_diff.py`

- `compare_folders(left, right)` — 두 폴더를 재귀적으로 비교
- 각 항목의 `status`: `same` / `different` / `left_only` / `right_only`
- 디렉터리는 자식이 하나라도 다르면 `different`
- `flatten_entries(entries, expanded)` — 펼침 상태에 따라 트리 평탄화

### `merge_state.py`

- `MergeDecision` enum: `NONE` / `LEFT` / `RIGHT`
- `set(chunk_idx, decision)` — 청크별 결정 저장
- `apply_to_right(chunks)` — LEFT 결정 청크를 왼쪽 내용으로 교체한 오른쪽 파일 내용 생성
- `apply_to_left(chunks)` — RIGHT 결정 청크를 오른쪽 내용으로 교체한 왼쪽 파일 내용 생성

### `diff_view_widget.py`

Textual `Widget` 서브클래스. `render()` 에서 Rich `Group` 반환.

- 가상 스크롤: `scroll_offset` 으로 보이는 행 범위만 렌더링
- 색상 테마: Catppuccin Mocha
  - `delete` 청크: 왼쪽 빨강, 오른쪽 회색 빈칸
  - `insert` 청크: 왼쪽 회색 빈칸, 오른쪽 초록
  - `replace` 청크: 왼쪽 노랑, 오른쪽 청록
  - 현재 청크: 배경 더 밝게
  - 채택 결정: 초록(LEFT) / 파랑(RIGHT) 오버레이
- `StateChanged` 메시지로 화면에 상태 전파

## 화면 전환

```
FolderDiffApp.on_mount()
    └─ push_screen(FolderScreen)

FolderScreen.action_open_file()
    └─ push_screen(FileScreen)

FileScreen.action_back()
    └─ pop_screen()   →  FolderScreen으로 복귀
```

## 메시지 흐름

```
DiffViewWidget
    ├─ StateChanged  →  FileScreen.on_diff_view_widget_state_changed()
    │                       └─ FileInfoBar.update_state()
    ├─ SaveResult    →  FileScreen._notify()
    └─ LoadError     →  FileScreen._notify()
```
