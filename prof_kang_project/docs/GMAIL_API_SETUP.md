# Gmail API를 활용한 강송희 교수님 이메일 피드백 자동 수집 가이드

본 문서는 강송희 교수님께서 이메일(Gmail)로 보내주시는 피드백 및 공지사항을 로컬 환경에 자동으로 수집·정리하기 위한 연동 매뉴얼입니다.

---

## 1. 연동 방식 비교 (추천 방식)

| 방식 | 보안/권한 | 구현 난이도 | 장점 | 단점 |
|:---|:---:|:---:|:---|:---|
| **방법 1: 공식 Gmail API (OAuth 2.0)** ⭐ **[권장]** | 세분화된 읽기 전용(`gmail.readonly`) | 보통 (최초 1회 인증) | • 계정 비밀번호 노출 없음<br>• 특정 라벨/검색어로 필터링 수집 용이 | GCP 프로젝트 생성 및 OAuth 클라이언트 ID 발급 필요 |
| **방법 2: IMAP + 앱 비밀번호(App Password)** | 전체 메일 접근 권한 | 쉬움 | 빠른 연동 가능 | • 구글 2단계 인증 필수<br>• 앱 비밀번호 발급 필요 |

> 💡 **추천**: 교수님 메일만 안전하게 **읽기 전용(`gmail.readonly`)**으로 긁어오기 위해서는 **방법 1 (공식 Gmail API)**이 가장 안전하고 권장됩니다.

---

## 2. 방법 1: 공식 Gmail API 연동 단계별 가이드

### [Step 1] Google Cloud Console 설정 (1회성)
1. [Google Cloud Console](https://console.cloud.google.com/) 접속 및 로그인
2. 새 프로젝트 생성 (예: `prof-kang-feedback-sync`)
3. **API 및 서비스 > 라이브러리** 이동 $\rightarrow$ **Gmail API** 검색 후 **[사용]** 클릭
4. **OAuth 동의 화면 (Consent Screen)** 구성:
   - User Type: **외부 (External)** 선택
   - 앱 이름: `Feedback Sync Bot`, 사용자 지원 이메일 입력
   - 범위(Scope): `https://www.googleapis.com/auth/gmail.readonly` 추가 (읽기 전용)
   - 테스트 사용자: 본인의 Gmail 주소 등록
5. **사용자 인증 정보 (Credentials)** 생성:
   - `+ 사용자 인증 정보 만들기` $\rightarrow$ `OAuth 클라이언트 ID`
   - 애플리케이션 유형: **데스크톱 앱 (Desktop App)**
   - 이름: `Gmail Feedback Client`
   - 생성 완료 후 **`JSON 다운로드`** 클릭 $\rightarrow$ 파일명을 `credentials.json`으로 변경하여 `prof_kang_project/config/` 폴더에 저장

---

### [Step 2] 필요한 Python 패키지 설치
터미널에서 아래 라이브러리를 설치합니다:
```bash
py -m pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

### [Step 3] 자동 수집 및 피드백 변환 스크립트 실행
- 스크립트 위치: `prof_kang_project/scripts/fetch_prof_feedback.py`
- 검색 쿼리: `from:교수님메일주소` 또는 `강송희` 키워드가 들어간 최신 메일 조회
- 조회된 메일 본문을 Markdown 형식(`prof_kang_project/feedbacks/YYYYMMDD_email_feedback.md`)으로 자동 저장

---

## 3. 방법 2: IMAP (앱 비밀번호) 방식 (간이 연동)

GCP 콘솔 설정이 번거로운 경우, 구글 계정 보안 설정에서 **앱 비밀번호**를 생성하여 IMAP으로 바로 가져올 수 있습니다.

1. **Google 계정 관리 > 보안** 접속
2. **2단계 인증** 활성화 확인
3. 검색창에 **"앱 비밀번호"** 검색 $\rightarrow$ 앱 이름 입력(예: `Antigravity Mail`) 후 16자리 비밀번호 발급
4. `.env` 파일에 저장:
   ```env
   GMAIL_USER=your_email@gmail.com
   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   PROFESSOR_EMAIL=교수님메일주소@tukorea.ac.kr
   ```
5. 파이썬 기본 내장 모듈 `imaplib`와 `email`을 사용해 교수님 발신 메일만 수집
