import streamlit as st
import datetime
import json
import base64
import importlib.util
import subprocess
import sys
from io import BytesIO
from uuid import uuid4
import pandas as pd


def rerun_app():
    rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun_fn is None:
        raise AttributeError("Streamlit rerun function not available")
    rerun_fn()

DEFAULT_TITLE = "Interactive Event Timeline with Lens Magnifier"


@st.cache_resource
def ensure_excel_engine():
    """Ensure an Excel writer engine is available, attempting on-the-fly install if needed."""
    preferred_engines = ("openpyxl", "xlsxwriter")

    for engine in preferred_engines:
        if importlib.util.find_spec(engine) is not None:
            return engine

    missing = [engine for engine in preferred_engines if importlib.util.find_spec(engine) is None]
    if missing:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        except Exception as exc:
            st.warning(f"Automatic install of Excel export dependencies failed: {exc}")
            return None

    for engine in preferred_engines:
        if importlib.util.find_spec(engine) is not None:
            return engine

    return None

st.set_page_config(page_title="Event Timeline Lens", page_icon="⏱️", layout="wide")

if "timeline_title" not in st.session_state:
    st.session_state["timeline_title"] = DEFAULT_TITLE

# Visualization layout preference
if "timeline_view" not in st.session_state:
    st.session_state["timeline_view"] = "Orbit"

# Initialize session state for events
if "events" not in st.session_state:
    st.session_state["events"] = []

if "tour_trigger" not in st.session_state:
    st.session_state["tour_trigger"] = False

st.title(st.session_state["timeline_title"])

tour_trigger = False
if st.session_state["events"]:
    if st.button(
        "Play Prezi-style Tour",
        use_container_width=True,
        help="Animate the timeline with dynamic zoom-and-pan transitions."
    ):
        st.session_state["tour_trigger"] = True

    tour_trigger = st.session_state["tour_trigger"]
    st.session_state["tour_trigger"] = False
else:
    st.session_state["tour_trigger"] = False

# Sidebar for data entry
with st.sidebar:
    view_choice = st.radio(
        "Visualization Style",
        ("Timeline", "Orbit"),
        index=0 if st.session_state["timeline_view"] == "Timeline" else 1,
        help="Choose between a horizontal timeline or circular orbit layout."
    )
    st.session_state["timeline_view"] = view_choice

    st.session_state["timeline_title"] = st.text_input(
        "Timeline Title",
        value=st.session_state.get("timeline_title", DEFAULT_TITLE),
        help="Displayed at the top of the timeline."
    ) or DEFAULT_TITLE

    st.header("Add a New Event")
    title_input = st.text_input("Event Title")
    date_input = st.date_input("Event Date", datetime.date(2002, 1, 1), min_value=datetime.date(2002, 1, 1))
    image_file = st.file_uploader("Upload an image (optional)", type=["png", "jpg", "jpeg", "gif"])
    image_data = None
    if image_file:
        image_data = base64.b64encode(image_file.read()).decode()

    if st.button("Add Event"):
        if title_input:
            st.session_state["events"].append(
                {
                    "id": str(uuid4()),
                    "title": title_input,
                    "date": date_input.isoformat(),
                    "image": image_data,
                }
            )
            # Force a rerun so the timeline updates immediately
            rerun_app()
        else:
            st.warning("Please enter an event title before adding.")

    st.markdown("---")
    st.subheader("Import Events from Excel")
    excel_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls", "xlsb"], key="excel_uploader")
    if excel_file:
        try:
            ext = excel_file.name.split(".")[-1].lower()
            read_kwargs = {}
            if ext == "xlsb":
                read_kwargs["engine"] = "pyxlsb"
            df = pd.read_excel(excel_file, **read_kwargs)
            missing_cols = {"eventname", "eventdate"} - set(col.lower() for col in df.columns)
            if missing_cols:
                st.error("Excel file must contain columns: eventname, eventdate")
            else:
                normalized = {col.lower(): col for col in df.columns}
                new_events = []
                for _, row in df.iterrows():
                    name = row[normalized["eventname"]]
                    date_val = row[normalized["eventdate"]]
                    if pd.isna(name) or pd.isna(date_val):
                        continue
                    if isinstance(date_val, datetime.date):
                        date_iso = date_val.isoformat()
                    else:
                        try:
                            parsed_date = pd.to_datetime(date_val).date()
                            date_iso = parsed_date.isoformat()
                        except Exception:
                            continue
                    new_events.append(
                        {
                            "id": str(uuid4()),
                            "title": str(name),
                            "date": date_iso,
                            "image": None,
                        }
                    )
                if new_events:
                    st.session_state["events"].extend(new_events)
                    st.success(f"Imported {len(new_events)} events from Excel.")
                    rerun_app()
                else:
                    st.warning("No valid rows found to import.")
        except Exception as exc:
            st.error(f"Failed to read Excel file: {exc}")

