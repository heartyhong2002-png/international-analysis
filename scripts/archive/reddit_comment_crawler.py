import requests
import json
import time

def get_user_posts_and_comments(username):
    print(f"[{username}] 계정의 게시물과 댓글을 크롤링합니다...")
    
    # 레딧은 봇 차단을 막기 위해 본인의 아이디가 포함된 고유한 User-Agent를 권장합니다.
    headers = {
        'User-agent': f'python:geopolitics_crawler_kpu:v1.0 (by /u/{username})'
    }
    
    submitted_url = f"https://www.reddit.com/user/{username}/submitted.json"
    
    try:
        response = requests.get(submitted_url, headers=headers)
        response.raise_for_status()
        user_data = response.json()
        
        posts = user_data['data']['children']
        
        if not posts:
            print("작성한 게시물이 없습니다.")
            return

        print(f"총 {len(posts)}개의 게시물을 찾았습니다.\n")
        
        # 2. 각 게시물(Post)을 순회하며 달린 댓글 수집하기
        for post in posts:
            post_title = post['data']['title']
            post_permalink = post['data']['permalink']
            post_url = f"https://www.reddit.com{post_permalink}.json"
            
            print(f"==================================================")
            print(f"📌 게시물 제목: {post_title}")
            print(f"🔗 링크: https://www.reddit.com{post_permalink}")
            print(f"==================================================")
            
            # 레딧 서버에 무리를 주지 않기 위해 1초 대기 (API 차단 방지)
            time.sleep(1)
            
            # 게시물 상세 URL(.json) 호출하여 댓글 가져오기
            post_response = requests.get(post_url, headers=headers)
            post_response.raise_for_status()
            post_data = post_response.json()
            
            # data[1]에 댓글 목록이 들어있음
            if len(post_data) > 1 and 'data' in post_data[1]:
                comments = post_data[1]['data']['children']
                
                comment_count = 0
                for comment in comments:
                    if comment['kind'] == 't1' and 'body' in comment['data']:
                        comment_count += 1
                        author = comment['data'].get('author', 'Unknown')
                        body = comment['data']['body']
                        
                        print(f"\n💬 [댓글 {comment_count}] 작성자: {author}")
                        print(f"{body}")
                        print("-" * 50)
                
                if comment_count == 0:
                    print("\n아직 달린 댓글이 없습니다.\n")
            else:
                print("\n아직 달린 댓글이 없습니다.\n")

    except requests.exceptions.RequestException as e:
        print(f"크롤링 중 에러가 발생했습니다: {e}")

if __name__ == "__main__":
    REDDIT_USERNAME = "nycmouse02"
    get_user_posts_and_comments(REDDIT_USERNAME)
