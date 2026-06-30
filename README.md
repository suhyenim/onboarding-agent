# 온보딩 에이전트 (Onboarding Agent)

신입 AX 개발자의 AI 개발 인프라 온보딩을 돕는 에이전트입니다.
정책/런북을 출처에서 실시간으로 읽어 가이드하고, Phase별 개발환경 검증을 에이전트가 직접 실행하며, 진행 상황을 추적합니다.

## 무엇이 다른가 (단순 챗봇이 아님)
- 도구를 실제로 호출합니다: `read_policy`, `verify_environment`, `record_progress`.
- 추측하지 않습니다: 계정/경로/환경변수명 같은 값은 `policies/*.md` 에서 매번 읽습니다.
- 검증을 진짜로 실행합니다: 모의 픽스처가 아니라, 앱이 도는 리눅스 환경에서 실제 명령(`python3 --version`, `git --version`, SDK import 체크 등)을 subprocess 로 실행해 결과로 통과/실패를 판정합니다. 화이트리스트로 고정된 read-only 명령만 실행합니다.
- Phase 경계 검증을 강제합니다: 이전 단계를 통과하지 못하면 다음 단계 검증을 코드 레벨에서 막습니다.

## 온보딩 단계
- Phase 0 사전 준비 (계정/권한)
- Phase 1 로컬 개발환경 (CLI/런타임/SDK/.env)
- Phase 2 AI 개발 스택 (모델 연결/레포/정책)
- Phase 3 빌드/배포 파이프라인

## 기술 스택
- LangGraph + LangChain (에이전트 그래프, tool calling)
- OpenAI `gpt-4.1-nano` (모델은 `llm.py` 의 `MODEL_PROVIDER` 한 줄로 교체 가능)
- Streamlit (UI + Community Cloud 배포)

## UI
- 화이트 테마에 SK Red(`#EA002C`) 브랜드 배너와 마스코트(`assets/agent-mascot.png`).
- 온보딩 여정을 보여주는 SVG 스텝퍼(Phase 0~3).
- 2단 레이아웃: 왼쪽은 채팅, 오른쪽은 점검 대상 환경을 실제 명령으로 비추는 셸 터미널.

## 로컬 실행
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # 키 입력
streamlit run streamlit_app.py
```

## 배포 (Streamlit Community Cloud)
1. 이 레포를 GitHub 에 올린다 (공개). 키는 절대 커밋하지 않는다.
2. share.streamlit.io 에서 레포를 연결하고 `streamlit_app.py` 를 진입점으로 지정한다.
3. Advanced settings 의 Secrets 에 `OPENAI_API_KEY` 를 넣는다 (레포가 아닌 Secrets 에만 둔다).
4. 배포된 공개 URL 로 외부에서 접속을 확인한다.

## AI Native 개발 노트
- 정책을 markdown(`CLAUDE.md`, `policies/*.md`)으로 관리하고 에이전트가 출처로 읽는 구조 자체가 AI Native 설계입니다.
- 이 프로젝트는 AI 협업(Claude Code)으로 빌드했습니다.

## 설계 경계 (정직한 스코핑)
- 환경 검증의 실제 점검 대상은 에이전트(앱)가 도는 서버, 즉 리눅스 컨테이너입니다. 모의 데이터를 읽는 것이 아니라 그 서버에서 명령을 실제로 실행합니다.
- 접속자 본인 PC 는 점검하지 않습니다. 브라우저 보안상 웹앱이 사용자의 로컬 머신에서 명령을 실행할 수 없기 때문입니다.
- 운영 전환 시에는 에이전트를 신입의 실제 개발 환경에 배포하거나 MCP 로 점검 범위를 확장해, 신입 본인 환경을 직접 점검하도록 설계합니다.
