# 🎓 AI Teacher Agent

생성형 AI와 Agent Workflow를 활용하여   
PPT 기반 강의 콘텐츠를 자동 생성하는 AI 교육 자동화 프로젝트입니다.

사용자가 PPT를 업로드하면 AI가 슬라이드 내용을 분석하고,  
강의 스크립트 생성 → 음성 변환(TTS) → 영상 제작 → 퀴즈 생성까지 자동 수행합니다.

---

# 📌 프로젝트 소개

기존 온라인 강의 제작 과정은 다음과 같은 많은 작업이 필요합니다.

- PPT 제작
- 강의 대본 작성
- 음성 녹음
- 영상 편집
- 자막 및 퀴즈 제작

본 프로젝트는 이러한 과정을 생성형 AI 기반 Agent 시스템으로 자동화하여  
AI가 실제 강사처럼 강의를 생성하도록 설계되었습니다.

---

# 🚀 주요 기능

## 1️⃣ PPT 슬라이드 분석

- 슬라이드 제목 및 텍스트 추출
- 발표 흐름 분석
- 교육 콘텐츠 구조 이해

---

## 2️⃣ 외부 검색 기반 정보 보강

- Tavily Search API 활용
- 슬라이드에 부족한 내용 자동 검색
- 최신 정보 기반 설명 생성

### Example

```text
PPT에 "Transformer"만 적혀 있어도
AI가 Transformer 개념과 활용 사례를 자동 검색 후 설명 생성
```

---

## 3️⃣ AI 강의 스크립트 생성

- 슬라이드별 발표 대본 생성
- 자연스러운 강의 흐름 구성
- 교육용 설명 스타일 적용

### Example

```text
이번 슬라이드에서는 Transformer 구조에 대해 살펴보겠습니다.
Transformer는 Self-Attention 메커니즘을 기반으로...
```

---

## 4️⃣ 음성 생성 (TTS)

- OpenAI TTS 기반 음성 생성
- 슬라이드별 AI 음성 생성
- 영상 길이 자동 동기화

---

## 5️⃣ 강의 영상 생성

- PPT 슬라이드를 이미지로 변환
- 음성과 슬라이드 결합
- MP4 영상 자동 생성

---

## 6️⃣ 영상 병합

- 슬라이드별 영상 자동 병합
- 최종 강의 영상 생성

```text
Final_Lecture.mp4
```

---

## 7️⃣ 요약 및 퀴즈 생성

- 강의 전체 내용 요약
- 핵심 개념 정리
- AI 기반 예상 문제 생성

---

# 🧠 Agent Workflow 구조

```text
PPT Upload
    ↓
Slide Analysis
    ↓
External Search
    ↓
Lecture Script Generation
    ↓
TTS Voice Generation
    ↓
Video Rendering
    ↓
Video Merge
    ↓
Summary & Quiz Generation
```

---

# ⚙️ 기술 스택

## 🔹 AI / LLM

- OpenAI API
- LangChain
- LangGraph

### 역할

- 강의 스크립트 생성
- 요약 생성
- 퀴즈 생성
- Agent 상태 관리

---

## 🔹 Search / RAG

- Tavily Search API

### 역할

- 외부 정보 검색
- 최신 데이터 기반 설명 보강
- Retrieval 기반 생성 시스템 구축

---

## 🔹 Multimedia Processing

- ffmpeg
- python-pptx
- Pillow(PIL)

### 역할

- PPT 이미지 추출
- 음성 + 슬라이드 결합
- 영상 렌더링 및 병합

---

## 🔹 TTS

- OpenAI Text-to-Speech

### 역할

- AI 음성 생성
- 강의 오디오 제작

---

## 🔹 Web Application

- Gradio

### 역할

- 웹 인터페이스 제공
- PPT 업로드
- 결과 영상 다운로드

---

# 📂 프로젝트 구조

```bash
AI-Teacher-Agent/
│
├── data/
├── outputs/
├── slides/
├── audio/
├── video/
│
├── app.py
├── main.py
├── agent.py
├── utils.py
├── requirements.txt
│
└── README.md
```

---

# 🖥️ 실행 방법

## 1️⃣ 저장소 클론

```bash
git clone https://github.com/your-github-id/AI-Teacher-Agent.git
```

---

## 2️⃣ 패키지 설치

```bash
pip install -r requirements.txt
```

---

## 3️⃣ API KEY 설정

```python
OPENAI_API_KEY=YOUR_API_KEY
TAVILY_API_KEY=YOUR_API_KEY
```

---

## 4️⃣ 실행

```bash
python app.py
```

또는

```bash
gradio app.py
```

---

# 📸 프로젝트 결과 예시

## 입력

- PPT 파일 업로드

## 출력

- AI 강의 영상 (.mp4)
- AI 음성 (.mp3)
- 강의 요약
- 예상 문제 및 퀴즈

---

# 💡 프로젝트 특징

## ✅ 생성형 AI + 멀티미디어 자동화

단순 챗봇이 아니라:

- 텍스트 생성
- 음성 생성
- 영상 생성

을 통합한 AI 자동화 시스템입니다.

---

## ✅ LangGraph 기반 Agent 구조

- Node 기반 Workflow
- 상태(State) 관리
- 자동 실행 파이프라인

구조를 적용했습니다.

---

## ✅ 실제 서비스형 프로젝트

Gradio 기반 Web UI를 포함하여  
실제 사용 가능한 서비스 형태로 구현했습니다.

---

# 📈 기대 효과

## 교육 산업 활용

- 온라인 강의 자동 제작
- 기업 교육 자동화
- AI 튜터 시스템
- LMS 플랫폼 연동
- 유튜브 강의 자동 생성

---

# 🧩 향후 개선 방향

- 개인 맞춤형 강의 생성
- 다국어 강의 지원
- 실시간 질의응답 챗봇
- 학습 데이터 분석 기능
- 추천 강의 시스템

---

# 🎯 프로젝트 핵심 가치

```text
PPT를 입력받아
AI가 강의 내용을 생성하고,
음성과 영상까지 자동 제작하는
생성형 AI 기반 교육 콘텐츠 자동화 시스템
```

---

# 👨‍💻 Contributors

- 김남효,조성준,조영진,김도훈,유승찬,이호,박병린,성현욱
- Team Project

---

# 📜 License

This project is licensed under the MIT License.
