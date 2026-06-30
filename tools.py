"""에이전트 도구 3종 + 실제 셸 점검 엔진.

설계 원칙(CLAUDE.md):
- read_policy: 값은 정책 파일에서 실시간으로 읽는다 (추측 금지).
- verify_environment: 모의 데이터가 아니라 앱이 도는 리눅스 환경에서 실제 명령을
  subprocess 로 실행하고 그 결과로 pass/fail 을 판정한다 (진짜 작동 입증).
- record_progress: 검증을 통과한 Phase 기준으로 진행 상태를 보고한다.

보안: 사용자/LLM 입력은 셸에 들어가지 않는다. 실행 명령은 아래 화이트리스트(CHECKS)에
인자 배열로 고정되어 있고, shell=False 로 실행하며 read-only 명령만 둔다.

진행 상태(PROGRESS)는 세션마다 격리되어야 한다. Streamlit 은 단일 프로세스에서
여러 세션을 처리하므로 streamlit_app.py 가 set_progress/get_progress 로 주입/회수한다.
"""
import os
import re
import shutil
import subprocess

from langchain_core.tools import tool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLICY_DIR = os.path.join(BASE_DIR, "policies")

# 단계 번호 -> 정책 파일명.
# 1단계는 정보 입력(이름/사번/팀, 셸 검증 없음)이라 정책/점검이 없다. 환경 점검은 2~5단계.
PHASE_POLICY = {
    2: "phase2_prereq.md",
    3: "phase3_local_env.md",
    4: "phase4_ai_stack.md",
    5: "phase5_build_deploy.md",
}

# 단계별 실제 점검 항목 (2~5단계. 1단계는 정보 입력이라 점검 없음).
# (라벨, 실행 인자 배열, 통과 판정 함수(rc, out)->bool, 실패 시 해결 명령, 명령 설명)
# desc: 이 명령이 실제로 무슨 행동을 하는지 신입이 이해할 한국어 한 문장.
# 모든 명령은 read-only 이며 화이트리스트로 고정된다.
CHECKS = {
    2: [
        ("작업 디렉토리 접근", ["pwd"], lambda rc, o: rc == 0, "쉘 접근 권한을 확인한다",
         "AI 앱을 만들 작업 폴더의 전체 경로를 출력해서, 셸(명령을 받아 실행해 주는 프로그램)이 정상 응답하는지 확인합니다."),
        ("OS 정보 확인", ["uname", "-s"], lambda rc, o: rc == 0, "리눅스 환경인지 확인한다",
         "AI 앱이 돌아갈 서버의 운영체제 이름을 읽어서 어떤 OS 환경에서 개발/배포하는지 확인합니다."),
    ],
    3: [
        ("Python 3.11 이상", ["python3", "--version"],
         lambda rc, o: rc == 0 and _ver_ge(o, (3, 11)),
         "pyenv install 3.11 && pyenv local 3.11",
         "AI 개발에 쓸 파이썬3 버전을 확인합니다. langgraph/langchain 같은 AI SDK(가져다 쓰는 코드 묶음)가 3.11 이상을 요구합니다."),
        ("git CLI 설치", ["git", "--version"], lambda rc, o: rc == 0,
         "git 공식 설치 가이드로 설치한다",
         "AI 프로젝트 코드의 변경 이력을 관리할 git 이 설치돼 있고 실행되는지 버전을 출력해 확인합니다."),
        ("AI 개발 SDK 설치", ["python3", "-c", "import langgraph, langchain_openai"],
         lambda rc, o: rc == 0, "pip install -r requirements.txt",
         "AI 에이전트를 만드는 핵심 SDK(langgraph, langchain_openai)를 코드가 실제로 불러올 수 있는지 확인합니다."),
        ("OPENAI_API_KEY 설정", ["python3", "-c", "import os,sys; sys.exit(0 if os.getenv('OPENAI_API_KEY') else 1)"],
         lambda rc, o: rc == 0, ".env 또는 Secrets 에 OPENAI_API_KEY 를 설정한다",
         "LLM 모델을 호출할 때 본인임을 증명하는 API 키(OPENAI_API_KEY)가 설정돼 있는지 확인합니다. AI 앱이 모델 응답을 받으려면 꼭 필요합니다. (키 값 자체는 출력하지 않습니다)"),
    ],
    4: [
        ("langchain 버전 확인", ["python3", "-c", "import langchain; print(langchain.__version__)"],
         lambda rc, o: rc == 0, "pip install langchain 으로 설치한다",
         "LLM 호출과 체인(여러 단계를 줄줄이 이어 붙인 처리 흐름)을 엮는 langchain 도구가 설치돼 있는지 버전을 출력해 확인합니다."),
        ("정책 파일(CLAUDE.md) 존재", ["ls", os.path.join(BASE_DIR, "CLAUDE.md")],
         lambda rc, o: rc == 0, "레포 루트에 CLAUDE.md 를 둔다",
         "AI 에이전트가 지켜야 할 규칙(가드레일)을 적어 둔 정책 파일 CLAUDE.md 가 레포에 실제로 있는지 확인합니다."),
    ],
    5: [
        ("앱 진입점 존재", ["ls", os.path.join(BASE_DIR, "streamlit_app.py")],
         lambda rc, o: rc == 0, "레포 루트에 streamlit_app.py 를 둔다",
         "AI 앱을 실행할 때 가장 먼저 읽히는 진입점 파일 streamlit_app.py 가 있는지 확인합니다. 이 파일로 앱을 띄웁니다."),
        ("streamlit 설치", ["python3", "-c", "import streamlit; print(streamlit.__version__)"],
         lambda rc, o: rc == 0, "pip install streamlit 으로 설치한다",
         "AI 앱 화면을 띄울 streamlit 이 설치돼 있는지 버전을 출력해 확인합니다."),
    ],
}

