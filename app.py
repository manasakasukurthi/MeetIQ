"""
MeetIQ - AI Meeting Intelligence
Run:  streamlit run app.py
Needs: pip install streamlit ollama reportlab
       ollama pull llama3.2   (and make sure Ollama is running)
"""

import html
import re
from datetime import datetime
from io import BytesIO
from urllib.parse import quote

import ollama
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

# ---------------- PAGE SETTINGS ----------------
st.set_page_config(page_title="MeetIQ", page_icon="🤖", layout="wide")

SECTIONS = {
    "MEETING SUMMARY": "📝",
    "KEY DECISIONS": "✅",
    "ACTION ITEMS": "🎯",
    "NEXT STEPS": "🚀",
}

SAMPLE = """Manasa: We need the frontend done before the client demo.
Manasa: I will complete the frontend by Friday.
Rahul: I'll prepare the database by Thursday and share the schema with the team.
Kavya: I will test the application on Saturday and report bugs.
Manasa: We decided to launch the beta version next Monday.
Rahul: Let's also schedule a review meeting on Sunday evening."""

# ---------------- CUSTOM CSS ----------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root { color-scheme: light; }
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
.stApp { background: #f4f6fa; color: #0f172a; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px; }

/* ---------- Text colours (always readable) ---------- */
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
[data-testid="stMain"] h4, [data-testid="stMain"] p, [data-testid="stMain"] li,
[data-testid="stMain"] label, [data-testid="stMain"] span { color: #0f172a; }
[data-testid="stMain"] [data-testid="stCaptionContainer"] * { color: #64748b !important; }
[data-testid="stMain"] label p { color: #334155 !important; font-weight: 600; }
hr { border-color: #e2e8f0 !important; }

/* ---------- Sidebar (navy) ---------- */
[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] * { color: #cbd5e1; }
[data-testid="stSidebar"] .stButton > button {
    background: transparent; border: 1px solid transparent; text-align: left;
    justify-content: flex-start; font-weight: 500; box-shadow: none;
}
[data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,0.08); }
[data-testid="stSidebar"] .stButton > button[kind="primary"] { background: #2563eb; border: none; }
[data-testid="stSidebar"] .stButton > button[kind="primary"] * { color: #ffffff !important; font-weight: 600; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background: #1e293b !important; border: 1px solid #334155 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] * { color: #f1f5f9 !important; }
.side-logo { font-size: 26px; font-weight: 800; color: #ffffff !important; letter-spacing: -0.5px; }
.side-sub { font-size: 12px; color: #94a3b8 !important; margin-top: -4px; }
.user-chip { background: #1e293b; border-radius: 12px; padding: 10px 14px; font-size: 14px; margin: 12px 0; }

/* ---------- Hero & titles ---------- */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #2563eb 100%);
    padding: 40px; border-radius: 20px; margin-bottom: 26px;
    box-shadow: 0 14px 34px rgba(30,58,138,0.25);
}
[data-testid="stMain"] .hero h1 { color: #ffffff !important; font-size: 36px; font-weight: 800; margin: 0 0 8px 0; letter-spacing: -1px; }
/* Greeting ("Good evening, ...") fully white */
[data-testid="stMain"] .hero h1,
[data-testid="stMain"] .hero h1 * {
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
}
/* Username in the greeting */
[data-testid="stMain"] .hero h1 .hero-name,
[data-testid="stMain"] .hero h1 span.hero-name {
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stMain"] .hero p { color: #dbeafe !important; font-size: 16px; margin: 0; max-width: 640px; }
.page-title { font-size: 30px; font-weight: 800; color: #0f172a; letter-spacing: -0.8px; margin-bottom: 2px; }
.page-sub { color: #64748b; margin-bottom: 18px; }
.section-title { font-size: 18px; font-weight: 700; color: #1e3a8a; margin-bottom: 8px; }

/* ---------- Cards ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0 !important;
    box-shadow: 0 4px 16px rgba(15,23,42,0.06); padding: 6px 10px;
}
div[data-testid="stMetric"] {
    background: #ffffff; padding: 20px 22px; border-radius: 16px;
    border: 1px solid #e2e8f0; border-left: 5px solid #2563eb; box-shadow: 0 4px 16px rgba(15,23,42,0.06);
}
[data-testid="stMetricLabel"] * { color: #64748b !important; }
[data-testid="stMetricValue"] * { color: #1e3a8a !important; font-weight: 800; }
.feature { font-size: 15px; color: #64748b; line-height: 1.6; }
.feature b { color: #0f172a; font-size: 17px; }
.badge {
    display: inline-block; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;
    padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; margin-right: 6px;
}
.steps { display: flex; gap: 14px; }
.step { flex: 1; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 18px; box-shadow: 0 4px 16px rgba(15,23,42,0.05); }
.step .num { width: 32px; height: 32px; border-radius: 50%; background: #2563eb; color: #ffffff; font-weight: 700;
    display: flex; align-items: center; justify-content: center; margin-bottom: 8px; }
.step b { color: #0f172a; } .step span { color: #64748b; font-size: 14px; }

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button, .stLinkButton > a, .stFormSubmitButton > button {
    border-radius: 10px; font-weight: 600; padding: 0.6rem 1rem; transition: all .2s ease;
}
[data-testid="stMain"] button[kind^="primary"], [data-testid="stMain"] .stDownloadButton button {
    background: #2563eb !important; border: none !important;
}
[data-testid="stMain"] button[kind^="primary"] *, [data-testid="stMain"] .stDownloadButton button * { color: #ffffff !important; }
[data-testid="stMain"] button[kind="secondary"], [data-testid="stMain"] .stLinkButton a {
    background: #ffffff; border: 1.5px solid #cbd5e1;
}
[data-testid="stMain"] button[kind="secondary"] *, [data-testid="stMain"] .stLinkButton a * { color: #1e3a8a !important; }
[data-testid="stMain"] button:hover, [data-testid="stMain"] .stLinkButton a:hover {
    transform: translateY(-2px); box-shadow: 0 8px 20px rgba(37,99,235,0.22);
}
[data-testid="stMain"] button[kind^="primary"]:hover { background: #1d4ed8 !important; }

/* ---------- Inputs ---------- */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="base-input"] { background: #ffffff !important; }
[data-testid="stMain"] input, [data-testid="stMain"] textarea {
    background: #ffffff !important; color: #0f172a !important; -webkit-text-fill-color: #0f172a !important;
}
[data-testid="stMain"] [data-baseweb="input"], [data-testid="stMain"] [data-baseweb="textarea"] {
    border: 1.5px solid #cbd5e1 !important; border-radius: 10px !important;
}
[data-testid="stMain"] [data-baseweb="input"]:focus-within, [data-testid="stMain"] [data-baseweb="textarea"]:focus-within {
    border-color: #2563eb !important; box-shadow: 0 0 0 3px rgba(37,99,235,0.15);
}

/* Password show/hide (eye) icon: white icon on a blue chip so it stays visible */
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"] button,
[data-testid="stMain"] [data-testid="stTextInput"] button[kind="borderlessIcon"] {
    background: #2563eb !important; border: none !important; border-radius: 8px !important;
    margin: 4px 6px 4px 0 !important; padding: 4px 8px !important; box-shadow: none !important;
}
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"] button *,
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"] button svg,
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"] button svg * {
    color: #ffffff !important; fill: #ffffff !important; stroke: #ffffff !important;
}
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"] button:hover {
    background: #1d4ed8 !important; transform: none; box-shadow: none;
}
/* Force the eye symbol itself to white */
[data-testid="stMain"] [data-testid="stTextInputRootElement"] button,
[data-testid="stMain"] [data-testid="stTextInputRootElement"] button * ,
[data-testid="stMain"] [data-testid="stTextInput"] button svg,
[data-testid="stMain"] [data-testid="stTextInput"] button svg path {
    color: #ffffff !important; fill: #ffffff !important; stroke: #ffffff !important;
}
[data-testid="stMain"] [data-testid="stTextInputRootElement"] button {
    background: #1e3a8a !important;
}

/* Logout button in sidebar: solid red with white text */
[data-testid="stSidebar"] .st-key-logout button {
    background: #dc2626 !important; border: none !important; justify-content: center !important;
}
[data-testid="stSidebar"] .st-key-logout button * { color: #ffffff !important; font-weight: 700; }
[data-testid="stSidebar"] .st-key-logout button:hover { background: #b91c1c !important; }

/* ---------- Login ---------- */
.login-brand {
    background: linear-gradient(150deg, #0f172a 0%, #1e3a8a 60%, #2563eb 100%);
    border-radius: 20px; padding: 48px 40px; min-height: 520px; position: relative; overflow: hidden;
    box-shadow: 0 18px 44px rgba(30,58,138,0.30);
}
.login-brand::after {
    content: ""; position: absolute; width: 280px; height: 280px; right: -90px; bottom: -90px;
    background: rgba(255,255,255,0.07); border-radius: 50%;
}
/* MeetIQ logo text in GOLD */
[data-testid="stMain"] .login-brand h1,
[data-testid="stMain"] .login-brand h1 span {
    color: #f5c242 !important; -webkit-text-fill-color: #f5c242 !important;
    font-size: 44px; font-weight: 800; letter-spacing: -1.5px; margin: 0 0 8px 0;
    text-shadow: 0 2px 14px rgba(245,194,66,0.35);
}
[data-testid="stMain"] .login-brand p { color: #dbeafe !important; font-size: 17px; margin-bottom: 28px; }
.login-brand ul { list-style: none; padding: 0; margin: 0; }
[data-testid="stMain"] .login-brand li { color: #ffffff !important; font-size: 16px; padding: 10px 0; }
.login-title { font-size: 28px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px; margin-bottom: 2px; }
.login-sub { color: #64748b; margin-bottom: 14px; }

/* ---------- Animation ---------- */
@keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
.hero, .login-brand, .step, div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stMetric"] { animation: fadeUp .5s ease both; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- SESSION STATE ----------------
defaults = {
    "logged_in": False,
    "username": "",
    "analysis": "",
    "meeting_history": [],
    "page": "Dashboard",
    "current_title": "",
    "current_date": "",
    "model": "llama3.2",
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


# ---------------- HELPERS ----------------
def greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def parse_sections(text: str) -> dict:
    """Split the AI report into its four sections."""
    names = "|".join(SECTIONS)
    pattern = rf"(?im)^[#*\s]*({names})[\s*:#]*$"
    matches = list(re.finditer(pattern, text))
    result = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[m.group(1).upper()] = text[m.end():end].strip()
    return result


def count_actions(text: str) -> int:
    section = parse_sections(text).get("ACTION ITEMS", "")
    task_lines = [l for l in section.split("\n") if re.search(r"\btask\b\s*:", l, re.I)]
    if task_lines:
        return len(task_lines)
    return sum(1 for l in section.split("\n") if re.match(r"^(\-|\*|•|\d+\.)\s", l))


def md_to_pdf_markup(line: str) -> str:
    line = html.escape(line.strip())
    line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
    line = re.sub(r"^(\-|\*)\s+", "• ", line)
    return line


def build_pdf(title: str, date: str, analysis: str) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)
    base = getSampleStyleSheet()
    brand = ParagraphStyle("Brand", parent=base["Title"], alignment=TA_CENTER,
                           textColor=colors.HexColor("#1d4ed8"), fontSize=28)
    sub = ParagraphStyle("Sub", parent=base["Normal"], alignment=TA_CENTER,
                         textColor=colors.HexColor("#64748b"), fontSize=11)
    head = ParagraphStyle("Head", parent=base["Heading2"],
                          textColor=colors.HexColor("#0f172a"), spaceBefore=12)
    body = ParagraphStyle("Body", parent=base["Normal"], leading=15)

    story = [
        Paragraph("MeetIQ", brand),
        Paragraph("AI-Powered Meeting Intelligence Report", sub),
        Spacer(1, 10),
        HRFlowable(width="100%", color=colors.HexColor("#bfdbfe")),
        Spacer(1, 10),
        Paragraph(f"<b>Meeting:</b> {html.escape(title)}", body),
        Paragraph(f"<b>Generated:</b> {html.escape(date)}", body),
        Spacer(1, 12),
    ]
    for line in analysis.split("\n"):
        if not line.strip():
            continue
        clean = re.sub(r"[#*:\s]+$", "", re.sub(r"^[#*\s]+", "", line)).upper()
        if clean in SECTIONS:
            story.append(Paragraph(clean.title(), head))
        else:
            story.append(Paragraph(md_to_pdf_markup(line), body))
            story.append(Spacer(1, 4))
    doc.build(story)
    buffer.seek(0)
    return buffer


def go(page: str, clear: bool = False):
    st.session_state.page = page
    if clear:
        st.session_state.analysis = ""
    st.rerun()


def page_header(title: str, subtitle: str):
    st.markdown(f"<div class='page-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-sub'>{subtitle}</div>", unsafe_allow_html=True)


# ---------------- LOGIN PAGE ----------------
if not st.session_state.logged_in:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.markdown(
            """<div class='login-brand'>
            <h1>🤖 MeetIQ</h1>
            <p>Turn conversations into clear actions.</p>
            <ul>
              <li>📝 &nbsp;Instant AI meeting summaries</li>
              <li>🎯 &nbsp;Tasks, owners &amp; deadlines extracted</li>
              <li>📄 &nbsp;One-click PDF reports</li>
              <li>🔒 &nbsp;Runs locally - your data stays private</li>
            </ul></div>""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<div class='login-title'>Welcome back 👋</div>", unsafe_allow_html=True)
            st.markdown("<div class='login-sub'>Sign in to continue to your dashboard.</div>",
                        unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Email or Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("🔐 Login", use_container_width=True, type="primary")
            if submitted:
                if username and password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.page = "Dashboard"
                    st.rerun()
                else:
                    st.warning("Please enter username and password.")
            st.caption("New to MeetIQ?")
            if st.button("✨ Create Account", use_container_width=True):
                st.info("Demo account creation is ready for the presentation.")
    st.stop()

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("<div class='side-logo'>🤖 MeetIQ</div>", unsafe_allow_html=True)
    st.markdown("<div class='side-sub'>AI Meeting Intelligence</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='user-chip'>👤 <b>{html.escape(st.session_state.username)}</b></div>",
                unsafe_allow_html=True)

    nav = [("🏠 Dashboard", "Dashboard"), ("➕ New Meeting", "New Meeting"),
           ("📚 Meeting History", "History")]
    for label, target in nav:
        active = st.session_state.page == target
        if st.button(label, use_container_width=True, key=f"nav_{target}",
                     type="primary" if active else "secondary"):
            go(target, clear=(target == "New Meeting"))

    st.markdown("---")
    st.session_state.model = st.selectbox(
        "🧠 AI Model", ["llama3.2", "llama3.1", "mistral", "gemma2"],
        index=["llama3.2", "llama3.1", "mistral", "gemma2"].index(st.session_state.model),
    )
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True, key="logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.page = "Dashboard"
        st.rerun()

page = st.session_state.page

# ============================================================
# DASHBOARD
# ============================================================
if page == "Dashboard":
    name = st.session_state.username.split("@")[0].title()
    st.markdown(
        f"""<div class='hero'>
        <h1>{greeting()}, <span class='hero-name'>{html.escape(name)}</span> 👋</h1>
        <p>Transform meeting conversations into summaries, decisions and actionable
        tasks - powered by a local AI model, so your data stays private.</p></div>""",
        unsafe_allow_html=True,
    )

    history = st.session_state.meeting_history
    total_actions = sum(count_actions(m["analysis"]) for m in history)

    c1, c2, c3 = st.columns(3)
    c1.metric("📅 Meetings Analysed", len(history))
    c2.metric("🎯 Action Items", total_actions)
    c3.metric("🟢 AI Status", "Online")

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>✨ What MeetIQ does</div>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    for col, icon, head, desc in [
        (f1, "📝", "Smart Summaries", "Long conversations condensed into a clear, concise summary."),
        (f2, "🎯", "Action Tracking", "Tasks, owners and deadlines extracted automatically."),
        (f3, "📄", "Share Instantly", "Export a branded PDF or share the report on WhatsApp."),
    ]:
        with col, st.container(border=True):
            st.markdown(f"<div class='feature'><b>{icon} {head}</b><br>{desc}</div>",
                        unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>⚡ How it works</div>", unsafe_allow_html=True)
    st.markdown(
        """<div class='steps'>
        <div class='step'><div class='num'>1</div><b>Paste</b><br><span>Add your meeting transcript.</span></div>
        <div class='step'><div class='num'>2</div><b>Analyse</b><br><span>AI extracts decisions &amp; tasks.</span></div>
        <div class='step'><div class='num'>3</div><b>Share</b><br><span>Download a PDF or send on WhatsApp.</span></div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    if st.button("➕ Create New Meeting", use_container_width=True, type="primary"):
        go("New Meeting", clear=True)

# ============================================================
# NEW MEETING
# ============================================================
elif page == "New Meeting":
    page_header("📝 New Meeting",
                "Enter your meeting details and let AI generate a structured report.")

    with st.container(border=True):
        meeting_title = st.text_input("Meeting Title", placeholder="Example: Project Team Meeting")
        st.session_state.setdefault("meeting_text", "")
        meeting_text = st.text_area(
            "Meeting Conversation", key="meeting_text", height=260,
            placeholder="Paste your meeting transcript here...\n\nExample:\n"
                        "Manasa will complete the frontend by Friday.\n"
                        "Rahul will prepare the database by Thursday.",
        )
        b1, b2 = st.columns([1, 3])
        if b1.button("📋 Load Sample", use_container_width=True):
            st.session_state.meeting_text = SAMPLE
            st.rerun()
        generate = b2.button("✨ Generate Meeting Insights", use_container_width=True, type="primary")

    if generate:
        if not meeting_text.strip():
            st.warning("Please enter a meeting conversation first.")
        else:
            prompt = f"""
You are an AI Meeting Intelligence Assistant.

Analyze this meeting conversation:

{meeting_text}

Return a professional meeting report with exactly these section headings,
each on its own line, in capital letters:

MEETING SUMMARY
Write a concise summary.

KEY DECISIONS
List the important decisions as bullet points.

ACTION ITEMS
For every task mentioned, write one bullet in this format:
- Task: ... | Person: ... | Deadline: ...

NEXT STEPS
List what should happen next as bullet points.

Keep the output clear and professional.
"""
            success = False
            try:
                with st.spinner("🤖 AI is analyzing your meeting..."):
                    response = ollama.chat(
                        model=st.session_state.model,
                        messages=[{"role": "user", "content": prompt}],
                    )
                st.session_state.analysis = response["message"]["content"]
                st.session_state.current_title = meeting_title or "Untitled Meeting"
                st.session_state.current_date = datetime.now().strftime("%d %B %Y, %I:%M %p")
                st.session_state.meeting_history.append({
                    "title": st.session_state.current_title,
                    "date": st.session_state.current_date,
                    "analysis": st.session_state.analysis,
                })
                success = True
            except Exception as err:
                st.error("Could not reach the AI model. Make sure Ollama is running "
                         f"and the model is installed (`ollama pull {st.session_state.model}`).")
                with st.expander("Technical details"):
                    st.code(str(err))
            if success:
                go("Report")

# ============================================================
# REPORT
# ============================================================
elif page == "Report":
    if not st.session_state.analysis:
        go("Dashboard")

    page_header("📊 Meeting Intelligence Report", "Your AI-generated meeting analysis.")
    st.markdown(
        f"<span class='badge'>📌 {html.escape(st.session_state.current_title)}</span>"
        f"<span class='badge'>🕒 {st.session_state.current_date}</span>"
        f"<span class='badge'>🎯 {count_actions(st.session_state.analysis)} action items</span>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    sections = parse_sections(st.session_state.analysis)
    if sections:
        left, right = st.columns(2)
        for i, (name, icon) in enumerate(SECTIONS.items()):
            if name in sections:
                with (left if i % 2 == 0 else right), st.container(border=True):
                    st.markdown(f"<div class='section-title'>{icon} {name.title()}</div>",
                                unsafe_allow_html=True)
                    st.markdown(sections[name])
    else:  # fallback if the model ignored the format
        with st.container(border=True):
            st.markdown(st.session_state.analysis)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    pdf = build_pdf(st.session_state.current_title, st.session_state.current_date,
                    st.session_state.analysis)
    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇️ Download PDF", data=pdf, file_name="MeetIQ_Meeting_Report.pdf",
                       mime="application/pdf", use_container_width=True)
    d2.download_button("📝 Download Text", data=st.session_state.analysis,
                       file_name="MeetIQ_Meeting_Report.txt", mime="text/plain",
                       use_container_width=True)
    share = quote(f"MeetIQ Meeting Report - {st.session_state.current_title}\n\n"
                  f"{st.session_state.analysis}"[:1500])
    d3.link_button("📤 Share on WhatsApp", f"https://wa.me/?text={share}",
                   use_container_width=True)

# ============================================================
# HISTORY
# ============================================================
elif page == "History":
    page_header("📚 Meeting History", "View your previously generated meeting reports.")
    history = st.session_state.meeting_history

    if not history:
        st.info("No meetings yet. Create your first meeting analysis.")
    else:
        query = st.text_input("🔍 Search meetings", placeholder="Search by title...")
        entries = [(i, m) for i, m in enumerate(history)
                   if query.lower() in m["title"].lower()]
        if not entries:
            st.warning("No meetings match your search.")
        for idx, meeting in reversed(entries):
            with st.container(border=True):
                a, b = st.columns([4, 1])
                a.markdown(f"### 📌 {meeting['title']}")
                a.caption(f"Generated on {meeting['date']} • "
                          f"{count_actions(meeting['analysis'])} action items")
                if b.button("👁️ View", key=f"view_{idx}", use_container_width=True, type="primary"):
                    st.session_state.analysis = meeting["analysis"]
                    st.session_state.current_title = meeting["title"]
                    st.session_state.current_date = meeting["date"]
                    go("Report")
                if b.button("🗑️ Delete", key=f"del_{idx}", use_container_width=True):
                    st.session_state.meeting_history.pop(idx)
                    st.rerun()