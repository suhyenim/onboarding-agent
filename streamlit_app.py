"""온보딩 에이전트 - Streamlit 채팅 UI.

UI 설계는 제출 양식을 역설계했다. 한 화면 캡처에 다음이 함께 보이도록 한다.
- 상단: 온보딩 여정 SVG 스텝퍼 + 효과 지표
- 왼쪽: 채팅 (도구 호출 가시화, 단순 RAG 챗봇이 아님을 증명)
- 오른쪽: 점검 대상 환경을 실제 명령으로 비추는 셸 터미널 (모의 데이터 아님)

세션 격리: thread_id 와 progress 를 st.session_state 로 관리한다.
Streamlit 은 단일 프로세스에서 여러 세션을 처리하므로, 전역 상태를 쓰면 사용자끼리 섞인다.
"""
import base64
import os
import re
import time
import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

# Streamlit Secrets -> 환경변수 (키는 레포가 아닌 Secrets에만 둔다)
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

from agent import build_graph  # noqa: E402  (키 주입 후 import)
from tools import (  # noqa: E402
    get_progress,
    run_env_checks,
    set_progress,
    set_role,
    welcome_ascii,
)

# 1단계는 정보 입력(인테이크), 2~5단계는 환경 점검.
PHASE_LABELS = {
    1: "정보 입력 (이름/사번/팀)",
    2: "사전 준비 (계정/권한)",
    3: "로컬 개발환경 (CLI/SDK/.env)",
    4: "AI 개발 스택 (모델/레포/정책)",
    5: "빌드/배포 파이프라인",
}
SHORT_LABELS = {1: "정보 입력", 2: "사전 준비", 3: "로컬 환경", 4: "AI 스택", 5: "빌드/배포"}
FIRST_CHECK_PHASE = 2  # 환경 점검이 시작되는 단계 (1단계는 정보 입력)
STEPS_NEED_PROGRESS = {4}  # 설치/동작이 실제로 필요해 '진행하기' 버튼을 끼우는 단계 (AI 스택)
SK_RED = "#EA002C"
SK_ORANGE = "#FF7A00"  # 색상은 SK Orange ~ SK Red ~ Gray 범주 안에서만 쓴다
MASCOT = "assets/agent-mascot.png"
LOGO = "assets/logo.png"
LOGO2 = "assets/logo2.png"
FAVICON = "assets/favicon.png"

# 직무는 AX 개발자로 통일한다 (AI 앱/에이전트를 만드는 개발자의 개발환경 온보딩).
ROLE = "developer"
ROLE_LABEL = "AX 개발자"

st.set_page_config(page_title="SK 온보딩 에이전트", page_icon=LOGO, layout="wide")

