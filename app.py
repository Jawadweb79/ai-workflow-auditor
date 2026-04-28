"""
app.py -- AI Workflow Auditor | Streamlit UI
Brand: Digital Solution by Jawad Hussain
"""

import os, json, base64, csv
from datetime import datetime
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from input_handler    import load_from_dict
from processor        import process_workflow
from roi_engine       import run_roi_engine, DEFAULT_HOURLY_VALUE
from ai_engine        import get_ai_analysis
from report_generator import generate_and_save_reports, generate_markdown_report
from validator        import ValidationError
from sheets_handler   import save_lead, is_configured as sheets_configured

# ── Constants ──────────────────────────────────────────────────────────────────
OUTPUT_DIR    = os.path.join(os.path.dirname(__file__), "reports")
ASSETS_DIR    = os.path.join(os.path.dirname(__file__), "assets")
PHOTO_PATH    = os.path.join(ASSETS_DIR, "jawad_photo.jpg")
BANNER_PATH   = os.path.join(ASSETS_DIR, "banner.png")
LEADS_CSV     = os.path.join(os.path.dirname(__file__), "leads.csv")
LINKEDIN_URL  = "https://www.linkedin.com/in/jawad-hussain-digital-solution/"
CONTACT_EMAIL = "jawadweb79@gmail.com"

DEMO_INPUT = {
    "role": "LinkedIn Creator",
    "industry": "Personal Branding",
    "tasks": [
        {"task": "Write posts manually",  "time_per_week_hours": 10},
        {"task": "Design content",        "time_per_week_hours": 5},
        {"task": "Schedule posts",        "time_per_week_hours": 3},
        {"task": "Reply to comments",     "time_per_week_hours": 4},
    ],
    "tools_used": ["ChatGPT", "Canva"],
    "pain_points": ["time consuming", "no system"],
}

# ── CSV fallback for email capture ─────────────────────────────────────────────
def save_lead_csv(name, email, role, industry, time_saved, efficiency, auto_score):
    """Always-available fallback: save lead to local CSV."""
    file_exists = os.path.exists(LEADS_CSV)
    with open(LEADS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp","Name","Email","Role","Industry",
                             "Time Saved/Week","Efficiency %","Automation Score"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            name or "Anonymous", email or "Not provided",
            role, industry, f"{time_saved:.1f}h",
            f"{efficiency:.1f}%", f"{auto_score}/100"
        ])


# ── Reusable banner hero (used on every tab) ───────────────────────────────────
def _load_b64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

_b64_banner_cache = None
_b64_photo_cache  = None