# 진행 상태 {phase: "pass"|"fail"}. 세션마다 set_progress/get_progress 로 격리한다.
_PROGRESS = {}

# 직무는 AX 개발자(developer)로 통일한다. read_policy 가 이 디렉토리에서 정책을 읽는다.
_ROLE = "developer"


def set_progress(progress):
    """현재 요청을 처리하기 전, 호출 세션의 진행 상태를 주입한다."""
    global _PROGRESS
    _PROGRESS = dict(progress or {})


def set_role(role):
    """현재 세션의 직무를 주입한다. 직무는 AX 개발자(developer)로 통일돼 있다."""
    global _ROLE
    _ROLE = "developer"


def get_progress():
    """요청 처리 후 갱신된 진행 상태를 반환한다 (세션에 다시 저장하기 위해)."""
    return dict(_PROGRESS)


def _parse_phase(value):
    """입력 문자열에서 단계 번호(2~5)를 추출한다. 없으면 None.

    1단계는 정보 입력이라 점검 대상이 아니므로 2~5만 인식한다.
    """
    m = re.search(r"[2-5]", str(value))
    return int(m.group()) if m else None


def _ver_ge(output, minimum):
    """버전 문자열(예: 'Python 3.11.7')이 minimum 튜플 이상인지 판정한다."""
    m = re.search(r"(\d+)\.(\d+)", output)
    if not m:
        return False
    return (int(m.group(1)), int(m.group(2))) >= minimum


def _run(args, timeout=8):
    """화이트리스트 명령을 shell=False 로 실제 실행하고 (returncode, 출력)을 반환한다.

    사용자 입력이 args 에 섞이지 않으므로 셸 인젝션 위험이 없다. read-only 명령만 둔다.
    """
    # 실행 파일이 없으면(예: 데모 환경에 git 미설치) 127 로 처리
    if shutil.which(args[0]) is None and not os.path.isabs(args[0]):
        return 127, f"command not found: {args[0]}"
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or p.stderr or "").strip()
        return p.returncode, out
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:  # 실행 불가 시 안전하게 실패 처리
        return 1, f"error: {e}"


def run_env_checks(phase):
    """해당 Phase의 점검 항목을 실제 실행하고 결과 리스트를 반환한다.

    각 항목: {label, cmd, out, ok, fix, desc}. UI 터미널과 도구 모두 이 결과를 사용한다.
    desc 는 이 명령이 무슨 행동을 하는지 신입에게 보여줄 한국어 설명이다.
    """
    results = []
    for label, args, judge, fix, desc in CHECKS.get(phase, []):
        rc, out = _run(args)
        ok = judge(rc, out)
        results.append({
            "label": label,
            "cmd": " ".join(args),
            "out": out if out else "(no output)",
            "ok": ok,
            "fix": fix,
            "desc": desc,
        })
    return results


# 터미널 첫 화면(점검 전)에 보여줄 대표 명령들 (실제 실행).
# 각 항목: (실행 인자 배열, 명령 설명 desc). desc 는 AI 개발 환경 맥락의 한국어 설명.
ENV_TERMINAL_CMDS = [
    (["uname", "-a"], "AI 앱이 돌아갈 이 서버의 OS, 커널(운영체제의 핵심) 버전, 아키텍처(CPU 종류) 정보를 모두 출력합니다."),
    (["python3", "--version"], "AI 개발에 쓸 파이썬3 버전을 출력합니다."),
    (["git", "--version"], "AI 프로젝트 코드의 변경 이력을 관리할 git 설치 여부와 버전을 출력합니다."),
    (["pwd"], "AI 앱을 만들 현재 작업 폴더의 전체 경로를 출력합니다."),
]


def get_env_snapshot():
    """앱이 도는 리눅스 환경을 실제 명령으로 스냅샷한다 (모의 아님).

    각 항목: {cmd, out, ok, desc}. desc 는 각 명령이 무슨 행동을 하는지 한국어 설명이다.
    """
    rows = []
    for args, desc in ENV_TERMINAL_CMDS:
        rc, out = _run(args)
        rows.append({
            "cmd": " ".join(args),
            "out": out if out else "(no output)",
            "ok": rc == 0,
            "desc": desc,
        })
    return rows


