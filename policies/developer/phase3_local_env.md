# 3단계 - 로컬 개발환경 (AX 개발자)

## 이 단계는
내 PC에서 AI 앱을 직접 짜고 돌려보려면 파이썬 런타임(파이썬 코드를 실제로 실행하는 프로그램), git, AI 개발 SDK, 모델 API 키 4가지가 필요합니다. 이 단계에서 그 4가지를 한 번에 갖춰, 코드를 작성하면 바로 실행되는 상태를 만듭니다.

## 무엇을 준비하나
- Python 3.11 이상: 우리가 쓰는 AI SDK(AI 앱을 만들 때 가져다 쓰는 코드 묶음)들이 3.11 기준으로 동작합니다. 버전이 낮으면 설치 자체가 깨지므로 먼저 맞춥니다.
- git: 코드를 받고 올리고 되돌리는 형상관리(코드 변경 이력을 저장하고 예전 상태로 되돌릴 수 있게 하는) 도구입니다. 개발자는 매일 씁니다.
- AI 개발 SDK: LLM 호출과 에이전트 흐름을 다루는 핵심 코드 묶음입니다. langgraph로 에이전트 그래프(AI가 일을 처리하는 순서도)를 짜고, langchain-openai로 모델을 호출합니다.
- OPENAI_API_KEY: 모델 API(외부 AI 모델을 불러 쓰는 통로)를 부를 때 본인임을 증명하는 키입니다. 이게 없으면 코드는 돌아도 모델 응답을 못 받습니다.

```bash
# 파이썬 런타임과 git 확인
python3 --version
git --version

# AI 개발 SDK 설치 (langgraph, langchain-openai 포함, requirements.txt 는 깔아야 할 라이브러리 목록 파일)
pip install -r requirements.txt

# 모델 API 키 설정 (.env 파일에 한 줄 또는 Secrets 에 등록)
echo 'OPENAI_API_KEY=sk-...' >> .env
export OPENAI_API_KEY=sk-...
```

## 검증 항목
- Python 3.11 이상: python3 --version 이 3.11 이상인지
- git CLI: git --version 이 정상 동작하는지
- AI 개발 SDK: python3 -c "import langgraph, langchain_openai" 가 성공하는지
- OPENAI_API_KEY 설정: 환경변수 OPENAI_API_KEY 가 존재하는지

## 문제 해결 (트러블슈팅)
- Python 버전이 낮으면 pyenv install 3.11 후 pyenv local 3.11 로 버전을 고정합니다 (pyenv 는 파이썬 버전을 여러 개 깔고 골라 쓰게 해 주는 도구).
- git이 없으면 git 공식 설치 가이드로 설치합니다.
- import(코드가 라이브러리를 불러오는 명령)가 실패하면 SDK가 아직 안 깔린 것입니다. pip install -r requirements.txt 를 다시 실행합니다.
- OPENAI_API_KEY가 비어 있으면 .env 에 OPENAI_API_KEY=sk-... 한 줄을 추가하거나 Secrets(API 키 같은 민감한 값을 안전하게 보관하는 곳)에 등록한 뒤 셸을 다시 엽니다.
