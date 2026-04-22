import json
import re

import streamlit as st
from groq import Groq

st.set_page_config(page_title="Firefly Prompt Studio", page_icon="", layout="wide")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are an expert in AI image generation prompts for Adobe Firefly.

Goals when rewriting:
- Lead with the main subject, then setting, lighting, camera/lens feel, materials, and color mood.
- Use concrete nouns and adjectives; avoid vague words like "nice" or "cool" unless you add specifics.
- Match the user's selected USE CASE (tone and composition): social posts favor bold clarity; brand work favors clean, on-brief language; concept art can be more imaginative; photo composite prompts should separate foreground/background when helpful.
- If the user asks for harmful, illegal, sexual, hateful, or IP-infringing content, do not comply. Return issues explaining why, keep rewritten_prompt as a safe, creative alternative that preserves benign intent, and use a low score.

Analyze the user's prompt and return ONLY a JSON object with this exact structure, no other text:
{
  "score": <integer 0-100>,
  "score_breakdown": {"specificity": <0-25>, "style_clarity": <0-25>, "visual_detail": <0-25>, "composition": <0-25>},
  "issues": ["issue 1", "issue 2"],
  "rewritten_prompt": "improved prompt here",
  "explanation": "2 sentences explaining the improvement",
  "variations": [
    {"style": "Photorealistic", "prompt": "photorealistic version"},
    {"style": "Illustration", "prompt": "illustration version"},
    {"style": "Cinematic", "prompt": "cinematic version"}
  ]
}"""


def analyze_prompt(user_prompt: str, style_hint: str = "", use_case: str = "General") -> dict:
    content = f"Analyze this prompt: {user_prompt}\nUSE CASE: {use_case}"
    if style_hint:
        content += f"\nPreferred style: {style_hint}"
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        temperature=0.3,
        max_tokens=1000,
    )
    text = response.choices[0].message.content.strip()
    text = re.sub(r"```json|```", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Model did not return valid JSON.")
    return json.loads(match.group())


def score_color(s: int) -> str:
    return "#1D9E75" if s >= 80 else "#BA7517" if s >= 60 else "#E24B4A"


def score_label(s: int) -> str:
    return "Strong" if s >= 80 else "Good" if s >= 60 else "Needs Work" if s >= 40 else "Weak"


if "history" not in st.session_state:
    st.session_state.history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_input" not in st.session_state:
    st.session_state.last_input = None

st.title("Firefly Prompt Studio")
st.markdown(
    "**Score, rewrite, and generate variations of your AI image prompts — tuned for Adobe Firefly workflows.**"
)
st.caption(
    "Tip: strong Firefly prompts usually specify subject, environment, lighting, and style. "
    "Use responsibly and follow Adobe’s terms and applicable laws."
)
st.markdown("---")

col1, col2 = st.columns([1, 1.4], gap="large")

with col1:
    st.subheader("Your Prompt")
    user_prompt = st.text_area(
        "prompt",
        placeholder="e.g. a woman in a forest",
        height=120,
        label_visibility="collapsed",
    )
    use_case = st.selectbox(
        "Use case",
        [
            "General",
            "Social / feed post",
            "Brand / marketing visual",
            "Concept art / exploration",
            "Photo-real composite",
        ],
        help="Shapes how the rewrite emphasizes composition and wording for typical Firefly use.",
    )
    style_hint = st.selectbox(
        "Style",
        [
            "No preference",
            "Photorealistic",
            "Illustration",
            "Cinematic",
            "Fantasy",
            "Minimalist",
            "Abstract",
        ],
    )
    analyze_btn = st.button("Analyze & Improve ", use_container_width=True, type="primary")

    if st.session_state.history:
        st.markdown("---")
        st.subheader("History")
        for item in reversed(st.session_state.history[-5:]):
            with st.expander(f"{item['original'][:40]}..."):
                st.write(f"**Score:** {item['score']}/100")
                st.write(f"**Rewritten:** {item['rewritten']}")

with col2:
    if analyze_btn:
        if not user_prompt.strip():
            st.warning("Please enter a prompt first!")
        else:
            with st.spinner("Analyzing your prompt..."):
                try:
                    style = "" if style_hint == "No preference" else style_hint
                    result = analyze_prompt(user_prompt, style, use_case)
                    st.session_state.last_result = result
                    st.session_state.last_input = {
                        "prompt": user_prompt,
                        "style": style_hint,
                        "use_case": use_case,
                    }
                    st.session_state.history.append(
                        {
                            "original": user_prompt,
                            "score": result["score"],
                            "rewritten": result["rewritten_prompt"],
                        }
                    )
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    result = st.session_state.last_result
    if result:
        meta = st.session_state.last_input or {}
        if meta:
            st.caption(
                f"Last run: **{meta.get('use_case', '—')}** · Style: **{meta.get('style', '—')}**"
            )
        r1, r2 = st.columns([1, 1])
        with r1:
            if st.button("Clear results", use_container_width=True):
                st.session_state.last_result = None
                st.session_state.last_input = None
                st.rerun()
        with r2:
            export = json.dumps(
                {"input": meta, "analysis": result},
                indent=2,
                ensure_ascii=False,
            )
            st.download_button(
                "Download JSON",
                data=export,
                file_name="firefly_prompt_analysis.json",
                mime="application/json",
                use_container_width=True,
            )

        color = score_color(result["score"])
        label = score_label(result["score"])
        st.markdown(
            f"""
            <div style="background:{color}18;border:1px solid {color};border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <p style="margin:0;font-size:13px;color:{color};font-weight:500;">PROMPT SCORE</p>
                        <p style="margin:0;font-size:36px;font-weight:700;color:{color};">{result['score']}<span style="font-size:16px;">/100</span></p>
                        <p style="margin:0;font-size:14px;color:{color};">{label}</p>
                    </div>
                    <div style="text-align:right;">
                        <p style="margin:0 0 4px;font-size:12px;color:#666;">Specificity: {result['score_breakdown']['specificity']}/25</p>
                        <p style="margin:0 0 4px;font-size:12px;color:#666;">Style Clarity: {result['score_breakdown']['style_clarity']}/25</p>
                        <p style="margin:0 0 4px;font-size:12px;color:#666;">Visual Detail: {result['score_breakdown']['visual_detail']}/25</p>
                        <p style="margin:0;font-size:12px;color:#666;">Composition: {result['score_breakdown']['composition']}/25</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if result.get("issues"):
            st.markdown("**What's weak:**")
            for issue in result["issues"]:
                st.markdown(f"- {issue}")
        st.markdown("---")
        st.subheader("Rewritten Prompt")
        st.success(result["rewritten_prompt"])
        st.caption(result["explanation"])
        st.code(result["rewritten_prompt"], language=None)
        st.markdown("---")
        st.subheader("Style Variations")
        for i, v in enumerate(result["variations"]):
            with st.expander(f"{v['style']} variation"):
                st.write(v["prompt"])
                st.code(v["prompt"], language=None)
                )
    elif not analyze_btn:
        st.info("Enter a prompt on the left and click Analyze to get started ")
