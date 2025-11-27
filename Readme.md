# MVNO 뉴스 자동 수집 시스템

네이버 뉴스 API를 활용한 MVNO 관련 뉴스 자동 수집 및 분석 시스템입니다.

## 📋 주요 기능

### 1. 실시간 뉴스 수집 (`naver_news.py`)
- **실행 주기**: 3시간마다 자동 실행
- **검색 기간**: 최근 3시간 뉴스
- **기능**:
  - 10개 키워드별 뉴스 수집
  - 중복 제거 (기존 수집 뉴스 제외)
  - 유사 제목 그룹화 (임계값: 0.60)
  - JSON, Excel, Markdown 저장
  - Telegram 요약 알림

### 2. 일일 뉴스 요약 (`naver_news_daily_summary.py`)
- **실행 주기**: 매일 오전 10시 (KST)
- **검색 기간**: 전날 00:00 ~ 23:59
- **기능**:
  - 키워드별 최대 50개 뉴스 수집
  - 전일 뉴스 종합 분석
  - 일일 리포트 생성

## 🎯 검색 키워드

우선순위 순서 (중복 시 앞쪽 키워드로 분류):
1. 알뜰폰
2. MVNO
3. 유모바일
4. 미디어로그
5. 헬로모바일
6. KT엠모바일
7. KTM
8. 텔링크
9. 세븐모바일
10. 스카이라이프

## 📂 디렉토리 구조

```
├── mvno_news/                    # 뉴스 데이터 (JSON)
│   ├── mvno_news_YYYYMMDD_HHMMSS.json     # 실시간 수집
│   └── mvno_daily_YYYYMMDD.json           # 일일 요약
├── news_reports/                 # 분석 리포트
│   ├── mvno_news_YYYYMMDD_HHMMSS.xlsx
│   ├── mvno_news_YYYYMMDD_HHMMSS.md
│   ├── mvno_daily_YYYYMMDD.xlsx
│   └── mvno_daily_YYYYMMDD.md
├── config.py                     # 설정 파일
├── naver_news.py                 # 실시간 수집 스크립트
├── naver_news_daily_summary.py   # 일일 요약 스크립트
└── .github/workflows/
    ├── mvno_news_collect.yml     # 실시간 수집 워크플로우
    └── mvno_news_daily.yml       # 일일 요약 워크플로우
```

## 🔧 환경 변수 설정

GitHub Secrets에 다음 값들을 설정하세요:

```
TELEGRAM_BOT_TOKEN          # 텔레그램 봇 토큰
TELEGRAM_CHAT_ID_NEWS       # 뉴스 알림용 채팅 ID
NAVER_CLIENT_ID             # 네이버 API 클라이언트 ID
NAVER_CLIENT_SECRET         # 네이버 API 클라이언트 시크릿
```

## ⚙️ 설정 커스터마이징

### config.py

```python
# 키워드당 수집 개수
NEWS_COUNT = 10

# 유사도 임계값 (0.0~1.0)
SIMILARITY_THRESHOLD = 0.60
```

### 워크플로우 수동 실행 시 파라미터

**실시간 수집**:
- `search_hours`: 검색 기간 (시간), 기본값 3
- `similarity_threshold`: 유사도 임계값, 기본값 0.60

**일일 요약**:
- `similarity_threshold`: 유사도 임계값, 기본값 0.60

## 📊 데이터 형식

### JSON 구조
```json
{
  "collection_time": "2025-01-15 10:00 KST",
  "search_hours": 3,
  "similarity_threshold": 0.60,
  "statistics": {
    "total_news": 25,
    "by_keyword": {
      "알뜰폰": 10,
      "MVNO": 8,
      "유모바일": 7
    }
  },
  "news_by_keyword": {
    "알뜰폰": [
      [
        {
          "title": "...",
          "link": "...",
          "pubDate": "..."
        }
      ]
    ]
  }
}
```

### Excel 컬럼
- 키워드
- 제목
- 링크
- 발행일
- 유사기사수
- 그룹크기

## 🚀 실행 방법

### 로컬 테스트
```bash
# 환경 변수 설정
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID_NEWS="your_chat_id"
export NAVER_CLIENT_ID="your_client_id"
export NAVER_CLIENT_SECRET="your_client_secret"

# 실시간 수집
python naver_news.py

# 일일 요약
python naver_news_daily_summary.py
```

### GitHub Actions
- **자동 실행**: 설정된 스케줄에 따라 자동 실행
- **수동 실행**: Actions 탭 → 워크플로우 선택 → "Run workflow"

## 📈 주요 특징

### 1. 중복 제거 시스템
- **링크 기반**: 동일 URL 제거
- **제목 정규화**: 유사 제목 통합
- **키워드 우선순위**: 앞쪽 키워드 우선

### 2. 유사 뉴스 그룹화
- SequenceMatcher 알고리즘 사용
- 임계값 0.60으로 유사도 판정
- 대표 제목 자동 선택 (가장 긴 제목)

### 3. 기간 필터링
- **실시간**: 최근 N시간 뉴스만 수집
- **일일**: 전날 00:00~23:59 뉴스만 수집
- KST 기준 시간대 처리

### 4. 데이터 보존
- 실시간 수집 시 기존 데이터와 중복 체크
- 7일/30일 히스토리 자동 정리
- Git을 통한 영구 보관

## 🔔 Telegram 알림

### 실시간 수집 알림
```
📰 MVNO 뉴스 수집 완료

📅 2025-01-15 10:00 KST
⏱️ 최근 3시간 뉴스
📊 새 뉴스: 25개

📈 키워드별 통계
  • 알뜰폰: 10개
  • MVNO: 8개
  • 유모바일: 7개

💾 저장 파일
  • JSON: mvno_news/mvno_news_20250115_100000.json
  • Excel: news_reports/mvno_news_20250115_100000.xlsx
  • Markdown: news_reports/mvno_news_20250115_100000.md
```

### 일일 요약 알림
```
📊 MVNO 일일 뉴스 요약

📅 보고 날짜: 2025-01-14 (전일)
🕐 생성 시간: 2025-01-15 10:00 KST
📰 총 기사: 87개

📈 키워드별 통계
  • 알뜰폰: 35개
  • MVNO: 28개
  • 유모바일: 24개

💾 저장 파일
  • JSON: mvno_news/mvno_daily_20250114.json
  • Excel: news_reports/mvno_daily_20250114.xlsx
  • Markdown: news_reports/mvno_daily_20250114.md
```

## 🛠️ 트러블슈팅

### GitHub Actions 제한 초과 시
- 현재 패턴: API → 데이터 → 저장 → Git push → Telegram 요약
- 모든 뉴스 내용은 파일로 저장되고 Git에 커밋됨
- Telegram에는 요약만 전송하여 API 호출 최소화

### 새 뉴스가 없을 때
- Git commit/push 생략
- Telegram 알림 없음
- 로그만 출력

## 📝 라이선스

MIT License