# ---------------- 브랜드 스타일 (SK Red 액센트, 화이트 톤, 큰 글씨) ----------------
st.markdown(
    f"""
    <style>
      .stApp {{ background-color: #FFFFFF; font-size: 17px; }}
      .stApp p, .stApp li, .stApp label {{ font-size: 17px; }}
      .stApp h4 {{ font-size: 22px; }}
      .stApp [data-testid="stChatMessageContent"] {{ font-size: 17px; }}
      .stApp [data-testid="stMetricValue"] {{ font-size: 28px; }}
      .stApp [data-testid="stMetricLabel"] {{ font-size: 15px; }}
      .stButton button {{ font-size: 16px; padding: 8px 14px; border-radius: 8px; }}
      .brand-banner {{
        background: linear-gradient(110deg, {SK_ORANGE} 0%, {SK_RED} 100%);
        color: #FFFFFF; padding: 24px 30px; border-radius: 14px;
        box-shadow: 0 6px 18px rgba(234,0,44,0.18);
        margin-bottom: 22px;
        display: flex; align-items: center; gap: 28px;
      }}
      .banner-left {{ flex: 0 0 44%; }}
      .banner-right {{ flex: 1 1 56%; }}
      .brand-banner h1 {{
        margin: 0; font-size: 34px; font-weight: 800; color:#FFFFFF;
        display: flex; align-items: center; gap: 12px;
      }}
      .banner-logo2 {{
        height: 34px; flex: 0 0 auto; margin-left: 14px;
        filter: brightness(0) invert(1);  /* 로고 모양은 유지하고 색만 흰색으로 */
      }}
      .banner-who {{ margin: 10px 0 0; font-size: 21px; font-weight: 700; opacity: 0.96; }}
      .brand-banner p  {{ margin: 12px 0 0; font-size: 17px; line-height: 1.55; opacity: 0.97; }}

      /* 채팅 말풍선: 에이전트=왼쪽 회색, 사용자=오른쪽 오렌지 */
      [data-testid="stChatMessage"] {{ background: transparent; padding: 2px 0; }}
      [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {{
        background:#F1F2F4; color:#1A1A1A; padding:12px 16px; border-radius:16px;
        border-top-left-radius:4px; box-shadow:0 1px 2px rgba(0,0,0,0.06);
        display:inline-block; max-width:92%;
      }}
      /* 사용자 메시지(마지막 자식이 user avatar인 행)는 오른쪽 정렬 + 오렌지 버블 */
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
        flex-direction: row-reverse;
      }}
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {{
        background:#E4E6EA; color:#1A1A1A;
        border-radius:16px; border-top-right-radius:4px; border-top-left-radius:16px;
      }}
      .brand-chip {{
        display:inline-block; background: rgba(255,255,255,0.18); color:#fff;
        padding: 3px 12px; border-radius: 999px; font-size: 13px; margin-top: 10px;
      }}
      .term {{
        background:#1A1A1A; border-radius:12px; padding:14px 16px; margin:6px 0 14px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size:15px; line-height:1.7; color:#D7D7D7; border:1px solid #2E2E2E;
      }}
      .term .bar {{ color:#9A9A9A; font-size:12px; margin-bottom:10px; }}
      .term .dot {{ height:10px; width:10px; border-radius:50%; display:inline-block; margin-right:5px; }}
      .term .note {{ color:#9A9A9A; font-size:13px; margin-top:9px; }}
      .term .note::before {{ content:"# "; color:#6E6E6E; }}
      .term .cmd {{ color:{SK_ORANGE}; }}
      .term .cmd::before {{ content:"$ "; color:#7A7A7A; }}
      .term .out {{ color:#C7C7C7; }}
      .term .ok {{ color:#E8A33D; font-weight:700; }}
      .term .bad {{ color:{SK_RED}; font-weight:700; }}
      .term .run {{ background:rgba(255,122,0,0.08); border-radius:6px; }}
      .term .sec {{ color:{SK_ORANGE}; margin-top:12px; font-weight:700; }}
      .term .ascii {{
        color:{SK_ORANGE}; background:transparent; border:0; margin:0 0 8px; padding:0;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size:11px; line-height:1.2; white-space:pre; overflow-x:auto;
        display:block;
      }}
      .term .cursor {{
        display:inline-block; width:9px; height:17px; background:{SK_ORANGE};
        vertical-align:middle; margin-left:3px; animation: blink 1.1s steps(1) infinite;
      }}
      @keyframes blink {{ 50% {{ opacity:0; }} }}
    </style>
    """,
    unsafe_allow_html=True,
)