# Editing existing events
with st.sidebar:
    st.header("Edit Previous Events")
    for idx, ev in enumerate(st.session_state["events"]):
        with st.expander(f"{ev['title']} - {ev['date']}", expanded=False):
            new_title = st.text_input(f"Title_{ev['id']}", ev["title"], key=f"title_{ev['id']}_edit")
            new_date = st.date_input(
                f"Date_{ev['id']}",
                datetime.date.fromisoformat(ev['date']),
                key=f"date_{ev['id']}_edit",
                min_value=datetime.date(2002, 1, 1)
            )
            new_image_file = st.file_uploader(
                "Replace image (optional)",
                type=["png", "jpg", "jpeg", "gif"],
                key=f"image_{ev['id']}_edit"
            )
            new_image_data = ev.get('image')
            if new_image_file:
                new_image_data = base64.b64encode(new_image_file.read()).decode()
            col1, col2 = st.columns(2)
            if col1.button("Save", key=f"save_{ev['id']}"):
                st.session_state['events'][idx]['title'] = new_title
                st.session_state['events'][idx]['date'] = new_date.isoformat()
                st.session_state['events'][idx]['image'] = new_image_data
                rerun_app()
            if col2.button("Delete", key=f"delete_{ev['id']}"):
                st.session_state['events'].pop(idx)
                rerun_app()

    st.markdown("---")
    st.subheader("Export Events to Excel")
    if st.session_state["events"]:
        sorted_export = sorted(
            st.session_state["events"],
            key=lambda e: datetime.date.fromisoformat(e["date"]),
        )
        export_rows = [
            {
                "eventname": ev["title"],
                "eventdate": ev["date"],
                "image": ev.get("image"),
            }
            for ev in sorted_export
        ]
        export_df = pd.DataFrame(export_rows)
        excel_buffer = BytesIO()

        engine = ensure_excel_engine()
        if engine is None:
            st.error(
                "Excel export requires the 'openpyxl' or 'XlsxWriter' package. "
                "Please install one of them in the deployment environment."
            )
            excel_buffer = None
        else:
            try:
                export_df.to_excel(excel_buffer, index=False, engine=engine)
            except ModuleNotFoundError:
                st.error(
                    "Excel export requires the 'openpyxl' or 'XlsxWriter' package. "
                    "Please install one of them in the deployment environment."
                )
                excel_buffer = None

        if excel_buffer is not None:
            st.download_button(
                label="Download events.xlsx",
                data=excel_buffer.getvalue(),
                file_name="timeline_events.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    else:
        st.info("Add events to enable exporting.")

# If no events, prompt the user and stop
if not st.session_state["events"]:
    st.info("Use the sidebar to add events. They will appear in a colorful, animated timeline!")
    st.stop()

# Sort events chronologically (oldest first)
sorted_events = sorted(
    st.session_state["events"],
    key=lambda e: datetime.date.fromisoformat(e["date"]),
)

# Serialize to JSON for JavaScript
events_json = json.dumps(sorted_events)
view_mode = st.session_state["timeline_view"]
tour_js_flag = "true" if tour_trigger else "false"

# HTML + CSS + JavaScript for the timeline
orbit_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <style>
    body {{
      margin: 0;
      position: relative;
      font-family: Arial, sans-serif;
      background: radial-gradient(circle at 15% 15%, #fefcea 0%, #f1da36 25%, #f0b800 55%, #f09900 100%);
      overflow: hidden;
    }}

    #fog {{
      position: absolute;
      inset: -25%;
      pointer-events: none;
      z-index: 50;
      background: radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0) 0px, rgba(255, 255, 255, 0.28) 220px, rgba(189, 206, 223, 0.6) 100%);
      filter: blur(12px);
      opacity: 0.75;
    }}

    #timeline-stage {{
      position: relative;
      width: 100%;
      height: 100%;
      min-height: 420px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 1.2s cubic-bezier(0.17, 0.84, 0.44, 1);
      transform-origin: center center;
      will-change: transform;
      z-index: 100;
    }}

    #orbit-container {{
      position: relative;
      width: min(90vw, 620px);
      height: min(90vw, 620px);
      max-width: 640px;
      max-height: 640px;
      aspect-ratio: 1;
    }}

    #orbit-ring {{
      position: absolute;
      inset: 6%;
      border-radius: 50%;
      border: 2px dashed rgba(255, 255, 255, 0.55);
      box-shadow: 0 0 20px rgba(255, 255, 255, 0.25);
      opacity: 0.9;
      animation: orbitGlow 6s ease-in-out infinite;
    }}

    @keyframes orbitGlow {{
      0%, 100% {{
        box-shadow: 0 0 20px rgba(255, 255, 255, 0.25);
        opacity: 0.85;
      }}
      50% {{
        box-shadow: 0 0 35px rgba(255, 255, 255, 0.45);
        opacity: 1;
      }}
    }}

    #orbit-core {{
      position: absolute;
      inset: 45%;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(255, 255, 255, 0.75) 0%, rgba(255, 255, 255, 0.05) 100%);
      box-shadow: 0 0 45px rgba(255, 255, 255, 0.35);
    }}

    #orbit-events {{
      position: absolute;
      inset: 0;
    }}

    .event {{
      position: absolute;
      width: 120px;
      text-align: center;
      color: #ffffff;
      pointer-events: auto;
      transform: translate(-50%, -50%) scale(0.82);
      transition: left 0.6s ease, top 0.6s ease, transform 0.4s ease;
    }}

    .event .bubble {{
      width: 70px;
      height: 70px;
      border-radius: 50%;
      margin: 0 auto;
      border: 2px solid rgba(255, 255, 255, 0.35);
      background: var(--color);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
      transition: border-color 0.35s ease, box-shadow 0.35s ease;
    }}

    .event .bubble img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      filter: saturate(0.65);
    }}

    .event .label {{
      margin-top: 10px;
      font-weight: 600;
      letter-spacing: 0.4px;
      color: rgba(255, 255, 255, 0.8);
    }}

    .event .date {{
      margin-top: 4px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.55);
    }}

    .event.tour-highlight {{
      z-index: 20;
      transform: translate(-50%, -50%) scale(1.2);
    }}

    .event.tour-highlight .bubble {{
      border-color: rgba(255, 255, 255, 0.95);
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.45);
    }}

    .event.tour-highlight .label {{
      color: #ffffff;
      text-shadow: 0 4px 12px rgba(0, 0, 0, 0.55);
    }}

    #lens {{
      position: absolute;
      width: 220px;
      height: 220px;
      border-radius: 50%;
      border: 3px solid rgba(255, 255, 255, 0.95);
      background: radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.05) 55%, rgba(255, 255, 255, 0) 100%);
      box-shadow: 0 0 25px rgba(0, 0, 0, 0.35), inset 0 0 18px rgba(255, 255, 255, 0.3);
      pointer-events: none;
      transform: translate(-50%, -50%);
      transition: left 0.6s ease, top 0.6s ease, opacity 0.6s ease;
      z-index: 30;
      opacity: 0;
    }}

    #lens.visible {{
      opacity: 1;
    }}
  </style>
