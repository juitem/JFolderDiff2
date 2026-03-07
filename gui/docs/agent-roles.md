# 개발 에이전트 역할 분담

이 문서는 병렬 개발을 위한 에이전트 역할 분리 설계입니다.
각 에이전트는 독립적인 책임 범위를 가지며, 인터페이스(API 명세)를 경계로 협력합니다.

---

## 에이전트 구성

### Agent 1 — Backend Engineer

**담당 파일**
```
gui/backend/
├── main.py
├── requirements.txt
├── api/
│   ├── browse.py
│   ├── compare.py
│   └── merge.py
├── models/          (tui/src/models 복사)
└── utils/           (tui/src/utils 복사)
```

**책임**
- FastAPI 앱 설정 (CORS, 정적 파일 서빙, 라우터 등록)
- `GET /api/browse` — 파일시스템 탐색
- `GET /api/compare` — 폴더 비교 (TUI 모델 재사용)
- `GET /api/diff` — 파일 diff (TUI 모델 재사용)
- `POST /api/merge` — 머지 결정 적용 및 저장
- 경로 검증 및 보안 (경로 트래버설 방어)
- Pydantic 응답 모델 정의

**선행 조건**
- `api-spec.md` 의 응답 형식을 반드시 준수
- TUI `src/models/`, `src/utils/` 코드 변경 없이 재사용

**완료 기준**
- `uvicorn backend.main:app` 으로 서버 기동 성공
- `GET /api/browse?path=/` 응답 확인
- `GET /api/compare`, `GET /api/diff`, `POST /api/merge` 동작 확인
- 잘못된 경로 입력 시 400 응답 반환

---

### Agent 2 — Frontend Engineer

**담당 파일**
```
gui/frontend/
├── index.html
└── static/
    ├── css/style.css
    └── js/
        ├── app.js
        ├── store.js
        ├── api.js
        └── components/
            ├── PathBar.js
            ├── FolderBrowser.js
            ├── FolderDiffView.js
            ├── FileDiffView.js
            └── Notification.js
```

**책임**
- 전체 HTML 구조 및 CSS 레이아웃
- Catppuccin Mocha 테마 적용
- `Store` 클래스 구현 (단방향 데이터 흐름)
- `ApiClient` 구현 (`api-spec.md` 기반)
- 5개 컴포넌트 구현
- 키보드 단축키 처리
- History API 기반 뷰 전환
- localStorage 경로 복원

**선행 조건**
- `api-spec.md` 의 요청/응답 형식에 맞춰 `api.js` 구현
- Agent 1의 서버가 `localhost:8000` 에서 동작한다고 가정

**완료 기준**
- 폴더 브라우저 모달에서 경로 선택 가능
- 폴더 비교 결과 트리 표시
- 파일 diff 사이드-바이-사이드 표시
- 머지 결정 → 저장 워크플로우 동작
- 키보드 단축키 전체 동작
- 알림 토스트 표시

---

### Agent 3 — QA / Integration

**담당 파일**
```
gui/backend/tests/
├── conftest.py
├── test_browse_api.py
├── test_compare_api.py
└── test_merge_api.py
```

**책임**
- FastAPI TestClient 기반 API 테스트
- 정상 시나리오 및 오류 케이스 검증
- 경계값 테스트 (빈 폴더, 바이너리 파일, 권한 없음 등)
- `pytest` 실행 환경 설정

**선행 조건**
- Agent 1의 API 구현 완료
- `api-spec.md` 응답 형식 기준으로 어서션 작성

**완료 기준**
- `pytest gui/backend/tests/` 전체 통과
- 커버리지: API 핸들러 80% 이상

---

## 인터페이스 (경계)

에이전트 간 유일한 결합점은 **API 명세** (`api-spec.md`) 입니다.

```
Agent 1 ──[HTTP JSON]──→ Agent 2
              ↑
        api-spec.md
              ↑
Agent 3 ────────────────→ Agent 1 (테스트)
```

- Agent 1이 `api-spec.md`를 변경할 경우 Agent 2에 즉시 통보
- Agent 2는 Mock 서버로 선행 개발 가능
- Agent 3은 Agent 1 완료 후 시작

---

## 실제 구현 순서

이 프로젝트에서는 단일 에이전트가 순서대로 구현합니다:

1. **Agent 1 역할**: `gui/backend/` 구현
2. **Agent 2 역할**: `gui/frontend/` 구현
3. **Agent 3 역할**: `gui/backend/tests/` 구현 및 검증