def render_banner(title: str, subtitle: str = ""):
    """Render the LinkedIn-style banner header on any tab."""
    global _b64_banner_cache, _b64_photo_cache
    if _b64_banner_cache is None:
        _b64_banner_cache = _load_b64(BANNER_PATH)
    if _b64_photo_cache is None:
        _b64_photo_cache  = _load_b64(PHOTO_PATH)

    if not _b64_banner_cache:
        # Fallback: plain gradient
        st.markdown(
            f'<div class="hero"><h1 style="margin:0 0 8px 0;">{title}</h1>' +
            (f'<p style="opacity:.85;margin:0;font-size:0.95rem;">{subtitle}</p>' if subtitle else "") +
            '</div>', unsafe_allow_html=True)
        return

    photo_html = (
        f'<img src="data:image/jpeg;base64,{_b64_photo_cache}"' +
        ' style="width:82px;height:82px;border-radius:50%;object-fit:cover;' +
        'border:4px solid white;box-shadow:0 4px 14px rgba(0,0,0,0.35);' +
        'position:absolute;bottom:-16px;left:26px;"/>' if _b64_photo_cache else ""
    )
    sub_html = (
        f'<p style="font-size:0.88rem;opacity:0.9;margin:6px 0 0 0;line-height:1.55;' +
        f'text-shadow:0 1px 4px rgba(0,0,0,0.4);max-width:560px;">{subtitle}</p>' if subtitle else ""
    )
    st.markdown(f"""
    <div style="position:relative;border-radius:16px;overflow:visible;
                margin-bottom:32px;box-shadow:0 8px 32px rgba(0,0,0,0.16);">
        <img src="data:image/png;base64,{_b64_banner_cache}"
             style="width:100%;height:210px;object-fit:cover;
                    border-radius:16px;display:block;"/>
        <div style="position:absolute;inset:0;border-radius:16px;
                    background:linear-gradient(135deg,
                      rgba(15,23,42,0.60) 0%,
                      rgba(30,58,138,0.35) 50%,
                      rgba(0,0,0,0.10) 100%);"></div>
        <div style="position:absolute;top:24px;left:130px;right:20px;color:white;">
            <h1 style="font-size:1.85rem;font-weight:800;margin:0 0 0 0;
                       line-height:1.2;text-shadow:0 2px 8px rgba(0,0,0,0.5);">
                {title}
            </h1>
            {sub_html}
        </div>
        {photo_html}
    </div>""", unsafe_allow_html=True)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Workflow Auditor | Digital Solution",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.metric-card {
    background: linear-gradient(135deg,#f8fafc,#eff6ff);
    border: 1px solid #bfdbfe; border-radius: 14px;
    padding: 20px 12px; text-align: center;
}
.metric-value { font-size:1.85rem; font-weight:800; color:#1e40af; line-height:1.1; }
.metric-label { font-size:0.77rem; color:#64748b; margin-top:6px; font-weight:500;
                text-transform:uppercase; letter-spacing:0.4px; }

.sec-header {
    background: linear-gradient(90deg,#1e3a8a,#2563eb);
    color:white; padding:11px 20px; border-radius:10px;
    font-weight:700; font-size:0.92rem; margin:22px 0 14px 0;
}
.hero {
    background: linear-gradient(135deg,#0f172a 0%,#1e3a8a 55%,#2563eb 100%);
    border-radius:18px; padding:42px 40px; color:white; margin-bottom:30px;
}
.hero-badge {
    display:inline-block; background:rgba(255,255,255,0.15);
    border:1px solid rgba(255,255,255,0.35); color:white;
    border-radius:20px; padding:4px 16px; font-size:0.75rem;
    font-weight:700; margin-bottom:16px; letter-spacing:0.6px;
}
.hero h1 { font-size:2.3rem; font-weight:800; margin:0 0 12px 0; line-height:1.2; }
.hero p  { font-size:1.05rem; opacity:0.88; margin:0; max-width:640px; line-height:1.65; }

.about-card {
    background:white; border:1px solid #e2e8f0; border-radius:14px;
    padding:26px 22px; box-shadow:0 2px 10px rgba(0,0,0,0.05); height:100%;
}
.step-num {
    width:38px; height:38px; border-radius:50%;
    background:linear-gradient(135deg,#1e3a8a,#2563eb);
    color:white; font-weight:800; font-size:17px;
    display:inline-flex; align-items:center; justify-content:center;
    margin-bottom:14px;
}
.ex-box {
    background:#f0f7ff; border-left:4px solid #2563eb;
    border-radius:0 12px 12px 0; padding:18px 22px;
    font-size:0.88rem; line-height:1.75; color:#1e293b;
}
.email-wrap {
    background:linear-gradient(135deg,#eff6ff,#f0fdf4);
    border:2px solid #93c5fd; border-radius:16px; padding:20px 24px; margin-bottom:20px;
}
.stButton > button {
    background:linear-gradient(135deg,#1e3a8a,#2563eb) !important;
    color:white !important; border:none !important; border-radius:10px !important;
    font-weight:600 !important; font-size:0.95rem !important;
}
.stButton > button:hover { transform:translateY(-1px) !important; box-shadow:0 6px 18px rgba(30,58,138,0.35) !important; }
.stTextInput input { font-size:0.95rem !important; padding:10px 14px !important; border-radius:8px !important; }
.stTextArea textarea { font-size:0.93rem !important; padding:12px 14px !important;
                       border-radius:8px !important; min-height:120px !important; line-height:1.65 !important; }
.stTabs [data-baseweb="tab-list"] { gap:4px; background:#f1f5f9; border-radius:12px; padding:4px; }
.stTabs [data-baseweb="tab"]      { border-radius:9px !important; font-weight:600 !important; }
.stTabs [aria-selected="true"]    { background:white !important; color:#1e3a8a !important;
                                    box-shadow:0 2px 8px rgba(0,0,0,0.08) !important; }
.sidebar-brand { text-align:center; padding:4px 0 16px 0;
                 border-bottom:1px solid #e2e8f0; margin-bottom:16px; }
.sidebar-brand-name   { font-size:17px; font-weight:800; color:#1e3a8a; margin:8px 0 2px 0; }
.sidebar-brand-person { font-size:11px; color:#94a3b8; margin:0; letter-spacing:0.3px; }
.pg-footer { text-align:center; color:#94a3b8; font-size:0.78rem;
             padding:20px 0 6px 0; border-top:1px solid #f1f5f9; margin-top:40px; }
.pg-footer a { color:#2563eb; text-decoration:none; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ─────────────────────────────────────────────────────────
for k, v in [("results", None), ("demo_requested", False), ("n_tasks", 3)]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">', unsafe_allow_html=True)
    if os.path.exists(PHOTO_PATH):
        st.image(PHOTO_PATH, width=76)
    else:
        st.markdown("""<div style="width:76px;height:76px;border-radius:50%;
            background:linear-gradient(135deg,#1e3a8a,#2563eb);display:flex;
            align-items:center;justify-content:center;font-size:24px;
            font-weight:800;color:white;margin:0 auto;">JH</div>""",
            unsafe_allow_html=True)
    st.markdown(
        '<p class="sidebar-brand-name">Digital Solution</p>'
        '<p class="sidebar-brand-person">Jawad Hussain</p>'
        '</div>', unsafe_allow_html=True)

    st.markdown("**⚙️ Configuration**")
    api_key = st.text_input("DeepSeek API Key",
        value=os.getenv("DEEPSEEK_API_KEY",""), type="password",
        help="Get your key at platform.deepseek.com")
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key

    hourly_rate = st.number_input("Your hourly rate (USD)",
        min_value=10, max_value=2000,
        value=int(DEFAULT_HOURLY_VALUE), step=5)

    st.divider()
    if st.button("📋 Load Demo Data", use_container_width=True):
        st.session_state["demo_requested"] = True
        st.session_state["n_tasks"] = 4
        st.rerun()

    st.divider()
    if sheets_configured():
        st.success("🟢 Google Sheets connected")
    elif os.path.exists(LEADS_CSV):
        st.info(f"📄 Saving leads to leads.csv")
    else:
        st.caption("📄 Leads saved locally to leads.csv\n🔗 See SETUP.md for Google Sheets.")

    st.markdown('<div class="pg-footer">AI Workflow Auditor v1.0<br/>by Digital Solution</div>',
                unsafe_allow_html=True)

# prefill from demo
prefill = DEMO_INPUT if st.session_state.get("demo_requested") else {}
if st.session_state.get("demo_requested"):
    st.session_state["demo_requested"] = False


# ── TABS ───────────────────────────────────────────────────────────────────────
t_about, t_input, t_results, t_contact = st.tabs([
    "🏠  About & How It Works",
    "📝  Run Your Audit",
    "📊  Audit Results",
    "📬  Contact",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ABOUT
# ══════════════════════════════════════════════════════════════════════════════
with t_about:
    render_banner("AI Workflow Auditor", "🤖 AI-Powered · Free to Use · Instant Report — Stop guessing where your time goes.")

    st.markdown("### What Does It Do?")
    st.markdown("Most professionals lose **30–60% of their working week** to repetitive, manual, or "
                "fragmented tasks. This auditor acts like a senior AI consultant — it analyses your "
                "specific workflow and gives you a **step-by-step system** to get that time back.")

    st.divider()
    st.markdown("### How It Works — 3 Steps")
    c1, c2, c3 = st.columns(3)
    for col, num, title, desc in [
        (c1,"1","Input Your Workflow","Enter your role, industry, tasks with hours, tools, and pain points. Under 3 minutes."),
        (c2,"2","AI Analyses & Diagnoses","Tasks are classified, inefficiencies flagged, then DeepSeek AI designs your optimised system."),
        (c3,"3","Download Your Report","Get a full 7-section audit in PDF and Markdown — ROI, before/after workflow, implementation plan."),
    ]:
        with col:
            st.markdown(f"""<div class="about-card">
                <div class="step-num">{num}</div>
                <h4 style="margin:0 0 10px;color:#1e3a8a;">{title}</h4>
                <p style="color:#475569;font-size:0.9rem;line-height:1.65;margin:0">{desc}</p>
            </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("### What's Inside Your Report")
    rl, rr = st.columns(2)
    with rl:
        st.markdown("- **Section 1** — Current workflow mapped out\n- **Section 2** — Key inefficiencies + severity\n"
                    "- **Section 3** — Automation opportunities per task\n- **Section 4** — Redesigned optimised workflow")
    with rr:
        st.markdown("- **Section 5** — Step-by-step implementation plan\n- **Section 6** — Full ROI: time, %, annual value\n"
                    "- **Section 7** — Executive summary, action-first")

    st.divider()
    st.markdown("### 📌 Filled Example — What to Enter")
    e1, e2 = st.columns(2)
    with e1:
        st.markdown("""<div class="ex-box">
        <strong>Role:</strong> LinkedIn Creator<br/><strong>Industry:</strong> Personal Branding<br/><br/>
        <strong>Tasks:</strong><br/>
        &nbsp;&nbsp;• Write posts manually — 10 hrs/week<br/>
        &nbsp;&nbsp;• Design content graphics — 5 hrs/week<br/>
        &nbsp;&nbsp;• Schedule posts — 3 hrs/week<br/>
        &nbsp;&nbsp;• Reply to comments — 4 hrs/week<br/><br/>
        <strong>Tools:</strong> ChatGPT, Canva<br/>
        <strong>Pain points:</strong> time consuming, no system
        </div>""", unsafe_allow_html=True)
    with e2:
        st.markdown("""<div class="ex-box">
        <strong>Expected results for this example:</strong><br/><br/>
        ⏱&nbsp; <strong>7.5 hours saved per week</strong><br/>
        📊&nbsp; <strong>34% efficiency improvement</strong><br/>
        🤖&nbsp; <strong>Automation score: 59 / 100</strong><br/>
        📅&nbsp; <strong>393 hours saved per year</strong><br/>
        💰&nbsp; <strong>$19,630 annual value recovered</strong><br/><br/>
        Plus: redesigned weekly workflow, named tool recommendations,
        and an 8-step implementation plan you can start today.
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 💡 Tips for Best Results")
    st.markdown("- **Be specific** — 'Write LinkedIn posts' beats 'Content'\n"
                "- **Include all tasks**, even 30-min admin ones — they add up\n"
                "- **List every tool** — even Gmail and Excel\n"
                "- **Be honest about pain points** — specifics drive better diagnosis\n"
                "- Use **Load Demo Data** in the sidebar to try a pre-filled example")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — INPUT (task count OUTSIDE form for real-time updates)
# ══════════════════════════════════════════════════════════════════════════════
with t_input:
    render_banner("Run Your Workflow Audit", "Complete the form below — takes 2–3 minutes. Fields marked * are required.")

    # ── EMAIL CAPTURE — outside the form, always visible ──────────────────────
    st.markdown("""<div class="email-wrap">
    <p style="font-size:1.1rem;font-weight:700;color:#1e3a8a;margin:0 0 4px 0;">
        📧 Your Contact Details (Required)</p>
    <p style="font-size:0.87rem;color:#475569;margin:0 0 14px 0;">
        Enter your name and email to receive your audit results and AI workflow insights
        from Jawad Hussain (Digital Solution). Required to run the audit.</p>
    </div>""", unsafe_allow_html=True)

    ec1, ec2 = st.columns(2)
    with ec1:
        lead_name = st.text_input("Your Name *",
            placeholder="e.g.  Sarah Ahmed (required)", key="lead_name")
    with ec2:
        lead_email = st.text_input("Your Email Address *",
            placeholder="e.g.  sarah@company.com (required)", key="lead_email")
    if lead_email and "@" not in lead_email:
        st.warning("⚠️ Please enter a valid email address.")

    st.divider()

    # ── PROFILE (outside form) ─────────────────────────────────────────────────
    st.markdown('<div class="sec-header">👤 Your Profile</div>', unsafe_allow_html=True)
    p1, p2 = st.columns(2)
    with p1:
        role = st.text_input("Your Role / Job Title *",
            value=prefill.get("role",""),
            placeholder="e.g. Marketing Manager, Freelance Designer, Founder")
    with p2:
        industry = st.text_input("Your Industry *",
            value=prefill.get("industry",""),
            placeholder="e.g. E-commerce, SaaS, Personal Branding, Finance")

    # ── TASK COUNT — OUTSIDE FORM so it updates rows in real time ─────────────
    st.markdown('<div class="sec-header">📋 Your Weekly Tasks</div>', unsafe_allow_html=True)
    st.markdown("Add **at least 3 tasks**. Be descriptive — *'Reply to client emails'* beats *'emails'*.")

    n_tasks = st.number_input(
        "How many tasks do you want to include?",
        min_value=3, max_value=15,
        value=st.session_state["n_tasks"],
        step=1,
        key="n_tasks_widget",
        help="Change this number to instantly add or remove task rows below"
    )
    # sync to session state immediately
    st.session_state["n_tasks"] = int(n_tasks)

    # Build task rows dynamically — OUTSIDE the form
    prefill_tasks = prefill.get("tasks", [])
    task_rows = []
    for i in range(st.session_state["n_tasks"]):
        tc1, tc2 = st.columns([4, 1])
        ex = prefill_tasks[i] if i < len(prefill_tasks) else {}
        with tc1:
            tname = st.text_input(
                f"Task {i+1} description *",
                value=ex.get("task",""),
                placeholder="e.g. Write weekly newsletter, Reply to DMs, Schedule posts",
                key=f"tn_{i}",
            )
        with tc2:
            thours = st.number_input(
                "Hrs/week", min_value=0.25, max_value=80.0,
                value=float(ex.get("time_per_week_hours", 1.0)),
                step=0.5, key=f"th_{i}",
            )
        if tname.strip():
            task_rows.append({"task": tname.strip(), "time_per_week_hours": thours})

    st.divider()

    # ── TOOLS & PAIN POINTS + SUBMIT — inside a minimal form ──────────────────
    st.markdown('<div class="sec-header">🛠 Tools & Pain Points</div>', unsafe_allow_html=True)

    tl_col, pp_col = st.columns(2)
    with tl_col:
        tools_raw = st.text_area(
            "Tools & apps you currently use *",
            value=", ".join(prefill.get("tools_used",[])),
            placeholder=(
                "List every tool, separated by commas.\n\n"
                "e.g. ChatGPT, Canva, Notion, Gmail,\n"
                "Excel, Slack, Trello, Zoom, HubSpot"
            ),
            height=150,
        )
    with pp_col:
        pain_raw = st.text_area(
            "Your main pain points *",
            value=", ".join(prefill.get("pain_points",[])),
            placeholder=(
                "What frustrates you most? Be honest.\n\n"
                "e.g. too much manual work, no system,\n"
                "context switching, can't scale,\n"
                "always behind, takes too long"
            ),
            height=150,
        )

    with st.expander("📁 Or upload a JSON input file (optional)"):
        uploaded = st.file_uploader("Upload workflow JSON", type="json")

    st.markdown("<br/>", unsafe_allow_html=True)
    run_btn = st.button("🚀  Run My Workflow Audit", use_container_width=True, type="primary")

    # ── Submit logic ───────────────────────────────────────────────────────────
    if run_btn:
        # Validate required fields
        lname_val  = st.session_state.get("lead_name","").strip()
        lemail_val = st.session_state.get("lead_email","").strip()
        if not lname_val:
            st.error("⚠️ Please enter your name before running the audit.")
            st.stop()
        if not lemail_val:
            st.error("⚠️ Please enter your email address before running the audit.")
            st.stop()
        if "@" not in lemail_val or "." not in lemail_val:
            st.error("⚠️ Please enter a valid email address (e.g. you@email.com).")
            st.stop()

        if uploaded:
            try:
                raw = json.load(uploaded)
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
                st.stop()
            workflow_raw = raw
        else:
            tools = [t.strip() for t in tools_raw.split(",") if t.strip()]
            pain  = [p.strip() for p in pain_raw.split(",") if p.strip()]
            workflow_raw = {
                "role": role, "industry": industry,
                "tasks": task_rows,
                "tools_used": tools, "pain_points": pain,
            }

        try:
            wf = load_from_dict(workflow_raw)
        except ValidationError as e:
            st.error(str(e))
            st.stop()

        prog = st.progress(0, text="Starting audit…")
        prog.progress(15, text="🔍 Classifying tasks and detecting inefficiencies…")
        analysis = process_workflow(wf)

        prog.progress(38, text="📐 Calculating ROI…")
        roi = run_roi_engine(analysis, hourly_value=float(hourly_rate))

        prog.progress(60, text="🤖 Running DeepSeek AI analysis…")
        ai_content = get_ai_analysis(analysis, roi)

        prog.progress(82, text="📄 Generating Markdown + PDF reports…")
        paths      = generate_and_save_reports(analysis, roi, ai_content, OUTPUT_DIR)
        md_content = generate_markdown_report(analysis, roi, ai_content)

        # Save lead — mandatory now, always save
        lname  = lname_val
        lemail = lemail_val
        prog.progress(92, text="💾 Saving your contact details…")
        # Always save to CSV
        save_lead_csv(lname, lemail, wf.get("role",""), wf.get("industry",""),
                      roi["time_saved_per_week"], roi["efficiency_gain_percent"],
                      roi["automation_score"])
        # Also try Google Sheets
        if sheets_configured():
            ok, msg = save_lead(name=lname, email=lemail,
                role=wf.get("role",""), industry=wf.get("industry",""),
                total_hours=roi["total_hours_per_week"],
                time_saved=roi["time_saved_per_week"],
                efficiency=roi["efficiency_gain_percent"],
                auto_score=roi["automation_score"])
            if ok:
                st.success("✅ Contact saved to Google Sheets!")
            else:
                st.warning(f"⚠️ Sheets error: {msg} — saved to leads.csv instead")
        else:
            st.info("📄 Contact saved to leads.csv (Google Sheets not configured)")

        prog.progress(100, text="✅ Audit complete!")

        st.session_state["results"] = {
            "analysis": analysis, "roi": roi,
            "ai_content": ai_content, "paths": paths, "md_content": md_content,
        }
        st.success("✅ Audit complete! Click the **Audit Results** tab above to see your report.")
        st.balloons()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RESULTS
# ══════════════════════════════════════════════════════════════════════════════
with t_results:
    render_banner("Your Audit Results", "AI-powered analysis · ROI breakdown · Implementation plan · Downloadable report")
    if not st.session_state.get("results"):
        st.info("👈 Complete the form in **Run Your Audit** to see your results here.")
    else:


        R = st.session_state["results"]
        analysis, roi, ai_content = R["analysis"], R["roi"], R["ai_content"]
        paths, md_content = R["paths"], R["md_content"]
        workflow = analysis["input"]

        if ai_content["success"]:
            st.success(f"✅ AI-powered analysis — model: `{ai_content['model']}`")
        else:
            st.warning("⚠️ DeepSeek API unavailable — deterministic fallback used. Add your key in the sidebar.")

        st.markdown('<div class="sec-header">📈 ROI AT A GLANCE</div>', unsafe_allow_html=True)
        for col, (val, lbl) in zip(st.columns(5), [
            (f"{roi['time_saved_per_week']:.1f}h",   "Time Saved / Week"),
            (f"{roi['efficiency_gain_percent']}%",    "Efficiency Gain"),
            (f"{roi['automation_score']} / 100",      "Automation Score"),
            (f"{roi['annual_hours_saved']:.0f}h",     "Annual Hours Saved"),
            (f"${roi['annual_value_usd']:,.0f}",      "Annual Value"),
        ]):
            with col:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{val}</div>'
                            f'<div class="metric-label">{lbl}</div></div>', unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        lc, rc = st.columns([1.1, 0.9])

        with lc:
            st.markdown('<div class="sec-header">SECTION 1 — CURRENT WORKFLOW</div>', unsafe_allow_html=True)
            st.caption(f"**{workflow['role']}** | **{workflow['industry']}** | "
                       f"{analysis['total_weekly_hours']:.1f}h/week | Tools: {', '.join(workflow['tools_used']) or 'None'}")
            st.dataframe(pd.DataFrame([{
                "Task": ct["task"], "Hrs/Week": ct["hours"],
                "Category": ct["category"], "Reducible": f"{ct['reduction_factor']*100:.0f}%",
                "Saved": ct["time_saved"]}
                for ct in analysis["classified_tasks"]]),
                use_container_width=True, hide_index=True)

            st.markdown('<div class="sec-header">SECTION 2 — KEY INEFFICIENCIES</div>', unsafe_allow_html=True)
            if analysis["inefficiencies"]:
                for item in analysis["inefficiencies"]:
                    icon = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(item["severity"],"⚪")
                    with st.expander(f"{icon} [{item['severity']}] {item['task']}"):
                        st.markdown(f"**Reason:** {item['reason']}")
                        st.markdown(f"**Impact:** {item['impact']}")
            else:
                st.success("No major inefficiencies detected.")

        with rc:
            st.markdown('<div class="sec-header">SECTION 6 — ROI BREAKDOWN</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame([{
                "Category": cat, "Tasks": d["tasks"],
                "Current h/wk": d["total_hours"], "Hrs Saved": d["hours_saved"]}
                for cat, d in roi["category_breakdown"].items()]),
                use_container_width=True, hide_index=True)

            st.markdown('<div class="sec-header">AUTOMATION PRIORITIES</div>', unsafe_allow_html=True)
            for opp in analysis["automation_opportunities"]:
                icon = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(opp["priority"],"⚪")
                with st.expander(f"{icon} {opp['task']} — {opp['hours']:.1f}h/week"):
                    st.markdown(f"**Suggestion:** {opp['automation_suggestion']}")
                    st.markdown(f"**Priority:** `{opp['priority']}` | **Saved:** {opp['estimated_hours_saved']:.1f}h/week")

        st.divider()
        st.markdown('<div class="sec-header">🤖 AI ANALYSIS — SECTIONS 3, 4, 5 & 7</div>', unsafe_allow_html=True)
        st.markdown(ai_content["content"])
        st.divider()

        st.markdown('<div class="sec-header">📥 DOWNLOAD YOUR REPORTS</div>', unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇️ Download Markdown (.md)", data=md_content.encode(),
                file_name=f"audit_{paths['timestamp']}.md", mime="text/markdown",
                use_container_width=True)
        with d2:
            if paths.get("pdf") and os.path.exists(paths["pdf"]):
                with open(paths["pdf"],"rb") as f:
                    st.download_button("⬇️ Download PDF Report", data=f.read(),
                        file_name=f"audit_{paths['timestamp']}.pdf",
                        mime="application/pdf", use_container_width=True)

        with st.expander("🗂 Export raw JSON"):
            exp = {"workflow": workflow, "classified_tasks": analysis["classified_tasks"],
                   "inefficiencies": analysis["inefficiencies"], "roi": roi}
            st.download_button("⬇️ analysis.json", data=json.dumps(exp,indent=2).encode(),
                file_name=f"analysis_{paths['timestamp']}.json", mime="application/json")
            st.json(exp)


    # ══════════════════════════════════════════════════════════════════════════════
    # TAB 4 — CONTACT  (pure Streamlit, no HTML wrappers around native widgets)
    # ══════════════════════════════════════════════════════════════════════════════
with t_contact:
    render_banner("About the Creator", "Digital Solution · Jawad Hussain · CEO & AI Workflow Architect")

    # ── Profile card ──────────────────────────────────────────────────────────
    photo_col, info_col = st.columns([1, 2.2], gap="large")

    with photo_col:
        if os.path.exists(PHOTO_PATH):
            with open(PHOTO_PATH, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<img src="data:image/jpeg;base64,{b64}" '
                'style="width:170px;height:170px;border-radius:50%;object-fit:cover;' +
                'border:5px solid #1e3a8a;box-shadow:0 8px 24px rgba(30,58,138,0.25);' +
                'display:block;margin:0 auto 18px auto;"/>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="width:170px;height:170px;border-radius:50%;' +
                'background:linear-gradient(135deg,#1e3a8a,#2563eb);' +
                'display:flex;align-items:center;justify-content:center;' +
                'font-size:52px;font-weight:800;color:white;margin:0 auto 18px auto;">JH</div>',
                unsafe_allow_html=True)

        st.markdown(
            "<h3 style='text-align:center;margin:0 0 4px 0;color:#0f172a;font-size:1.2rem;'>Jawad Hussain</h3>"
            "<p style='text-align:center;color:#2563eb;font-weight:700;margin:0 0 4px 0;font-size:0.95rem;'>CEO — Digital Solution</p>"
            "<p style='text-align:center;color:#64748b;font-size:0.82rem;line-height:1.7;margin:0 0 16px 0;'>"
            "AI Workflow Architect<br/>Blockchain &amp; RWA Strategist<br/>"
            "LinkedIn Creator · 3,200+ Followers<br/>Digital Transformation Consultant</p>",
            unsafe_allow_html=True)

        st.link_button("💼  LinkedIn Profile", LINKEDIN_URL, use_container_width=True)
        st.markdown(
            f'<a href="mailto:{CONTACT_EMAIL}" style="display:block;text-align:center;' +
            'background:linear-gradient(135deg,#1e3a8a,#2563eb);color:white;' +
            'padding:9px 16px;border-radius:10px;font-weight:600;' +
            'text-decoration:none;margin-top:8px;font-size:0.9rem;">' +
            f'✉️  {CONTACT_EMAIL}</a>',
            unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(
            '<div style="background:#f0f7ff;border-radius:12px;padding:14px 16px;' +
            'border-left:4px solid #2563eb;font-size:0.82rem;color:#1e293b;line-height:1.7;">' +
            '<b>📍 Islamabad, Pakistan</b><br/>' +
            '🌐 Digital Solution<br/>' +
            '💬 DM open on LinkedIn<br/>' +
            '⚡ Responds within 24 hours</div>',
            unsafe_allow_html=True)

    with info_col:
        st.markdown("### 👋 About Jawad Hussain")
        st.markdown(
            "Jawad Hussain is the CEO and founder of **Digital Solution** — a platform dedicated to "
            "AI education, workflow automation, and digital transformation. With deep expertise across "
            "Agentic AI, Blockchain, and digital finance, Jawad helps founders, creators, and business "
            "owners replace slow, manual processes with intelligent, scalable systems.\n\n"
            "Having worked with professionals across industries — from solo creators to growing teams — "
            "Jawad brings a practical, results-first approach: no fluff, no generic advice. Every system "
            "is designed around your specific workflow, your tools, and your goals. The AI Workflow Auditor "
            "is one of the free tools built under Digital Solution to make that level of insight accessible to everyone.")

        st.divider()
        st.markdown("### 🎯 Areas of Expertise")
        col_a, col_b = st.columns(2)
        with col_a:
            for icon, title, desc in [
                ("🤖", "Agentic AI & Workflow Automation",
                 "Designing multi-agent AI pipelines that eliminate manual, repetitive tasks end-to-end — from content to client management."),
                ("🔗", "Blockchain & RWA Tokenisation",
                 "Building decentralised financial systems, real-world asset tokenisation frameworks, and digital currency strategies for businesses."),
                ("📈", "LinkedIn Growth & Personal Branding",
                 "Creating content systems and posting strategies that grow engaged audiences and generate consistent inbound leads on autopilot."),
            ]:
                with st.expander(f"{icon}  {title}"):
                    st.write(desc)
        with col_b:
            for icon, title, desc in [
                ("💹", "Trading, Stocks & Digital Finance",
                 "AI-assisted market analysis, financial modelling, investment frameworks, and digital asset strategy for individuals and funds."),
                ("🛠", "Digital Transformation for Businesses",
                 "Auditing and rebuilding fragmented manual workflows into AI-powered, scalable operating systems for founders and teams."),
                ("📊", "AI Tools & Content Systems",
                 "Building custom AI tool stacks, content pipelines, and automation workflows tailored to your specific role and industry."),
            ]:
                with st.expander(f"{icon}  {title}"):
                    st.write(desc)

        st.divider()
        st.markdown("### 📬 Work With Jawad")
        st.markdown(
            "Whether you need a **custom AI workflow audit**, a **done-for-you automation system**, "
            "a **blockchain strategy**, or simply want to discuss how AI can transform your business — "
            "Jawad is open to collaborations, consulting engagements, and speaking opportunities.")

        cta1, cta2, cta3 = st.columns(3)
        with cta1:
            st.markdown(
                '<div style="background:linear-gradient(135deg,#eff6ff,#dbeafe);border:1px solid #93c5fd;' +
                'border-radius:14px;padding:18px 16px;text-align:center;height:100%;">' +
                '<div style="font-size:1.6rem;margin-bottom:8px;">💬</div>' +
                '<b style="color:#1e3a8a;font-size:0.92rem;">DM on LinkedIn</b>' +
                '<p style="color:#475569;font-size:0.8rem;margin:6px 0 0 0;line-height:1.5;">' +
                'Send a message on LinkedIn and describe your challenge. ' +
                'Jawad responds within 24 hours.</p></div>',
                unsafe_allow_html=True)
        with cta2:
            st.markdown(
                '<div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1px solid #86efac;' +
                'border-radius:14px;padding:18px 16px;text-align:center;height:100%;">' +
                '<div style="font-size:1.6rem;margin-bottom:8px;">✉️</div>' +
                f'<b style="color:#166534;font-size:0.92rem;">Email Directly</b>' +
                f'<p style="color:#475569;font-size:0.8rem;margin:6px 0 0 0;line-height:1.5;">' +
                f'Drop an email to <b>{CONTACT_EMAIL}</b> with your workflow challenge ' +
                'or project brief and expect a reply within 24–48 hours.</p></div>',
                unsafe_allow_html=True)
        with cta3:
            st.markdown(
                '<div style="background:linear-gradient(135deg,#fefce8,#fef9c3);border:1px solid #fde047;' +
                'border-radius:14px;padding:18px 16px;text-align:center;height:100%;">' +
                '<div style="font-size:1.6rem;margin-bottom:8px;">📄</div>' +
                '<b style="color:#854d0e;font-size:0.92rem;">Send a PDF Brief</b>' +
                '<p style="color:#475569;font-size:0.8rem;margin:6px 0 0 0;line-height:1.5;">' +
                'Have a detailed plan or project? Attach a PDF brief to your email. ' +
                'Jawad will review and respond with a personalised plan within 48 hours.</p></div>',
                unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        st.info(
            f"💡 **Ready to transform your workflow?** Run a free audit using the **Run Your Audit** tab above, "
            f"then share the downloaded PDF report with Jawad at **{CONTACT_EMAIL}** or via LinkedIn DM. "
            "You'll get a personalised response with a recommended action plan within 48 hours.")

    st.divider()
    st.markdown(
        f'<div class="pg-footer">AI Workflow Auditor &nbsp;·&nbsp; Digital Solution &nbsp;·&nbsp; Jawad Hussain<br/>' +
        f'<a href="{LINKEDIN_URL}" target="_blank">LinkedIn</a> &nbsp;·&nbsp; ' +
        f'<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> &nbsp;·&nbsp; ' +
        'Islamabad, Pakistan</div>',
        unsafe_allow_html=True)