def stepper_svg():
    """온보딩 여정(Phase 1~4)을 SVG 스텝퍼 문자열로 만든다.

    빨간 브랜드 박스 안에 얹히므로, 색은 흰색 계열 대비로 그린다.
    (통과=흰 채움 + 빨간 체크, 현재=흰 테두리 강조, 미래=반투명 흰 테두리)
    """
    progress = st.session_state.progress
    phases = list(PHASE_LABELS)  # [1,2,3,4]
    passed = [p for p in phases if progress.get(p) == "pass"]
    cur = (max(passed) + 1) if passed else phases[0]  # 다음 진행할 단계

    n = len(phases)
    W, H, r, cy = 820, 116, 21, 34
    gap = W / n
    svg = [f"<svg viewBox='0 0 {W} {H}' width='100%' height='{H}' role='img'>"]

    for i in range(1, n):  # 연결선: 통과=흰 실선, 현재로 향하는 선=흐르는 점선
        x1, x2 = gap * (i - 0.5), gap * (i + 0.5)
        prev_p, next_p = phases[i - 1], phases[i]
        done = progress.get(prev_p) == "pass"
        flowing = done and next_p == cur  # 직전 통과 + 다음이 현재 단계면 "흐름" 연출
        if flowing:
            # 바탕 흰 선 위에 점선이 왼->오로 흐르는 효과 (다음 단계로 진행 중임을 표현)
            svg.append(f"<line x1='{x1:.0f}' y1='{cy}' x2='{x2:.0f}' y2='{cy}' stroke='rgba(255,255,255,0.35)' stroke-width='3'/>")
            svg.append(
                f"<line x1='{x1:.0f}' y1='{cy}' x2='{x2:.0f}' y2='{cy}' stroke='#FFFFFF' stroke-width='3' "
                f"stroke-linecap='round' stroke-dasharray='2 10'>"
                f"<animate attributeName='stroke-dashoffset' from='24' to='0' dur='0.9s' repeatCount='indefinite'/>"
                f"</line>"
            )
        else:
            color = "#FFFFFF" if done else "rgba(255,255,255,0.35)"
            svg.append(f"<line x1='{x1:.0f}' y1='{cy}' x2='{x2:.0f}' y2='{cy}' stroke='{color}' stroke-width='3'/>")

    for i, p in enumerate(phases):  # 노드 + 라벨
        cx = gap * (i + 0.5)
        st_ = progress.get(p)
        if st_ == "pass":
            fill, txt, mark, stroke = "#FFFFFF", SK_RED, "✓", "none"
        elif st_ == "fail":
            fill, txt, mark, stroke = "#FFFFFF", SK_ORANGE, "!", "none"
        elif p == cur:
            fill, txt, mark, stroke = "rgba(255,255,255,0.18)", "#FFFFFF", str(p), "#FFFFFF"
        else:
            fill, txt, mark, stroke = "rgba(255,255,255,0.0)", "rgba(255,255,255,0.7)", str(p), "rgba(255,255,255,0.5)"
        if p == cur:
            svg.append(f"<circle cx='{cx:.0f}' cy='{cy}' r='{r + 4}' fill='none' stroke='#FFFFFF' stroke-opacity='0.45' stroke-width='2'/>")
        svg.append(
            f"<circle cx='{cx:.0f}' cy='{cy}' r='{r}' fill='{fill}' stroke='{stroke}' stroke-width='2'/>"
            f"<text x='{cx:.0f}' y='{cy + 6}' text-anchor='middle' fill='{txt}' font-size='18' font-weight='700'>{mark}</text>"
        )
        svg.append(
            f"<text x='{cx:.0f}' y='82' text-anchor='middle' fill='#FFFFFF' font-size='16' font-weight='700'>{p}단계</text>"
            f"<text x='{cx:.0f}' y='102' text-anchor='middle' fill='rgba(255,255,255,0.85)' font-size='14'>{SHORT_LABELS[p]}</text>"
        )
    svg.append("</svg>")
    return "".join(svg)


def _esc(s):
    return (s or "").replace("<", "&lt;").replace(">", "&gt;")


def _term_line(cmd, out, ok, run=False, desc=None):
    """터미널 한 명령의 줄을 HTML로 만든다.

    desc(한국어 설명)가 있으면 명령 위에 '# ...' 주석으로 띄워, 이 명령이
    지금 무슨 일을 하는지 신입이 바로 이해하게 한다. 에이전트가 직접 치는 느낌.
    """
    mark = "<span class='ok'>OK</span>" if ok else "<span class='bad'>FAIL</span>"
    cls = "run" if run else ""
    note = f"<div class='note'>{_esc(desc)}</div>" if desc else ""
    return (
        f"{note}"
        f"<div class='{cls}'><span class='cmd'>{_esc(cmd)}</span></div>"
        f"<div class='{cls}'>&nbsp;&nbsp;<span class='out'>{_esc(out)}</span> &nbsp;{mark}</div>"
    )