</head>
<body>
  <div id="fog"></div>
  <div id="timeline-stage">
    <div id="orbit-container">
      <div id="orbit-ring"></div>
      <div id="orbit-core"></div>
      <div id="orbit-events"></div>
      <div id="lens"></div>
    </div>
  </div>
  <script>
    const events = {events_json};
    const tourTrigger = {tour_js_flag};
    events.sort((a, b) => new Date(a.date) - new Date(b.date));

    const stage = document.getElementById('timeline-stage');
    const orbitContainer = document.getElementById('orbit-container');
    const eventsHost = document.getElementById('orbit-events');
    const lens = document.getElementById('lens');
    const eventElements = [];
    const baseAngles = [];

    events.forEach((ev, idx) => {{
      const eventDiv = document.createElement('div');
      eventDiv.className = 'event';
      eventDiv.dataset.index = idx;

      const hue = (idx * 137.5) % 360;
      const color = `hsl(${{hue}}, 70%, 50%)`;
      eventDiv.style.setProperty('--color', color);

      const bubbleContent = ev.image
        ? `<img src="data:image/png;base64,${{ev.image}}" alt="${{ev.title}}" />`
        : '';
      const dateLabel = new Date(ev.date).toLocaleDateString(undefined, {{ year: 'numeric', month: 'short', day: 'numeric' }});

      eventDiv.innerHTML = `
        <div class="bubble">${{bubbleContent}}</div>
        <div class="label">${{ev.title}}</div>
        <div class="date">${{dateLabel}}</div>
      `;

      eventsHost.appendChild(eventDiv);
      eventElements.push(eventDiv);
    }});

    const TWO_PI = Math.PI * 2;
    const TOP_ALIGNMENT = -Math.PI / 2;
    const count = eventElements.length;

    eventElements.forEach((el, idx) => {{
      const angle = count ? TWO_PI * idx / count : 0;
      baseAngles.push(angle);
      el.dataset.baseAngle = angle;
    }});

    let orbitRadius = 0;
    let center = {{ x: 0, y: 0 }};
    let currentOffset = 0;

    function highlightEvent(target) {{
      eventElements.forEach(el => el.classList.remove('tour-highlight'));
      if (target) {{
        target.classList.add('tour-highlight');
      }}
    }}

    function renderOrbit(offset = currentOffset) {{
      currentOffset = offset;
      eventElements.forEach((el, idx) => {{
        const angle = baseAngles[idx] + currentOffset;
        const x = center.x + orbitRadius * Math.cos(angle);
        const y = center.y + orbitRadius * Math.sin(angle);
        el.dataset.currentAngle = angle;
        el.style.left = `${{x}}px`;
        el.style.top = `${{y}}px`;
      }});
    }}

    function updateLensPosition() {{
      if (!eventElements.length) {{
        lens.classList.remove('visible');
        return;
      }}
      const lensOffset = orbitRadius * 0.75;
      lens.style.left = `${{center.x}}px`;
      lens.style.top = `${{center.y - lensOffset}}px`;
      lens.classList.add('visible');
    }}

    function recalcGeometry() {{
      const rect = orbitContainer.getBoundingClientRect();
      const size = Math.min(rect.width, rect.height);
      orbitRadius = eventElements.length ? Math.max(size / 2 - 110, size / 4) : 0;
      center = {{ x: rect.width / 2, y: rect.height / 2 }};
      updateLensPosition();
      renderOrbit(currentOffset);
    }}

    function focusEvent(el, {{ highlight = true }} = {{}}) {{
      if (!el) {{
        return;
      }}
      const baseAngle = parseFloat(el.dataset.baseAngle);
      const offset = TOP_ALIGNMENT - baseAngle;
      renderOrbit(offset);
      if (highlight) {{
        highlightEvent(el);
      }}
      stage.style.transform = 'scale(1.2) translateY(-14px)';
    }}

    function focusOverview() {{
      renderOrbit(0);
      highlightEvent(null);
      stage.style.transform = 'scale(1) translateY(0px)';
    }}

    let tourScenes = [];
    function rebuildScenes() {{
      tourScenes = eventElements.map(el => ({{ element: el }}));
      if (eventElements.length) {{
        tourScenes.push({{ overview: true }});
      }}
    }}

    eventElements.forEach(el => {{
      el.addEventListener('mouseenter', () => {{
        focusEvent(el);
      }});
      el.addEventListener('click', () => {{
        focusEvent(el);
      }});
    }});

    function runTourAnimation() {{
      if (!tourScenes.length) {{
        return;
      }}
      let index = 0;
      const highlightDuration = 2600;

      const step = () => {{
        const scene = tourScenes[index];
        if (!scene) return;

        if (scene.overview) {{
          focusOverview();
        }} else {{
          focusEvent(scene.element);
        }}

        index += 1;
        if (index < tourScenes.length) {{
          setTimeout(step, highlightDuration);
        }} else {{
          setTimeout(() => {{
            focusOverview();
          }}, highlightDuration);
        }}
      }};

      setTimeout(step, 600);
    }}

    function handleResize() {{
      recalcGeometry();
    }}

    window.addEventListener('resize', () => {{
      window.requestAnimationFrame(handleResize);
    }});

    recalcGeometry();
    rebuildScenes();
    focusOverview();
    if (tourTrigger) {{
      setTimeout(runTourAnimation, 500);
    }}
  </script>
