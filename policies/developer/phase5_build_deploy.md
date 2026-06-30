# 5단계 - 빌드/배포 (AX 개발자)

## 이 단계는
지금까지 갖춘 환경 위에서 AI 앱을 실제로 띄워 보는 마지막 단계입니다. 우리는 streamlit으로 LLM 앱에 웹 화면을 입혀 사용자가 쓸 수 있는 형태로 만들고, 그 앱을 처음으로 배포(만든 앱을 서버에 올려 누구나 접속해 쓸 수 있게 하는 것)합니다. 여기까지 통과하면 개발 환경 전체가 한 바퀴 돌았다는 뜻입니다.

## 무엇을 준비하나
- streamlit: 파이썬 코드만으로 채팅 화면 같은 웹 화면을 만드는 도구입니다. 화면 디자인을 따로 짜지 않아도 AI 앱을 바로 사람이 쓸 수 있게 해 줍니다.
- streamlit_app.py: 앱의 진입점(앱을 실행할 때 가장 먼저 읽히는) 파일입니다. streamlit이 이 파일을 읽어 화면을 띄우므로, 레포 루트(코드 저장소의 최상위 폴더)에 반드시 있어야 합니다.

```bash
# streamlit 설치와 버전 확인
pip install streamlit
python3 -c "import streamlit; print(streamlit.__version__)"

# 진입점 파일 확인 후 내 PC에서 실행
ls streamlit_app.py
streamlit run streamlit_app.py

# 첫 배포: 변경한 코드를 커밋(변경 내용을 한 묶음으로 기록)하고 올리면(push) 배포가 이어집니다
git add -A && git commit -m "deploy onboarding app" && git push
```

## 검증 항목
- 앱 진입점 존재: 레포 루트에 streamlit_app.py 가 있는지
- streamlit 설치: python3 -c "import streamlit; print(streamlit.__version__)" 가 성공하는지

## 문제 해결 (트러블슈팅)
- streamlit_app.py가 없다고 나오면 레포 루트에 진입점 파일을 두었는지, pwd 로 현재 위치가 레포 루트인지 확인합니다.
- import(라이브러리를 불러오는 명령)가 실패하면 pip install streamlit 으로 설치합니다.
- streamlit run은 되는데 모델 응답이 비면 3단계의 OPENAI_API_KEY가 실행 중인 셸에 들어가 있는지 다시 확인합니다.
- 포트(프로그램이 통신에 쓰는 번호) 충돌로 안 뜨면 streamlit run streamlit_app.py --server.port 8502 처럼 포트를 바꿔 실행합니다.