_TERM_BAR = (
    "<div class='bar'>"
    "<span class='dot' style='background:#FF5F56'></span>"
    "<span class='dot' style='background:#FFBD2E'></span>"
    "<span class='dot' style='background:#27C93F'></span>"
    "&nbsp; 온보딩 에이전트가 직접 입력하는 개발 환경</div>"
)


def _term_head():
    """터미널 상단(타이틀 바 + 환영 ASCII)을 만든다. 프로필 있으면 환영 포함."""
    name = st.session_state.profile["name"] if st.session_state.profile else None
    head = _TERM_BAR
    if name and st.session_state.welcome_shown:
        head += f"<pre class='ascii'>{_esc(welcome_ascii(name))}</pre>"
    return head


def _term_wrap(inner):
    return f"<div class='term'>{inner}</div>"


_CURSOR = "<div><span class='cursor'></span></div>"


def render_env_terminal_to(slot, active_phase=None):
    """터미널을 placeholder(slot)에 정적으로 그린다 (rerun 후 최종 상태 표시용).

    active_phase 가 있으면 그 단계 점검 결과를 한 번에 보여준다.
    라이브 타이핑 연출은 play_phase_check 가 담당한다.
    """
    name = st.session_state.profile["name"] if st.session_state.profile else None
    body = _term_head()
    if active_phase is None:
        if name:
            body += "<div class='note'>준비되면 채팅에서 '2단계 검증해줘'라고 해 주세요. 그때 제가 여기에 직접 확인 명령을 입력할게요.</div>"
    else:
        body += f"<div class='sec'># {active_phase}단계 환경을 직접 확인할게요</div>"
        for c in run_env_checks(active_phase):
            body += _term_line(c["cmd"], c["out"], c["ok"], run=True, desc=c.get("desc"))
    slot.markdown(_term_wrap(body + _CURSOR), unsafe_allow_html=True)


def play_phase_check(slot, phase):
    """에이전트가 그 단계 점검 명령을 터미널에 '직접 쳐 넣는' 모습을 한 줄씩 연출한다.

    slot 은 터미널 자리(st.empty()). 명령마다 설명 -> 명령 -> 결과 순으로 쌓으며
    짧은 딜레이를 줘서, 사용자가 자연어로 부탁한 일이 실제 명령으로 실행되는 흐름을 보게 한다.
    """
    body = _term_head()
    body += f"<div class='sec'># {phase}단계 환경을 직접 확인할게요</div>"
    slot.markdown(_term_wrap(body + _CURSOR), unsafe_allow_html=True)
    time.sleep(0.35)
    for c in run_env_checks(phase):
        # 1) 무슨 일을 하는지 설명 + 명령이 쳐지는 줄 (결과 전)
        body += (f"<div class='note'>{_esc(c.get('desc'))}</div>"
                 f"<div class='run'><span class='cmd'>{_esc(c['cmd'])}</span></div>")
        slot.markdown(_term_wrap(body + _CURSOR), unsafe_allow_html=True)
        time.sleep(0.45)
        # 2) 실행 결과 줄
        mark = "<span class='ok'>OK</span>" if c["ok"] else "<span class='bad'>FAIL</span>"
        body += f"<div class='run'>&nbsp;&nbsp;<span class='out'>{_esc(c['out'])}</span> &nbsp;{mark}</div>"
        slot.markdown(_term_wrap(body + _CURSOR), unsafe_allow_html=True)
        time.sleep(0.25)


