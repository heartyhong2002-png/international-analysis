import requests

def ask_solar(prompt, model="kristada673/solar-10.7b-instruct-v1.0-uncensored"):
    """SOLAR 모델에게 질문하고 답변 받기"""
    
    # 한국어로 답하도록 명시적으로 지시 추가
    full_prompt = f"{prompt}\n\n반드시 한국어로만 답변하세요. Please answer only in Korean language, not English."
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": full_prompt,
            "stream": False
        }
    )
    return response.json()["response"]

if __name__ == "__main__":
    print("🚀 SOLAR 테스트 시작\n")
    
    prompt = "미국과 중국의 무역전쟁이 한국 경제에 미치는 영향을 3가지로 요약해줘."
    
    print(f"질문: {prompt}\n")
    print("🔄 답변 생성 중...\n")
    
    result = ask_solar(prompt)
    
    print("답변:")
    print(result)