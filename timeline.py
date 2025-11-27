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

st.set_page_config(
    page_title="Event Timeline Lens",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "timeline_title" not in st.session_state:
    st.session_state["timeline_title"] = DEFAULT_TITLE

# Visualization layout preference
if "timeline_view" not in st.session_state:
    st.session_state["timeline_view"] = "Orbit"

# Initialize session state for events
if "events" not in st.session_state:
    st.session_state["events"] = []


st.title(st.session_state["timeline_title"])


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

    # Background color picker for horizontal timeline
    if "timeline_bg_color" not in st.session_state:
        st.session_state["timeline_bg_color"] = "#fefcea"
    
    timeline_bg_color = st.color_picker(
        "Timeline Background Color",
        value=st.session_state["timeline_bg_color"],
        help="Set the background color for the horizontal timeline view."
    )
    st.session_state["timeline_bg_color"] = timeline_bg_color

    # Event title styling options
    if "event_title_color" not in st.session_state:
        st.session_state["event_title_color"] = "#ffffff"
    
    if "event_title_font" not in st.session_state:
        st.session_state["event_title_font"] = "Arial"
    
    if "event_title_size" not in st.session_state:
        st.session_state["event_title_size"] = 12
    
    st.markdown("### Event Title Styling")
    
    event_title_color = st.color_picker(
        "Title Color",
        value=st.session_state["event_title_color"],
        help="Set the color of event titles."
    )
    st.session_state["event_title_color"] = event_title_color
    
    event_title_font = st.selectbox(
        "Title Font",
        options=["Arial", "Helvetica", "Times New Roman", "Georgia", "Verdana", "Courier New", "Impact", "Comic Sans MS"],
        index=["Arial", "Helvetica", "Times New Roman", "Georgia", "Verdana", "Courier New", "Impact", "Comic Sans MS"].index(st.session_state["event_title_font"]),
        help="Choose the font for event titles."
    )
    st.session_state["event_title_font"] = event_title_font
    
    event_title_size = st.slider(
        "Title Size (px)",
        min_value=8,
        max_value=24,
        value=st.session_state["event_title_size"],
        help="Set the font size for event titles in pixels."
    )
    st.session_state["event_title_size"] = event_title_size

    # Event date styling options
    if "event_date_color" not in st.session_state:
        st.session_state["event_date_color"] = "#ffffff"
    
    if "event_date_font" not in st.session_state:
        st.session_state["event_date_font"] = "Arial"
    
    if "event_date_size" not in st.session_state:
        st.session_state["event_date_size"] = 10
    
    event_date_color = st.color_picker(
        "Date Color",
        value=st.session_state["event_date_color"],
        help="Set the color of event dates."
    )
    st.session_state["event_date_color"] = event_date_color
    
    event_date_font = st.selectbox(
        "Date Font",
        options=["Arial", "Helvetica", "Times New Roman", "Georgia", "Verdana", "Courier New", "Impact", "Comic Sans MS"],
        index=["Arial", "Helvetica", "Times New Roman", "Georgia", "Verdana", "Courier New", "Impact", "Comic Sans MS"].index(st.session_state["event_date_font"]),
        help="Choose the font for event dates."
    )
    st.session_state["event_date_font"] = event_date_font
    
    event_date_size = st.slider(
        "Date Size (px)",
        min_value=6,
        max_value=18,
        value=st.session_state["event_date_size"],
        help="Set the font size for event dates in pixels."
    )
    st.session_state["event_date_size"] = event_date_size

    # Lens styling options
    if "lens_size" not in st.session_state:
        st.session_state["lens_size"] = 240
    
    lens_size = st.slider(
        "Lens Size (px)",
        min_value=120,
        max_value=400,
        value=st.session_state["lens_size"],
        help="Set the size of the lens in pixels."
    )
    st.session_state["lens_size"] = lens_size

    st.header("Add a New Event")
    title_input = st.text_input("Event Title")
    date_input = st.date_input("Event Date", datetime.date(2002, 1, 1), min_value=datetime.date(2002, 1, 1), max_value=datetime.date.today())
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
    st.info("Excel file must contain columns named 'eventname' and 'eventdate' (case-insensitive)")
    excel_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls", "xlsb"], key="excel_uploader")
    if excel_file:
        try:
            ext = excel_file.name.split(".")[-1].lower()
            read_kwargs = {}
            if ext == "xlsb":
                if importlib.util.find_spec("pyxlsb") is None:
                    st.error("pyxlsb package is required for .xlsb files. Please install it with: pip install pyxlsb")
                    st.stop()
                read_kwargs["engine"] = "pyxlsb"
            
            st.info(f"Reading Excel file: {excel_file.name}")
            df = pd.read_excel(excel_file, **read_kwargs)
            
            # Show file info
            st.write(f"Found {len(df)} rows in Excel file")
            st.write("Columns found:", df.columns.tolist())
            
            missing_cols = {"eventname", "eventdate"} - set(col.lower() for col in df.columns)
            if missing_cols:
                st.error(f"Excel file must contain columns: eventname, eventdate. Missing: {missing_cols}")
                st.write("Available columns:", [col for col in df.columns])
            else:
                normalized = {col.lower(): col for col in df.columns}
                new_events = []
                skipped_count = 0
                duplicate_count = 0
                
                # Get existing events for duplicate checking
                existing_events = set()
                for ev in st.session_state["events"]:
                    key = (ev["title"].lower().strip(), ev["date"])
                    existing_events.add(key)
                
                for idx, row in df.iterrows():
                    name = row[normalized["eventname"]]
                    date_val = row[normalized["eventdate"]]
                    
                    if pd.isna(name) or pd.isna(date_val):
                        skipped_count += 1
                        continue
                        
                    try:
                        # Handle pandas Timestamp objects (most common from Excel)
                        if hasattr(date_val, 'date'):
                            parsed_date = date_val.date()
                        # Handle datetime objects
                        elif isinstance(date_val, datetime.datetime):
                            parsed_date = date_val.date()
                        # Handle date objects
                        elif isinstance(date_val, datetime.date):
                            parsed_date = date_val
                        # Handle string dates
                        else:
                            parsed_date = pd.to_datetime(date_val).date()
                        
                        # Validate minimum date constraint
                        if parsed_date < datetime.date(2002, 1, 1):
                            st.warning(f"Row {idx+1}: Skipping event '{name}' - date {parsed_date} is before minimum allowed date (2002-01-01)")
                            skipped_count += 1
                            continue
                            
                        date_iso = parsed_date.isoformat()
                    except Exception as e:
                        st.warning(f"Row {idx+1}: Skipping event '{name}' - invalid date format: {date_val}")
                        skipped_count += 1
                        continue
                    
                    # Check for duplicates
                    event_key = (str(name).lower().strip(), date_iso)
                    if event_key in existing_events:
                        duplicate_count += 1
                        continue
                        
                    existing_events.add(event_key)
                        
                    new_events.append(
                        {
                            "id": str(uuid4()),
                            "title": str(name).strip(),
                            "date": date_iso,
                            "image": None,
                        }
                    )
                
                if new_events:
                    st.session_state["events"].extend(new_events)
                    st.success(f"Successfully imported {len(new_events)} events from Excel.")
                    if skipped_count > 0:
                        st.info(f"Skipped {skipped_count} rows due to missing data or invalid dates")
                    if duplicate_count > 0:
                        st.info(f"Skipped {duplicate_count} duplicate events that already exist")
                    # Clear the file uploader to prevent re-importing on rerun
                    st.session_state["excel_uploader"] = None
                    st.rerun()
                else:
                    st.warning("No valid rows found to import. Check that your Excel file has proper eventname and eventdate columns.")
        except Exception as exc:
            st.error(f"Failed to read Excel file: {exc}")
            st.write("Please ensure your Excel file is not corrupted and has the correct format.")

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
                min_value=datetime.date(2002, 1, 1),
                max_value=datetime.date.today()
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
      background: {st.session_state["timeline_bg_color"]};
      overflow: hidden;
    }}

    #orbit-container {{
      position: relative;
      width: 100%;
      height: 100vh;
      max-width: none;
      max-height: none;
      aspect-ratio: auto;
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
      z-index: 30;
    }}

    .event {{
      position: absolute;
      width: 120px;
      text-align: center;
      color: #ffffff;
      pointer-events: auto;
      transform: translate(-50%, -50%) scale(0.82);
      transition: left 0.6s ease, top 0.6s ease, transform 0.4s ease;
      z-index: 40;
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
      color: {st.session_state["event_title_color"]};
      font-family: {st.session_state["event_title_font"]};
      font-size: {st.session_state["event_title_size"]}px;
      white-space: normal;
      word-wrap: break-word;
      line-height: 1.2;
    }}

    .event .date {{
      margin-top: 4px;
      font-size: {st.session_state["event_date_size"]}px;
      color: {st.session_state["event_date_color"]};
      font-family: {st.session_state["event_date_font"]};
    }}

    .event.tour-highlight {{
      z-index: 60;
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
      width: {st.session_state["lens_size"]}px;
      height: {st.session_state["lens_size"]}px;
      border-radius: 50%;
      border: 2px solid rgba(255, 255, 255, 0.6);
      background: transparent;
      background-color: transparent !important;
      mix-blend-mode: normal;
      filter: none;
      box-shadow: none;
      pointer-events: none;
      transform: translate(-50%, -50%);
      transition: left 0.6s ease, top 0.6s ease, opacity 0.6s ease;
      z-index: 5;
      opacity: 0;
      overflow: visible;
    }}

    #lens.visible {{
      opacity: 1;
    }}
  </style>