def next_actions():
    """현재 진행 상태 기준으로 다음 액션 버튼을 만든다.

    반환: [(표시라벨, primary여부, 전송문구), ...]. primary=True 인 첫 버튼이 '지금 할 일'.
    표시라벨은 친근하게, 전송문구는 LLM 이 도구를 확실히 호출하도록 'N단계 설명해줘/검증해줘'
    형태로 분리한다. ('뭐 하는지' 같은 모호한 문구는 nano 가 도구 호출을 건너뛴다.)
    """
    progress = st.session_state.progress
    passed = [p for p in PHASE_LABELS if progress.get(p) == "pass"]
    cur = (max(passed) + 1) if passed else FIRST_CHECK_PHASE
    if cur < FIRST_CHECK_PHASE:
        cur = FIRST_CHECK_PHASE

    if cur > max(PHASE_LABELS):  # 2~5 전부 통과 (온보딩 완료)
        return [("처음부터 다시 둘러보기", False, "처음부터 다시 알려줘"),
                ("진행 상황 보기", False, "진행 상황 알려줘")]

    label = SHORT_LABELS[cur]
    if progress.get(cur) == "fail":
        # 직전 점검 실패: 해결 먼저(빨강) -> 재점검
        return [
            (f"{cur}단계, 뭐가 막혔는지 알려줘", True, f"{cur}단계 실패 원인과 해결 방법 알려줘"),
            (f"{cur}단계 다시 점검하기", False, f"{cur}단계 검증해줘"),
            ("진행 상황 보기", False, "진행 상황 알려줘"),
        ]

    # 아직 통과 전. 사용자는 '맨 위(빨강) 버튼'만 누르면 자연스럽게 다음으로 흐른다.
    # 흐름: 설명 듣기 -> (설치/동작 필요한 단계만) 진행하기 -> 검증하기 -> [통과 시 다음 단계로 자동]
    explained = st.session_state.get("last_intent") == ("explain", cur)
    explain_btn = (f"{cur}단계 ({label}) 설명 듣기", f"{cur}단계 설명해줘")
    progress_btn = (f"{cur}단계 설치/설정 어떻게 하는지 알려줘", f"{cur}단계 설치하고 설정하는 방법 알려줘")
    verify_btn = (f"준비됐어요, {cur}단계 점검하기", f"{cur}단계 검증해줘")
    status_btn = ("진행 상황 보기", "진행 상황 알려줘")

    # 설치/동작이 실제로 필요한 단계에는 '진행하기'를 끼운다 (예: AI 스택 설치).
    if cur in STEPS_NEED_PROGRESS:
        ordered = [explain_btn, progress_btn, verify_btn, status_btn]
    else:
        ordered = [explain_btn, verify_btn, status_btn]

    # '지금 할 일'을 맨 위 + 빨강으로. 설명을 보냈으면 그 다음 버튼이 지금 할 일이 된다.
    cur_idx = 1 if explained and len(ordered) > 1 else 0
    out = []
    for i, (lbl, send) in enumerate(ordered):
        out.append((lbl, i == cur_idx, send))
    # 맨 위가 지금 할 일이 되도록 재정렬 (빨강 버튼을 가장 위로)
    out.sort(key=lambda x: (not x[1]))
    return out


# ---------------- 프로필 채팅 입력(인테이크) ----------------
# 별도 입력 폼이 아니라, 첫 화면부터 에이전트가 채팅으로 신입 정보를 물어 받는다.
# 직무는 AX 개발자로 고정이라 따로 묻지 않는다. 톤은 담백한 존댓말(토스/당근 결).
INTAKE_PROMPTS = {
    "name": "반가워요. AX 개발자 온보딩을 같이 할 에이전트예요.\n시작하기 전에 몇 가지만 받을게요. 성함이 어떻게 되세요?",
    "emp_no": "{name}님, 반가워요. 사번을 알려주세요.\nSK 뒤에 숫자 8자리예요. (예: SK00000000)",
    "team": "어느 팀이세요? 팀명을 알려주세요. (예: AX플랫폼팀)",
}
EMP_NO_RE = re.compile(r"^SK\d{8}$", re.IGNORECASE)


