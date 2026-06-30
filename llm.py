"""LLM 추상화 레이어.

MODEL_PROVIDER 환경변수 한 줄로 모델을 교체한다.
데모: OpenAI gpt-4.1-nano (최저가, function calling 지원).
운영 전환 시: 같은 인터페이스로 사내/온프레 모델로 교체 (교체 포인트만 설계).
"""
import os

from langchain_openai import ChatOpenAI


def get_llm():
    """현재 설정된 provider의 LLM 인스턴스를 반환한다."""
    provider = os.getenv("MODEL_PROVIDER", "openai")

    if provider == "openai":
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-nano"),
            temperature=0,
        )

    # 운영 전환 포인트: 사내/온프레 모델 provider를 여기 추가.
    raise ValueError(f"지원하지 않는 MODEL_PROVIDER: {provider}")
