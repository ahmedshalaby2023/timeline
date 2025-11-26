import streamlit as st
import datetime
import json
import random
import base64
from io import BytesIO
from uuid import uuid4
import pandas as pd


def rerun_app():
    rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun_fn is None:
        raise AttributeError("Streamlit rerun function not available")
    rerun_fn()

DEFAULT_TITLE = "Interactive Event Timeline with Lens Magnifier"

st.set_page_config(page_title="Event Timeline Lens", page_icon="⏱️", layout="wide")

if "timeline_title" not in st.session_state:
    st.session_state["timeline_title"] = DEFAULT_TITLE

st.title(st.session_state["timeline_title"])

# Initialize session state for events
if "events" not in st.session_state:
    st.session_state["events"] = []

# Sidebar for data entry
with st.sidebar:
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
        try:
            export_df.to_excel(excel_buffer, index=False, engine="openpyxl")
        except ModuleNotFoundError:
            excel_buffer = BytesIO()
            try:
                export_df.to_excel(excel_buffer, index=False, engine="xlsxwriter")
            except ModuleNotFoundError:
                st.error(
                    "Excel export requires the 'openpyxl' or 'XlsxWriter' package."
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

# HTML + CSS + JavaScript for the timeline
html_content = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <style>
    /* Page styles */
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: radial-gradient(circle at 15% 15%, #fefcea 0%, #f1da36 25%, #f0b800 55%, #f09900 100%);
    }}

    /* Lens overlay */
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

    /* Fog outside lens */
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


    @keyframes lensPulse {{
      0%, 100% {{
        box-shadow: 0 0 18px rgba(255, 255, 255, 0.45), inset 0 0 15px rgba(255, 255, 255, 0.2);
      }}
      50% {{
        box-shadow: 0 0 26px rgba(255, 255, 255, 0.6), inset 0 0 22px rgba(255, 255, 255, 0.26);
      }}
    }}

    /* Timeline container */
    #timeline-wrapper {{
      position: relative;
      width: 100%;
      overflow-x: scroll;
      overflow-y: hidden;
      white-space: nowrap;
      padding: 105px 50vw 80px; /* align bubbles and labels with enlarged lens center */
      box-sizing: border-box;
    }}

    /* Individual event */
    .event {{
      display: inline-block;
      width: 120px;
      margin: 0 60px;
      text-align: center;
      color: #ffffff;
      transition: transform 0.35s ease, box-shadow 0.35s ease;
      transform-origin: center center;
    }}

    /* Colored bubble */
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

    /* Magnification effect when in lens */
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

    @keyframes tremor {{
      0%, 100% {{ transform: scale(1.12) translate(0px, 0px); }}
      20% {{ transform: scale(1.12) translate(-1.5px, 1.2px); }}
      40% {{ transform: scale(1.12) translate(1.4px, -1px); }}
      60% {{ transform: scale(1.12) translate(-1px, -1.6px); }}
      80% {{ transform: scale(1.12) translate(1.6px, 1px); }}
      100% {{ transform: scale(1.12) translate(1.8px, 1px); }}
    }}

    .event.focused .label {{
      color: #ffffff;
    }}

    .event.focused .date {{
      color: rgba(255, 255, 255, 0.85);
    }}
  </style>
</head>
<body>
  <!-- Fog overlay -->
  <div id="fog"></div>

  <!-- Lens overlay -->
  <div id="lens"></div>

  <!-- Timeline container -->
  <div id="timeline-wrapper"></div>

  <script>
    // Event data from Streamlit
    const events = {events_json};
    events.sort((a, b) => new Date(a.date) - new Date(b.date));
    const wrapper = document.getElementById('timeline-wrapper');
    const eventElements = [];

    // Populate timeline with events
    events.forEach((ev, idx) => {{
      const eventDiv = document.createElement('div');
      eventDiv.className = 'event';
      eventDiv.dataset.id = ev.id;

      // Random but consistent color per event using idx
      const hue = (idx * 137.5) % 360; // Golden angle for decent color spread
      const color = `hsl(${{hue}}, 70%, 50%)`;
      eventDiv.style.setProperty('--color', color);

      // Event HTML
      const bubbleContent = ev.image 
        ? `<img src="data:image/png;base64,${{ev.image}}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">` 
        : '';
      const dateLabel = new Date(ev.date).toLocaleDateString(undefined, {{ year: 'numeric', month: 'short', day: 'numeric' }});
      eventDiv.innerHTML = `
        <div class="bubble">${{bubbleContent}}</div>
        <div class="label">${{ev.title}}</div>
        <div class="date">${{dateLabel}}</div>
      `;

      wrapper.appendChild(eventDiv);
      eventElements.push(eventDiv);
    }});

    // Lens center position
    let lensX = window.innerWidth / 2;

    function getScrollLeftForEvent(el) {{
      const wrapperRect = wrapper.getBoundingClientRect();
      const targetCenter = el.offsetLeft + el.offsetWidth / 2;
      const lensOffset = lensX - wrapperRect.left;
      return Math.max(0, targetCenter - lensOffset);
    }}

    // Helper to update focused state based on lens position
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

    // Initial check
    updateFocus();

    // Re-check whenever user scrolls or resizes
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

# Render the HTML component within Streamlit
st.components.v1.html(html_content, height=380, scrolling=True)