def intake_question():
    """현재 인테이크 단계의 질문 문구를 반환한다."""
    step = st.session_state.intake_step
    return INTAKE_PROMPTS[step].format(**st.session_state.intake)


def handle_intake(user_text):
    """프로필 채팅 입력 한 턴을 처리한다. 검증 실패 시 재질문, 성공 시 다음 단계로.

    이름 -> 사번(SK+8자리) -> 팀명 순서로 받고, 팀명까지 받으면 프로필을 확정한다.
    직무는 AX 개발자 고정이라 묻지 않는다.
    반환: 에이전트가 이어서 할 응답 문구.
    """
    step = st.session_state.intake_step
    text = (user_text or "").strip()

    if step == "name":
        if not text:
            return "성함이 비어 있어요. 한 번만 더 알려주세요."
        st.session_state.intake["name"] = text
        st.session_state.intake_step = "emp_no"
        return intake_question()

    if step == "emp_no":
        normalized = text.upper().replace(" ", "").replace("-", "")
        if not EMP_NO_RE.match(normalized):
            return ("사번 형식이 조금 달라요. SK 뒤에 숫자 8자리로 부탁드려요. "
                    "(예: SK00000000)")
        st.session_state.intake["emp_no"] = normalized
        st.session_state.intake_step = "team"
        return intake_question()

    if step == "team":
        if not text:
            return "팀명이 비어 있어요. 소속 팀명을 알려주세요."
        st.session_state.intake["team"] = text
        finish_intake()
        p = st.session_state.profile
        return (f"좋아요. {p['name']}님 ({p['emp_no']} / {p['team']} / {ROLE_LABEL}) 확인했어요. 1단계 완료예요!\n"
                f"오른쪽에 환영 인사를 띄워 뒀어요. 이제 천천히 같이 시작해 봐요.\n"
                f"먼저 '2단계 설명해줘'라고 해 주시면, 다음 단계가 뭔지 쉽게 알려드릴게요.")

    return intake_question()


def finish_intake():
    """팀명까지 받으면 프로필을 확정한다.

    1단계(정보 입력)는 입력 완료가 곧 통과이므로 progress[1]="pass" 로 표시한다.
    이래야 스텝퍼가 1단계 완료 -> 2단계 진행 중으로 흐르고, 2단계 검증도 열린다.
    """
    st.session_state.intake["role"] = ROLE
    st.session_state.profile = dict(st.session_state.intake)
    st.session_state.intake_step = "done"
    st.session_state.welcome_shown = True
    st.session_state.progress[1] = "pass"  # 1단계: 입력 완료 = 통과


@st.cache_data
def img_data_uri(path):
    """이미지를 base64 data URI 로 인코딩한다 (배너 HTML 안에 인라인으로 박기 위함)."""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


@st.cache_resource
def get_graph():
    return build_graph()


# ---------------- 세션 상태 초기화 ----------------
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []  # 렌더링 전용 (LLM 입력은 체크포인터가 관리)
if "progress" not in st.session_state:
    st.session_state.progress = {}  # {phase: "pass"|"fail"}
if "active_phase" not in st.session_state:
    st.session_state.active_phase = None
if "profile" not in st.session_state:
    st.session_state.profile = None  # {"name", "emp_no", "team", "role"}
if "intake_step" not in st.session_state:
    st.session_state.intake_step = "name"  # name -> emp_no -> team -> done
if "intake" not in st.session_state:
    st.session_state.intake = {}  # 입력 누적 버퍼
if "welcome_shown" not in st.session_state:
    st.session_state.welcome_shown = False  # 터미널 환영 ASCII 표시 여부
if "last_intent" not in st.session_state:
    st.session_state.last_intent = None  # 방금 보낸 의도 ("explain"|"verify", 단계) - 버튼 위계용

# ---------------- 본문 ----------------
intake_active = st.session_state.profile is None  # 프로필 확정 전이면 인테이크 모드

who = ""
if st.session_state.profile:
    p = st.session_state.profile
    team = p.get("team") or ROLE_LABEL
    who = f"<div class='banner-who'>{p['name']}님 | {team}</div>"