</head>
<body>
  <div id="orbit-container">
      <div id="orbit-ring"></div>
      <div id="orbit-core"></div>
      <div id="orbit-events"></div>
      <div id="lens"></div>
    </div>
  <script>
    const events = {events_json};
    events.sort((a, b) => new Date(a.date) - new Date(b.date));

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

    function focusEvent(el) {{
      if (!el) {{
        return;
      }}
      const baseAngle = parseFloat(el.dataset.baseAngle);
      const offset = TOP_ALIGNMENT - baseAngle;
      renderOrbit(offset);
      orbitContainer.style.transform = 'scale(1.2) translateY(-14px)';
    }}

    function focusOverview() {{
      renderOrbit(0);
      orbitContainer.style.transform = 'scale(1) translateY(0px)';
    }}


    eventElements.forEach(el => {{
      el.addEventListener('mouseenter', () => {{
        focusEvent(el);
      }});
      el.addEventListener('click', () => {{
        focusEvent(el);
      }});
    }});


    function handleResize() {{
      recalcGeometry();
    }}

    window.addEventListener('resize', () => {{
      window.requestAnimationFrame(handleResize);
    }});

    recalcGeometry();
    focusOverview();
  </script>
</body>
</html>
"""

timeline_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: {st.session_state["timeline_bg_color"]};
      overflow: hidden;
    }}

    #lens {{
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      width: {st.session_state["lens_size"]}px;
      height: {st.session_state["lens_size"]}px;
      border-radius: 50%;
      border: 2px solid rgba(255, 255, 255, 0.6);
      background: transparent;
      background-color: transparent !important;
      mix-blend-mode: normal;
      filtered: none;
      box-shadow: none;
      pointer-events: none;
      z-index: 1000;
      overflow: visible;
    }}

    #lens::before,
    #lens::after {{
      content: none;
    }}

    #timeline-wrapper {{
      position: relative;
      width: 100%;
      overflow-x: auto;
      overflow-y: hidden;
      white-space: nowrap;
      padding: 30px 50vw 60px;
      box-sizing: border-box;
      scroll-behavior: smooth;
      -ms-overflow-style: none;
      scrollbar-width: none;
    }}

    #timeline-wrapper::-webkit-scrollbar {{
      display: none;
    }}

    .event {{
      display: inline-block;
      width: 120px;
      margin: 0 60px;
      text-align: center;
      color: #ffffff;
      transition: transform 0.35s ease, box-shadow 0.35s ease;
      transform-origin: center center;
      transform: translateY(0) scale(1);
      z-index: 1500;
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
      color: {st.session_state["event_title_color"]};
      transition: color 0.35s ease;
      font-family: {st.session_state["event_title_font"]};
      font-size: {st.session_state["event_title_size"]}px;
      white-space: normal;
      word-wrap: break-word;
      line-height: 1.2;
    }}

    .date {{
      margin-top: 4px;
      font-size: {st.session_state["event_date_size"]}px;
      color: {st.session_state["event_date_color"]};
      font-family: {st.session_state["event_date_font"]};
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


    .event.hovering {{
      transform: translateY(-28px) scale(calc({st.session_state["lens_size"]} / 120));
      z-index: 2000;
    }}

    .event.hovering .bubble {{
      border-color: rgba(255, 255, 255, 0.85);
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.35);
    }}

    .event.hovering .label {{
      color: #ffffff;
    }}

    .event.hovering .date {{
      color: rgba(255, 255, 255, 0.75);
    }}

    .event.hovering.focused {{
      transform: translateY(-28px) scale(calc({st.session_state["lens_size"]} / 80));
      z-index: 2500;
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
  <div id="lens"></div>
  <div id="timeline-wrapper"></div>
  <script>
    const events = {events_json};
    events.sort((a, b) => new Date(a.date) - new Date(b.date));
    const wrapper = document.getElementById('timeline-wrapper');
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

      eventDiv.addEventListener('mouseenter', () => {{
        eventDiv.classList.add('hovering');
        const targetScroll = getScrollLeftForEvent(eventDiv);
        wrapper.scrollTo({{ left: targetScroll, behavior: 'smooth' }});
      }});

      eventDiv.addEventListener('mouseleave', () => {{
        eventDiv.classList.remove('hovering');
      }});

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
        const lensRadius = {st.session_state["lens_size"]} / 2;
        if (Math.abs(center - lensX) < lensRadius * 0.6) {{
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

  </script>
</body>
</html>
"""

if view_mode == "Orbit":
    st.components.v1.html(orbit_html, height=520, scrolling=False)
else:
    st.components.v1.html(timeline_html, height=400, scrolling=True)
