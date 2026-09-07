from huggingface_hub import snapshot_download

print("🚀 SOLAR-10.7B 다운로드 재개 중...")
print("(이미 받은 부분은 건너뛰고 이어서 받습니다)\n")

snapshot_download(
    repo_id="upstage/SOLAR-10.7B-Instruct-v1.0",
    resume_download=True  # 이어받기 명시
)

print("\n✅ 다운로드 완료!")