# 빨간 박스: 왼쪽=마스코트(제목 앞 인라인)+제목+(이름 줄)+부제, 오른쪽=1~5단계 가로 스텝퍼.
# 스텝퍼는 인테이크 중에도 보여준다 (정보 입력이 1단계라 첫 화면부터 흐른다).
# HTML 은 들여쓰기/빈 줄 없이 한 줄로 둔다.
# (Streamlit 마크다운은 4칸 이상 들여쓴 라인을 코드블록으로 오인해 태그를 그대로 노출시킨다.)
_banner_html = (
    '<div class="brand-banner">'
    '<div class="banner-left">'
    f'<h1>SK 온보딩 에이전트<img class="banner-logo2" src="{img_data_uri(LOGO2)}" alt="" /></h1>'
    f'{who}'
    '<p>AX 개발자 첫 출근, 개발 환경 세팅을 단계별로 안내해 드려요.<br/>'
    '필요한 준비를 설명하고, 환경이 제대로 갖춰졌는지 직접 확인까지 해 드려요.</p>'
    '</div>'
    f'<div class="banner-right">{stepper_svg()}</div>'
    '</div>'
)
st.markdown(_banner_html, unsafe_allow_html=True)

# 첫 진입 시: 인테이크 첫 질문을 대화에 미리 넣어, 첫 화면부터 채팅으로 정보를 받는다.
if not st.session_state.messages and st.session_state.intake_step == "name":
    st.session_state.messages.append(
        {"role": "assistant", "content": intake_question(), "tool_logs": []}
    )

# 화면 가로 비율 고정 (채팅 35 : 터미널 65)
chat_ratio = 35


def run_agent(user_text: str, term_slot=None):
    """에이전트를 호출한다. 도구 호출을 화면에 가시화하고, 로그/최종답변/진행률을 반환한다."""
    graph = get_graph()
    config = RunnableConfig(configurable={"thread_id": st.session_state.thread_id})

    # 이 세션의 직무/진행 상태를 도구에 주입 (직무는 AX 개발자 고정)
    set_role(ROLE)
    set_progress(st.session_state.progress)

    final_text = ""
    tool_logs = []            # rerun 후에도 도구 가시화를 보존하기 위해 텍스트로 적재
    last_verify_phase = None  # 터미널 반영용: 방금 점검한 Phase
    for event in graph.stream({"messages": [HumanMessage(content=user_text)]}, config):
        for _node, value in event.items():
            for m in value["messages"]:
                if isinstance(m, AIMessage):
                    for tc in m.tool_calls or []:
                        arg0 = str(list(tc["args"].values())[0]) if tc["args"] else ""
                        mm = re.search(r"[2-5]", arg0)
                        if tc["name"] == "verify_environment" and mm:
                            last_verify_phase = int(mm.group())
                            # 에이전트가 그 단계 점검 명령을 터미널에 직접 쳐 넣는 모습을 연출
                            if term_slot is not None:
                                play_phase_check(term_slot, last_verify_phase)
                    if m.content:
                        final_text = m.content

    if final_text:
        st.markdown(final_text)

    before = dict(st.session_state.progress)
    st.session_state.progress = get_progress()
    if last_verify_phase is not None:
        st.session_state.active_phase = last_verify_phase
    # 이번 턴에 새로 통과한 Phase가 있으면 알린다 (채팅에 축하 구분선/카드용)
    newly_passed = None
    if last_verify_phase is not None:
        p = last_verify_phase
        if st.session_state.progress.get(p) == "pass" and before.get(p) != "pass":
            newly_passed = p
            # 단계를 통과했으면 의도 초기화 -> 다음 단계는 다시 '설명'부터 강조
            st.session_state.last_intent = None
    return final_text, tool_logs, newly_passed


# 2단 레이아웃: 왼쪽 채팅 / 오른쪽 실제 셸 터미널
col_chat, col_term = st.columns([chat_ratio, 100 - chat_ratio], gap="medium")

