# 🏛️ 오픈소스 LLM 다자간 교차 검증(Consensus) 감사 리포트

- **실행 일시**: 2026-09-18 12:51:42
- **검증 모드**: BENCHMARK
- **참여 모델**:
  - `mistral:latest` (Mistral AI — 영미권/서방 시각)
  - `qwen2.5:7b` (Alibaba — 아시아/글로벌 다국어 시각)
  - `exaone3.5:7.8b` (LG AI Research — 한국/동아시아 외교 시각)

---

## 1. 📊 종합 합의 지표 (Consensus Metrics)

| 지표 항목 | 수치 | 비고 |
| :--- | :--- | :--- |
| **총 평가 건수** | 5건 | 100% |
| **만장일치 합의 (3:0, Unanimous)** | 4건 | 신뢰도 High (자동 승인) |
| **다수결 합의 (2:1, Majority)** | 1건 | 신뢰도 Medium (다수 채택) |
| **의견 분열 (1:1:1, Split)** | 0건 | 신뢰도 Low (심층 검수 필요) |
| **고신뢰 합의 도출률** | **100.0%** | (만장일치 + 다수결) |
| **다수결 합의 최종 정확도** | **100.0%** | 정답(Ground Truth) 대비 |

---

## 2. 🔍 개별 모델 성능 및 일치율

| 모델명 | 개별 정답률 (Accuracy) | 평가 역할 |
| :--- | :--- | :--- |
| `mistral:latest` | **100.0%** | 서방/아시아/한국 교차 검증 |
| `qwen2.5:7b` | **80.0%** | 서방/아시아/한국 교차 검증 |
| `exaone3.5:7.8b` | **100.0%** | 서방/아시아/한국 교차 검증 |

---

## 3. 📝 세부 교차 검증 내역

| ID | 기사 제목 | 정답/기존 | 다수결 합의 | 합의상태 | 이견 모델 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| BM-01 | US inflation rises to 3.5%, prompting Federal... | 중립적 | **중립적** | `UNANIMOUS` | 없음(만장일치) |
| BM-02 | Opposition lawmakers fiercely condemn governm... | 비판적 | **비판적** | `UNANIMOUS` | 없음(만장일치) |
| BM-03 | South Korea and United States sign milestone ... | 우호적 | **우호적** | `MAJORITY` | qwen2.5:7b |
| BM-04 | Ukrainian military strikes Russian ammunition... | 중립적 | **중립적** | `UNANIMOUS` | 없음(만장일치) |
| BM-05 | Editorial: European leadership displays pathe... | 비판적 | **비판적** | `UNANIMOUS` | 없음(만장일치) |

---

## 4. 💡 엔지니어링 의의 및 포트폴리오 결론
1. **주관적 편향 배제**: 특정 개인의 편향된 시각 대신 독립적인 3대 모델의 앙상블 합의(Consensus)를 통해 톤 라벨링의 객관성 확보.
2. **이상치 자동 플래그**: 3개 모델이 분열하거나 이견을 낸 난해한 케이스만 선별 추출하여 검수 리소스를 80% 이상 절감(Active Learning).
