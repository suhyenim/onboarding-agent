# 온보딩 에이전트 (Onboarding Agent)

신입 AX 개발자가 첫 출근 후 AI 개발 환경을 스스로 갖추도록 돕는 온보딩 코치입니다.
단계별 정책 문서를 출처에서 실시간으로 읽어 안내하고, 환경 점검을 에이전트가 직접 실제 셸 명령으로 실행하며, 진행 상황을 단계 스텝퍼로 추적합니다.

## 무엇이 다른가 (단순 챗봇이 아님)
- 도구를 실제로 호출합니다: `read_policy`, `verify_environment`, `record_progress`.
- 추측하지 않습니다: 계정/경로/환경변수명 같은 값은 `policies/developer/*.md` 에서 매번 읽어 출처로 답합니다.
- 점검을 진짜로 실행합니다: 모의 데이터가 아니라, 앱이 도는 환경에서 실제 명령(`python3 --version`, `git --version`, SDK import 체크 등)을 subprocess 로 실행해 결과로 통과/실패를 판정합니다. 화이트리스트로 고정된 read-only 명령만 실행합니다.
- 단계 경계를 강제합니다: 앞 단계를 통과하지 못하면 다음 단계 점검을 코드 레벨에서 막습니다.
- 에이전트가 터미널에 명령을 직접 입력하는 모습을 보여줍니다: 신입이 채팅으로 부탁하면, 오른쪽 터미널에 점검 명령이 한 줄씩 쳐지고 각 명령이 무슨 일을 하는지 한국어로 함께 표시됩니다.

## 온보딩 단계 (1~5단계)
- 1단계 정보 입력 (이름, 사번, 팀) - 채팅으로 받고, 입력 완료가 곧 통과
- 2단계 사전 준비 (계정, 셸 기본)
- 3단계 로컬 개발환경 (파이썬, git, AI SDK, 모델 API 키)
- 4단계 AI 개발 스택 (langchain, 정책 파일)
- 5단계 빌드/배포 (앱 실행, 배포)

각 단계는 "설명 듣기 -> (필요 시) 설치/설정 -> 검증 -> 통과 시 다음 단계" 순서로 진행됩니다.
화면의 추천 버튼은 항상 "지금 할 일"을 맨 위에 강조해, 그 버튼만 누르면 자연스럽게 다음으로 흐릅니다.

## 기술 스택
- LangGraph + LangChain (에이전트 그래프, tool calling)
- OpenAI `gpt-4.1-nano` (모델은 `llm.py` 의 `MODEL_PROVIDER` 로 교체 가능)
- Streamlit (UI + Community Cloud 배포)

## UI
- 화이트 톤 본문에 오렌지 ~ 레드 그라데이션 브랜드 배너, 제목 옆 흰색 로고.
- 배너 안에 1~5단계 가로 스텝퍼 (현재 단계로 흐르는 점선 애니메이션).
- 2단 레이아웃: 왼쪽은 채팅(말풍선 + 추천 액션 버튼), 오른쪽은 점검 환경을 실제 명령으로 비추는 셸 터미널.
- 정보 입력을 마치면 터미널에 환영 인사가 뜹니다.

## 로컬 실행
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # OPENAI_API_KEY 입력
streamlit run streamlit_app.py
```

## 배포 (Streamlit Community Cloud)
1. 이 레포를 GitHub 에 올린다 (공개). 키는 절대 커밋하지 않는다(`.gitignore` 로 제외).
2. share.streamlit.io 에서 레포를 연결하고 `streamlit_app.py` 를 진입점으로 지정한다.
3. Advanced settings 의 Secrets 에 `OPENAI_API_KEY` 를 넣는다 (레포가 아닌 Secrets 에만 둔다).
4. 배포된 공개 URL 로 외부 기기에서 접속을 확인한다.

## AI Native 개발 노트
- 정책을 markdown(`CLAUDE.md`, `policies/developer/*.md`)으로 관리하고 에이전트가 출처로 읽는 구조 자체가 AI Native 설계입니다.
- 이 프로젝트는 AI 협업(Claude Code)으로 빌드했습니다.

## 설계 경계 (정직한 스코핑)
- 환경 점검의 실제 대상은 에이전트(앱)가 도는 서버입니다. 모의 데이터를 읽는 것이 아니라 그 서버에서 명령을 실제로 실행합니다.
- 접속자 본인 PC 는 점검하지 않습니다. 브라우저 보안상 웹앱이 사용자의 로컬 머신에서 명령을 실행할 수 없기 때문입니다.
- 운영 전환 시에는 에이전트를 신입의 실제 개발 환경에 배포하거나 MCP 로 점검 범위를 확장해, 신입 본인 환경을 직접 점검하도록 설계합니다.