# 터미널을 먼저 만들어 placeholder(term_slot)를 확보한다.
# 이래야 채팅에서 에이전트가 도구를 호출하는 순간, 그 명령이 터미널에 실시간으로 쳐진다.
with col_term:
    st.markdown("#### 🖥️ 실제 실행 환경")
    term_slot = st.empty()
    render_env_terminal_to(term_slot, active_phase=st.session_state.active_phase)

with col_chat:
    st.markdown("#### 💬 온보딩 대화")
    clicked = None

    # 대화 히스토리는 고정 높이 영역 안에서 스크롤된다 (길어져도 화면을 밀지 않음)
    history = st.container(height=560)
    with history:
        last_idx = len(st.session_state.messages) - 1
        for idx, msg in enumerate(st.session_state.messages):
            avatar = MASCOT if msg["role"] == "assistant" else None
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])
                # 마지막 에이전트 말풍선 바로 밑에 추천 액션을 가로로 긴 버튼(세로 스택)으로 제시
                # 첫 버튼(primary)이 '지금 할 일'이라 강조색으로 띄워, 뭘 누를지 헷갈리지 않게 한다.
                if not intake_active and msg["role"] == "assistant" and idx == last_idx:
                    st.caption("👇 지금 이걸 누르면 돼요")
                    for i, (label_txt, primary, send_txt) in enumerate(next_actions()):
                        if st.button(
                            label_txt,
                            use_container_width=True,
                            type="primary" if primary else "secondary",
                            key=f"act_{idx}_{i}",
                        ):
                            clicked = send_txt  # 화면 라벨과 달리, LLM 엔 명확한 명령형을 보낸다

    prompt = st.chat_input(" ") or clicked

    if prompt:
        # 방금 보낸 의도를 즉시 기록 -> 버튼 위계가 LLM 응답을 기다리지 않고 바로 바뀐다.
        m_phase = re.search(r"([2-5])\s*단계", prompt)
        if m_phase:
            ph = int(m_phase.group(1))
            if "설명" in prompt:
                st.session_state.last_intent = ("explain", ph)
            elif "검증" in prompt or "점검" in prompt:
                st.session_state.last_intent = ("verify", ph)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with history:
            with st.chat_message("user"):
                st.markdown(prompt)

        if st.session_state.profile is None:
            # 인테이크 모드: 자연어 대화로 이름/사번/팀명을 받는다 (LLM 없이 즉답)
            reply = handle_intake(prompt)
            with history:
                with st.chat_message("assistant", avatar=MASCOT):
                    st.markdown(reply)
            st.session_state.messages.append(
                {"role": "assistant", "content": reply, "tool_logs": []}
            )
        else:
            # 온보딩 모드: 에이전트가 응답하고, 점검 도구를 부르면 터미널(term_slot)에 명령을 직접 친다
            with history:
                with st.chat_message("assistant", avatar=MASCOT):
                    answer, logs, newly_passed = run_agent(prompt, term_slot=term_slot)
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "tool_logs": logs}
            )
            # 단계 통과 시: 축하 구분선 + 다음 단계 안내 카드를 대화에 남긴다
            if newly_passed is not None:
                nxt = newly_passed + 1
                if nxt in PHASE_LABELS:
                    card = (f"---\n\n**🎉 {newly_passed}단계 완료!** {SHORT_LABELS[newly_passed]} 끝냈어요.\n\n"
                            f"다음은 **{nxt}단계 ({SHORT_LABELS[nxt]})** 예요. '{nxt}단계 설명해줘'로 이어가요.")
                else:
                    card = (f"---\n\n**🎉 {newly_passed}단계 완료!** 온보딩 5단계를 전부 끝냈어요. "
                            f"수고하셨어요. 이제 진짜 첫 작업을 시작하면 돼요.")
                st.session_state.messages.append(
                    {"role": "assistant", "content": card, "tool_logs": []}
                )
        st.rerun()
