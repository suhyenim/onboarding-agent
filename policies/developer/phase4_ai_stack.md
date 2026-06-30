# 4단계 - AI 개발 스택 (AX 개발자)

## 이 단계는
이제 LLM 앱을 실제로 조립하는 스택(앱을 만드는 데 쓰는 도구 묶음)을 확인합니다. langchain은 프롬프트(모델에게 주는 질문/지시문), 모델 호출, 체인(여러 단계를 줄줄이 이어 붙인 처리 흐름)을 정해진 방식으로 엮어 주는 핵심 프레임워크(앱의 뼈대를 미리 짜 둔 틀)이고, CLAUDE.md는 우리 코드가 따라야 하는 정책(가드레일, 해도 되는 일과 안 되는 일을 정해 둔 규칙)의 출처입니다. 둘 다 있어야 일관된 AI 앱을 만들 수 있습니다.

## 무엇을 준비하나
- langchain: LLM 앱의 뼈대입니다. 프롬프트를 모델에 넘기고 응답을 다음 단계로 흘려보내는 체인을, 매번 직접 짜지 않고 미리 만들어진 부품으로 구성합니다. 3단계의 langgraph가 흐름이라면 langchain은 그 흐름을 채우는 부품입니다.
- CLAUDE.md: 추측 금지, read-only(읽기만 하고 환경을 바꾸지 않음) 우선 같은 에이전트 행동 규칙이 적힌 문서입니다. 개발자는 코드를 짜기 전 이 정책을 읽고, 코드가 정책을 벗어나지 않게 맞춥니다.

```bash
# langchain 설치와 버전 확인
pip install langchain
python3 -c "import langchain; print(langchain.__version__)"

# 정책 문서가 레포 루트에 있는지 확인하고 읽어 두기
ls CLAUDE.md
cat CLAUDE.md
```

## 검증 항목
- langchain 버전 확인: python3 -c "import langchain; print(langchain.__version__)" 가 성공하는지
- 정책 파일(CLAUDE.md) 존재: 레포 루트에 CLAUDE.md 가 있는지

## 문제 해결 (트러블슈팅)
- import(라이브러리를 불러오는 명령)가 실패하면 pip install langchain 으로 설치한 뒤 다시 확인합니다.
- 버전이 너무 낮아 동작이 다르면 pip install -U langchain 으로 올립니다.
- CLAUDE.md가 없다고 나오면 레포(코드를 모아 둔 저장소) 루트(최상위 폴더)에 CLAUDE.md 를 두었는지 확인합니다. 폴더를 잘못 들어와 있을 수도 있으니 pwd 로 위치부터 봅니다.