def welcome_ascii(name: str) -> str:
    """신입사원 환영용 ASCII 아트 + 환영 문구를 여러 줄 문자열로 반환한다.

    LLM 도구가 아니라 streamlit 터미널 UI(검은 배경 모노스페이스 박스)에 그대로
    출력하기 위한 순수 렌더 헬퍼다. 좁은 터미널에서도 안 깨지도록 폭을 짧게 유지한다.
    백슬래시가 들어가므로 raw string 으로 둔다.
    """
    art = r"""
   _____ _   __
  / ___/| | / /     WELCOME
  \__ \ | |/ /
 ___/ / |   <       SK ONBOARDING
/____/  |_|\_\
"""
    deco = "  *  .  +  .  *  .  +  .  *  ."
    greeting = f"  SK 신입사원 {name}님, 환영합니다 \U0001F389"
    return "\n".join([
        art.strip("\n"),
        "",
        deco,
        greeting,
        deco,
    ])


@tool
def read_policy(topic: str) -> str:
    """온보딩 정책/런북을 출처 파일에서 실시간으로 읽어 반환한다.

    topic 에는 단계 번호(2~5) 또는 '2단계' 같은 문자열을 넣는다.
    (1단계는 정보 입력이라 정책이 없다.)
    값(계정/경로/환경변수명)을 답하기 전에 반드시 이 도구로 출처를 확인한다.
    """
    phase = _parse_phase(topic)
    if phase is None:
        return "정책을 찾으려면 단계 번호(2~5)를 알려주세요."
    fname = PHASE_POLICY[phase]
    path = os.path.join(POLICY_DIR, _ROLE, fname)
    if not os.path.exists(path):
        return f"정책 파일을 찾을 수 없습니다: policies/{fname}"
    with open(path, encoding="utf-8") as f:
        return f"[출처: policies/{_ROLE}/{fname}]\n\n" + f.read()


@tool
def verify_environment(phase: str) -> str:
    """해당 단계의 개발환경을 실제 명령으로 점검하고 결과와 해결 명령을 반환한다.

    모의 데이터가 아니라 앱이 도는 리눅스 환경에서 실제 명령(python3 --version 등)을
    실행한 결과로 판정한다. read-only 화이트리스트 명령만 실행한다.
    phase 에는 2~5 사이의 숫자를 넣는다. (1단계는 정보 입력이라 점검 대상이 아니다.)
    """
    p = _parse_phase(phase)
    if p is None:
        return "점검하려면 단계 번호(2~5)를 알려주세요."

    # 단계 경계 검증 강제: 이전 점검 단계가 모두 pass 여야 현재 단계를 점검할 수 있다.
    # 점검은 2단계부터라 2단계 이전(1단계: 정보 입력)은 검사하지 않는다.
    blocked = [i for i in range(2, p) if _PROGRESS.get(i) != "pass"]
    if blocked:
        nxt = blocked[0]
        return (
            f"[단계 경계 검증] {p}단계는 아직 잠겨 있어요.\n"
            f"먼저 {', '.join(str(i) + '단계' for i in blocked)}를 통과해야 해요.\n"
            f"=> 다음으로 '{nxt}단계 검증해줘' 를 진행해 주세요."
        )

    results = run_env_checks(p)
    lines = [f"[{p}단계 점검] 실제 명령 실행 결과"]
    all_pass = True
    for r in results:
        lines.append(f"    설명: {r['desc']}")
        if r["ok"]:
            lines.append(f"  PASS  {r['label']}  ($ {r['cmd']} -> {r['out']})")
        else:
            all_pass = False
            lines.append(f"  FAIL  {r['label']}  ($ {r['cmd']} -> {r['out']}) -> 해결: {r['fix']}")

    _PROGRESS[p] = "pass" if all_pass else "fail"
    lines.append("")
    lines.append("=> 통과" if all_pass else "=> 미통과 (해결 후 재검증 필요)")
    return "\n".join(lines)


@tool
def record_progress() -> str:
    """현재까지의 단계 진행 상태를 반환한다. 점검을 통과한 단계만 완료로 표시된다."""
    checked = {k: v for k, v in _PROGRESS.items() if k >= 2}  # 점검 대상은 2단계부터
    if not checked:
        return "아직 점검한 단계가 없어요. '2단계 검증해줘' 로 시작해요."
    done = sorted(k for k, v in checked.items() if v == "pass")
    summary = ", ".join(f"{k}단계: {checked[k]}" for k in sorted(checked))
    return f"진행 상태: {summary}\n완료한 단계: {done if done else '없음'} / 점검 단계 2~5 (정보 입력 1단계 제외)"


TOOLS = [read_policy, verify_environment, record_progress]
