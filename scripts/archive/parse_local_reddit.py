import json
import os

def extract_comments_recursive(children, comment_list):
    for child in children:
        if child.get('kind') == 't1' and 'data' in child:
            data = child['data']
            author = data.get('author', 'Unknown')
            upvotes = data.get('ups', 0)
            body = data.get('body', '')
            
            if body:
                comment_list.append({
                    'author': author,
                    'upvotes': upvotes,
                    'body': body
                })
                
            # 대댓글(replies)이 존재하는 경우 재귀적으로 추출
            replies = data.get('replies')
            if replies and isinstance(replies, dict):
                reply_children = replies.get('data', {}).get('children', [])
                extract_comments_recursive(reply_children, comment_list)

def parse_local_reddit_json(file_path):
    if not os.path.exists(file_path):
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print("✅ 로컬 JSON 파일을 성공적으로 불러왔습니다!\n")
        print("="*50)
        
        if len(data) > 1 and 'data' in data[1]:
            top_level_children = data[1]['data']['children']
            all_comments = []
            
            extract_comments_recursive(top_level_children, all_comments)
            
            for idx, c in enumerate(all_comments, 1):
                print(f"\n--- [댓글 {idx}] 작성자: {c['author']} (추천 수: {c['upvotes']}) ---")
                print(f"{c['body']}")
                print("-" * 50)
                
            if len(all_comments) == 0:
                print("이 게시물에는 아직 일반 댓글이 없습니다.")
            else:
                print(f"\n총 {len(all_comments)}개의 댓글(대댓글 포함)을 성공적으로 추출했습니다!")
                
    except Exception as e:
        print(f"파일을 파싱하는 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    json_file_path = r"c:\Users\홍준기\Desktop\international-analysis\reddit_data.json"
    parse_local_reddit_json(json_file_path)
