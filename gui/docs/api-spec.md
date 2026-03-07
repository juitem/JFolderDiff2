# REST API 명세

Base URL: `http://localhost:8000`

---

## GET /api/browse

파일시스템의 특정 경로 내 항목 목록을 반환합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `path` | string | ○ | 탐색할 절대 경로 |

**Response 200**

```json
{
  "path": "/Users/juitem",
  "parent": "/Users",
  "entries": [
    {
      "name": "Documents",
      "path": "/Users/juitem/Documents",
      "is_dir": true,
      "size": null,
      "modified": "2025-01-01T00:00:00"
    },
    {
      "name": "notes.txt",
      "path": "/Users/juitem/notes.txt",
      "is_dir": false,
      "size": 1024,
      "modified": "2025-01-02T00:00:00"
    }
  ]
}
```

**Response 400** — 경로가 존재하지 않거나 디렉터리가 아닌 경우

---

## GET /api/compare

두 폴더를 비교하여 항목 트리와 통계를 반환합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `left` | string | ○ | 왼쪽 폴더 절대 경로 |
| `right` | string | ○ | 오른쪽 폴더 절대 경로 |

**Response 200**

```json
{
  "left": "/path/to/left",
  "right": "/path/to/right",
  "stats": {
    "same": 3,
    "different": 2,
    "left_only": 1,
    "right_only": 1,
    "total": 7
  },
  "entries": [
    {
      "name": "subdir",
      "rel_path": "subdir",
      "is_dir": true,
      "status": "different",
      "left_abs": "/path/to/left/subdir",
      "right_abs": "/path/to/right/subdir",
      "depth": 0,
      "children": [...]
    },
    {
      "name": "modified.txt",
      "rel_path": "modified.txt",
      "is_dir": false,
      "status": "different",
      "left_abs": "/path/to/left/modified.txt",
      "right_abs": "/path/to/right/modified.txt",
      "depth": 0,
      "children": []
    }
  ]
}
```

**Response 400** — 경로가 유효하지 않은 경우

---

## GET /api/diff

두 파일을 비교하여 diff 청크와 정렬된 행 목록을 반환합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `left` | string | ✕ | 왼쪽 파일 절대 경로 (없으면 빈 파일) |
| `right` | string | ✕ | 오른쪽 파일 절대 경로 (없으면 빈 파일) |

**Response 200**

```json
{
  "left_path": "/path/to/left/file.txt",
  "right_path": "/path/to/right/file.txt",
  "error": null,
  "change_count": 3,
  "chunks": [
    {
      "index": 0,
      "tag": "equal",
      "left_start": 0,
      "left_end": 1,
      "right_start": 0,
      "right_end": 1
    },
    {
      "index": 1,
      "tag": "replace",
      "left_start": 1,
      "left_end": 2,
      "right_start": 1,
      "right_end": 2
    }
  ],
  "aligned": [
    {
      "left_lineno": 1,
      "right_lineno": 1,
      "left_text": "First line",
      "right_text": "First line",
      "chunk_idx": 0,
      "tag": "equal"
    },
    {
      "left_lineno": 2,
      "right_lineno": 2,
      "left_text": "Old second line",
      "right_text": "New second line",
      "chunk_idx": 1,
      "tag": "replace"
    }
  ]
}
```

**error 필드** — 바이너리 파일이거나 읽기 실패 시 오류 메시지, 정상이면 `null`

---

## POST /api/merge

머지 결정을 적용하여 파일에 저장합니다.

**Request Body**

```json
{
  "left_path": "/path/to/left/file.txt",
  "right_path": "/path/to/right/file.txt",
  "decisions": {
    "1": "left",
    "3": "right"
  }
}
```

- `decisions` 키: 청크 인덱스 (문자열)
- `decisions` 값: `"left"` (오른쪽 파일에 왼쪽 내용 적용) | `"right"` (왼쪽 파일에 오른쪽 내용 적용)

**Response 200**

```json
{
  "success": true,
  "saved_files": ["/path/to/right/file.txt"],
  "message": "저장 완료"
}
```

**Response 400** — 경로가 유효하지 않은 경우
**Response 500** — 저장 중 오류 발생

---

## 오류 응답 공통 형식

```json
{
  "detail": "오류 메시지"
}
```
