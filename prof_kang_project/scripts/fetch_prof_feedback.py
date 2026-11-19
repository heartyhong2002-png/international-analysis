"""
강송희 교수님 이메일 피드백 자동 수집 스크립트 (Gmail API 기반)
- 강송희 교수님 공식 메일(dellabee@tukorea.ac.kr) 또는 '강송희' 키워드로 검색합니다.
- 중복 저장을 방지하고, 피드백 문서를 prof_kang_project/feedbacks/ 에 자동 생성합니다.
"""

import os
import sys
import base64
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
FEEDBACKS_DIR = os.path.join(BASE_DIR, 'feedbacks')
CREDENTIALS_FILE = os.path.join(CONFIG_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(CONFIG_DIR, 'token.json')

PROFESSOR_EMAIL = 'dellabee@tukorea.ac.kr'

def get_gmail_service():
    """OAuth 2.0 인증을 거쳐 Gmail API 서비스 객체를 반환합니다."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"인증 파일이 없습니다: {CREDENTIALS_FILE}\n"
                    "GCP 콘솔에서 다운로드한 OAuth 클라이언트 JSON을 config/credentials.json 으로 저장해주세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def search_emails(service, query, max_results=5):
    """지정된 쿼리로 이메일을 검색합니다."""
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    return messages

def parse_email(service, msg_id):
    """메일 ID로부터 발신자, 제목, 날짜, 본문을 파싱합니다."""
    message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = message.get('payload', {})
    headers = payload.get('headers', [])
    
    subject = ''
    sender = ''
    date_str = ''
    
    for h in headers:
        name = h.get('name', '').lower()
        if name == 'subject':
            subject = h.get('value', '')
        elif name == 'from':
            sender = h.get('value', '')
        elif name == 'date':
            date_str = h.get('value', '')

    body = ''
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
    elif 'body' in payload:
        data = payload.get('body', {}).get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    return {
        'id': msg_id,
        'subject': subject,
        'sender': sender,
        'date': date_str,
        'body': body.strip()
    }

def save_feedback_markdown(email_data):
    """수집된 이메일을 피드백 Markdown 파일로 변환하여 저장합니다."""
    os.makedirs(FEEDBACKS_DIR, exist_ok=True)
    today_str = datetime.now().strftime('%Y%m%d')
    file_path = os.path.join(FEEDBACKS_DIR, f"{today_str}_email_{email_data['id']}.md")

    if os.path.exists(file_path):
        print(f"이미 존재하는 피드백 파일입니다: {file_path}")
        return

    md_content = f"""# [이메일 피드백] {email_data['subject']}

- **수신 일시**: {email_data['date']}
- **발신자**: {email_data['sender']}
- **수집 방식**: Gmail API 자동 연동 (`{email_data['id']}`)

---

## 1. 메일 원문 요약 및 내용
```text
{email_data['body']}
```

---

## 2. 강송희 교수님 주요 피드백 및 조언 분석
> 본문 내용에서 추출한 핵심 요구사항과 보완점

### 📌 연구 방향 / 과업 관련
- 

### 📌 보고서 / PPT / 논문 관련
- 

---

## 3. 후속 조치 및 Action Items (To-Do List)
| No | 과업 내용 (Action Item) | 세부 설명 및 산출물 | 기한 (Due) | 상태 (Status) |
|:--:|:-----------------------|:-------------------|:----------:|:-------------:|
| 1  | 메일 피드백 반영 사항 확인 | 세부 내용 검토 및 반영 계획 수립 | - | 대기 |

---
*자동 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"피드백 문서 저장 완료: {file_path}")

def main():
    # 교수님 이메일(dellabee@tukorea.ac.kr) 또는 '강송희' 키워드 메일 검색
    query = f"from:{PROFESSOR_EMAIL} OR 강송희"
    print(f"Gmail 검색 쿼리 실행 중: '{query}'")
    
    try:
        service = get_gmail_service()
        messages = search_emails(service, query=query, max_results=5)
        
        if not messages:
            print("조건에 맞는 메일이 없습니다.")
            return

        for m in messages:
            email_data = parse_email(service, m['id'])
            print(f"- 발견: [{email_data['date']}] {email_data['subject']}")
            save_feedback_markdown(email_data)
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == '__main__':
    main()