</body>
</html>
"""

timeline_html = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: radial-gradient(circle at 15% 15%, #fefcea 0%, #f1da36 25%, #f0b800 55%, #f09900 100%);
      overflow: hidden;
    }}

    #fog {{
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 950;
      background: radial-gradient(circle at 50% 150px, rgba(255, 255, 255, 0) 0px, rgba(255, 255, 255, 0) 130px, rgba(218, 226, 234, 0.32) 190px, rgba(201, 210, 220, 0.6) 100%);
      backdrop-filter: blur(6px) saturate(0.8);
      -webkit-backdrop-filter: blur(6px) saturate(0.8);
      mask: radial-gradient(circle at 50% 150px, transparent 130px, rgba(0, 0, 0, 0.9) 200px, rgba(0, 0, 0, 1) 100%);
      -webkit-mask: radial-gradient(circle at 50% 150px, transparent 130px, rgba(0, 0, 0, 0.9) 200px, rgba(0, 0, 0, 1) 100%);
    }}

    #lens {{
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      width: 240px;
      height: 240px;
      border-radius: 50%;
      border: 3px solid rgba(255, 255, 255, 0.95);
      background: radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0.05) 45%, rgba(255, 255, 255, 0.01) 70%, rgba(255, 255, 255, 0) 100%);
      backdrop-filter: blur(0.5px) saturate(1.1);
      box-shadow: 0 0 18px rgba(255, 255, 255, 0.45), inset 0 0 12px rgba(255, 255, 255, 0.18);
      pointer-events: none;
      z-index: 1000;
      overflow: hidden;
      animation: lensPulse 5s ease-in-out infinite;
    }}

    #lens::before {{
      content: "";
      position: absolute;
      inset: 20px;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.75) 0%, rgba(255, 255, 255, 0.35) 25%, rgba(255, 255, 255, 0.02) 70%);
      mix-blend-mode: screen;
      opacity: 0.78;
      pointer-events: none;
    }}

    @keyframes lensPulse {{
      0%, 100% {{
        box-shadow: 0 0 18px rgba(255, 255, 255, 0.45), inset 0 0 15px rgba(255, 255, 255, 0.2);
      }}
      50% {{
        box-shadow: 0 0 26px rgba(255, 255, 255, 0.6), inset 0 0 22px rgba(255, 255, 255, 0.26);
      }}
    }}

    #timeline-stage {{
      position: relative;
      width: 100%;
      overflow: hidden;
      padding-top: 120px;
      transition: transform 1.2s cubic-bezier(0.17, 0.84, 0.44, 1);
      transform-origin: center top;
      will-change: transform;
    }}

    #timeline-wrapper {{
      position: relative;
      width: 100%;
      overflow-x: scroll;
      overflow-y: hidden;
      white-space: nowrap;
      padding: 30px 50vw 60px;
      box-sizing: border-box;
      scroll-behavior: smooth;
    }}

    .event {{
      display: inline-block;
      width: 120px;
      margin: 0 60px;
      text-align: center;
      color: #ffffff;
      transition: transform 0.35s ease, box-shadow 0.35s ease;
      transform-origin: center center;
    }}

    .bubble {{
      width: 70px;
      height: 70px;
      border-radius: 50%;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
      border: 2px solid rgba(255, 255, 255, 0.35);
      background: var(--color);
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
      transition: border-color 0.35s ease, box-shadow 0.35s ease;
    }}

    .bubble::before {{
      content: "";
      position: absolute;
      inset: -40%;
      background: var(--color);
      filter: blur(25px);
      opacity: 0.75;
      transform: scale(1.2);
      transition: opacity 0.35s ease;
      pointer-events: none;
    }}

    .bubble::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(150deg, rgba(255, 255, 255, 0.8) 0%, rgba(255, 255, 255, 0.25) 55%, rgba(255, 255, 255, 0.05) 100%);
      opacity: 0.9;
      transition: opacity 0.35s ease;
      pointer-events: none;
    }}

    .bubble img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      filter: blur(8px) saturate(0.55);
      transform: scale(1.12);
      transition: filter 0.35s ease, transform 0.35s ease;
      animation: tremor 1.4s infinite ease-in-out;
    }}

    .label {{
      margin-top: 10px;
      font-weight: bold;
      color: rgba(255, 255, 255, 0.75);
      transition: color 0.35s ease;
    }}

    .date {{
      margin-top: 4px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.55);
      letter-spacing: 0.4px;
      transition: color 0.35s ease;
    }}

    .event.focused {{
      transform: scale(2.0);
      z-index: 10;
    }}

    .event.focused .bubble {{
      border-color: rgba(255, 255, 255, 0.9);
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.35);
    }}

    .event.focused .bubble::before,
    .event.focused .bubble::after {{
      opacity: 0;
    }}

    .event.focused .bubble img {{
      filter: blur(0) saturate(1);
      transform: scale(1);
      animation: none;
    }}

    .event.tour-highlight {{
      transform: scale(2.6) rotate(-2deg) translateY(-12px);
      z-index: 15;
    }}

    .event.tour-highlight .bubble {{
      border-color: rgba(255, 255, 255, 0.95);
      box-shadow: 0 14px 45px rgba(0, 0, 0, 0.45);
    }}

    .event.tour-highlight .bubble::before,
    .event.tour-highlight .bubble::after {{
      opacity: 0;
    }}

    .event.tour-highlight .bubble img {{
      filter: blur(0) saturate(1.1);
      transform: scale(1);
      animation: none;
    }}

    .event.tour-highlight .label {{
      color: #ffffff;
      text-shadow: 0 6px 18px rgba(0, 0, 0, 0.55);
    }}

    .event.tour-highlight .date {{
      color: rgba(255, 255, 255, 0.92);
    }}

    @keyframes tremor {{
      0%, 100% {{ transform: scale(1.12) translate(0px, 0px); }}
      20% {{ transform: scale(1.12) translate(-1.5px, 1.2px); }}
      40% {{ transform: scale(1.12) translate(1.4px, -1px); }}
      60% {{ transform: scale(1.12) translate(-1px, -1.6px); }}
      80% {{ transform: scale(1.12) translate(1.6px, 1px); }}
      100% {{ transform: scale(1.12) translate(1.8px, 1px); }}
    }}
  </style>
</head>
<body>
  <div id=\"fog\"></div>
  <div id=\"lens\"></div>
  <div id=\"timeline-stage\">
    <div id=\"timeline-wrapper\"></div>
  </div>
  <script>
    const events = {events_json};
    const tourTrigger = {tour_js_flag};
    events.sort((a, b) => new Date(a.date) - new Date(b.date));
    const wrapper = document.getElementById('timeline-wrapper');
    const stage = document.getElementById('timeline-stage');
    const eventElements = [];

    events.forEach((ev, idx) => {{
      const eventDiv = document.createElement('div');
      eventDiv.className = 'event';
      eventDiv.dataset.id = ev.id;

      const hue = (idx * 137.5) % 360;
      const color = `hsl(${{hue}}, 70%, 50%)`;
      eventDiv.style.setProperty('--color', color);

      const bubbleContent = ev.image 
        ? `<img src=\"data:image/png;base64,${{ev.image}}\" style=\"width:100%;height:100%;object-fit:cover;border-radius:50%;\">`
        : '';
      const dateLabel = new Date(ev.date).toLocaleDateString(undefined, {{ year: 'numeric', month: 'short', day: 'numeric' }});
      eventDiv.innerHTML = `
        <div class=\"bubble\">${{bubbleContent}}</div>
        <div class=\"label\">${{ev.title}}</div>
        <div class=\"date\">${{dateLabel}}</div>
      `;

      wrapper.appendChild(eventDiv);
      eventElements.push(eventDiv);
    }});

    let lensX = window.innerWidth / 2;

    function getScrollLeftForEvent(el) {{
      const wrapperRect = wrapper.getBoundingClientRect();
      const targetCenter = el.offsetLeft + el.offsetWidth / 2;
      const lensOffset = lensX - wrapperRect.left;
      return Math.max(0, targetCenter - lensOffset);
    }}

    function updateFocus() {{
      document.querySelectorAll('.event').forEach(el => {{
        const rect = el.getBoundingClientRect();
        const center = rect.left + rect.width / 2;
        if (Math.abs(center - lensX) < 120) {{
          el.classList.add('focused');
        }} else {{
          el.classList.remove('focused');
        }}
      }});
    }}

    updateFocus();

    wrapper.addEventListener('scroll', () => {{
      updateFocus();
    }});

    window.addEventListener('resize', () => {{
      lensX = window.innerWidth / 2;
      updateFocus();
    }});

    const tourScenes = eventElements.map((el, idx) => ({{
      element: el,
      scale: 1.35 + (idx % 3) * 0.25,
      rotate: (idx % 2 === 0 ? -4 : 4),
      translateY: idx % 2 === 0 ? -14 : 10
    }}));

    if (eventElements.length) {{
      tourScenes.push({{
        element: null,
        scale: 1,
        rotate: 0,
        translateY: 0,
        overview: true
      }});
    }}

    function runTourAnimation() {{
      if (!eventElements.length) {{
        return;
      }}

      wrapper.style.scrollBehavior = 'smooth';
      stage.style.transform = 'scale(1) rotate(0deg) translateY(0px)';

      let index = 0;
      const highlightDuration = 2600;

      const step = () => {{
        eventElements.forEach(el => el.classList.remove('tour-highlight'));
        const scene = tourScenes[index];

        if (!scene) {{
          return;
        }}

        if (scene.element) {{
          const scrollLeft = getScrollLeftForEvent(scene.element);
          wrapper.scrollTo({{ left: scrollLeft, behavior: 'smooth' }});
          scene.element.classList.add('tour-highlight');
        }} else {{
          const centerScroll = Math.max(0, (wrapper.scrollWidth - wrapper.clientWidth) / 2);
          wrapper.scrollTo({{ left: centerScroll, behavior: 'smooth' }});
        }}

        stage.style.transform = `scale(${{scene.scale}}) rotate(${{scene.rotate}}deg) translateY(${{scene.translateY || 0}}px)`;

        index += 1;
        if (index < tourScenes.length) {{
          setTimeout(step, highlightDuration);
        }} else {{
          setTimeout(() => {{
            eventElements.forEach(el => el.classList.remove('tour-highlight'));
            stage.style.transform = 'scale(1) rotate(0deg) translateY(0px)';
          }}, highlightDuration);
        }}
      }};

      setTimeout(step, 600);
    }}

    if (tourTrigger) {{
      setTimeout(runTourAnimation, 400);
    }}
  </script>
</body>
</html>
"""

if view_mode == "Orbit":
    st.components.v1.html(orbit_html, height=520, scrolling=False)
else:
    st.components.v1.html(timeline_html, height=400, scrolling=True)
