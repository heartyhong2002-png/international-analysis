# ANTIGRAVITY 인수인계 프롬프트: 백악관 공식 RSS 수집기

아래 내용을 ANTIGRAVITY 세션의 첫 메시지로 사용한다.

```text
먼저 PROJECT_CONTEXT.md와 AGENT_SYNC.md를 읽고 현재 프로젝트 방향과 다른 AI 세션의 작업 상태를 파악해줘.

이 프로젝트는 국제정세 예측 시스템이 아니라 공급망·지정학 리스크 조기경보 시스템이다. 예전 예측·챗봇 문서는 docs/history 또는 docs/archive의 이력으로만 취급해.

이번 담당 범위는 백악관 공식 발표 수집기다. 작업 시작 전 git status --short를 확인하고, AGENT_SYNC.md의 Active Work Board에서 관련 파일 충돌 여부를 확인해줘. 기존 사용자 수정은 덮어쓰지 마.

현재 구현된 파일:
- scripts/collection/fetch_whitehouse_official.py
- scripts/run_pipeline.py의 --with-whitehouse 선택 플래그
- data/whitehouse_official/whitehouse_latest.json
- data/whitehouse_official/rss_latest.xml

현재 수집 경계:
1. https://www.whitehouse.gov/releases/feed/ 공식 RSS를 1순위로 사용한다.
2. 기본 실행은 최근 7일·최대 50건 메타데이터를 수집하며, 원문 HTML을 대량 다운로드하지 않는다.
3. --include-sitemap을 지정한 경우에만 사이트맵을 제한적으로 보완한다.
4. 통합 파이프라인은 --with-whitehouse를 지정한 경우에만 이 수집기를 실행한다.
5. source_url, published_at, observed_at, document_type, raw_ref, RSS 해시, parse_status, license_access_note를 보존한다.
6. 백악관 발표는 공식 입장 신호이지 사실 확정이나 Alert Level이 아니다. 수집 세션에서 교차검증·LLM 분석·대시보드·DB 로직을 추가하지 않는다.
7. robots.txt, 이용약관, 요청 간격을 준수하고 검색 쿼리 우회·로그인·접근제한 회피를 하지 않는다.

먼저 소량 드라이런을 실행해:
python scripts/collection/fetch_whitehouse_official.py --days 1 --limit 3

그 다음 다음 사항만 점검해줘:
- RSS의 pubDate/date 파싱과 UTC 정규화
- 동일 URL 중복 제거
- RSS 원문과 JSON 영수증의 재현성
- 사이트맵을 켰을 때 요청 상한이 지켜지는지
- run_pipeline.py --help에 --with-whitehouse가 노출되는지

필요한 수정이 있으면 수집기와 수집 문서만 수정하고, 작업 종료 시 AGENT_SYNC.md에 바꾼 파일·검증 결과·다음 작업·주의할 점을 짧게 남겨줘.
```
