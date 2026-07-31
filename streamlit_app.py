import streamlit as st
import pandas as pd
import json
import datetime
import os

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime, pd.Timestamp)):
            return obj.strftime('%Y-%m-%d') if hasattr(obj, 'strftime') else obj.isoformat()
        return super().default(obj)

# Set page config
st.set_page_config(
    page_title="UF Academic Deadlines Hub",
    page_icon="🐊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styles
st.markdown("""
<style>
    .main-title {
        color: #FF4A00;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.1rem;
    }
    .sub-title {
        color: #0021A5;
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #FF4A00;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .code-box {
        font-family: monospace;
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Helper to load data
@st.cache_data
def load_data(filename):
    path = os.path.join('data', filename)
    if os.path.exists(path):
        if filename.endswith('.json'):
            return pd.read_json(path, convert_dates=False)
        elif filename.endswith('.csv'):
            return pd.read_csv(path)
    return None

@st.cache_data
def get_last_update():
    path = os.path.join('data', 'last_update.txt')
    if os.path.exists(path):
        with open(path, 'r') as f:
            raw_ts = f.read().strip()
            # Convert ISO to nice string
            try:
                dt = datetime.datetime.fromisoformat(raw_ts)
                return dt.strftime('%B %d, %Y at %I:%M %p UTC')
            except:
                return raw_ts
    return "Unknown"

# Load Master Data
df_calendar = load_data('calendar.json')
last_update = get_last_update()

# Title Section
st.markdown('<div class="main-title">🐊 University of Florida Academic Deadlines</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">Automated, normalized, and real-time dates database • Last updated: {last_update}</div>', unsafe_allow_html=True)

if df_calendar is None or df_calendar.empty:
    st.error("No academic calendar data found. Please run the scraping script first.")
else:
    # Pre-process dates
    df_calendar['date_dt'] = pd.to_datetime(df_calendar['date']).dt.date
    df_calendar['end_date_dt'] = pd.to_datetime(df_calendar['end_date']).dt.date

    today = datetime.date.today()

    # Determine default term based on current date
    term_bounds = []
    for term_name in df_calendar['term'].unique():
        term_df = df_calendar[df_calendar['term'] == term_name]
        classes_begin = term_df[term_df['event'].str.contains('Classes Begin', case=False, na=False)]
        classes_end = term_df[term_df['event'].str.contains('Classes End', case=False, na=False)]

        if not classes_begin.empty:
            start_dt = pd.to_datetime(classes_begin['date'].iloc[0]).date()
        else:
            start_dt = pd.to_datetime(term_df['date']).min().date()

        if not classes_end.empty:
            end_dt = pd.to_datetime(classes_end['date'].iloc[0]).date()
        else:
            end_dt = pd.to_datetime(term_df['date']).max().date()

        term_bounds.append({
            'term': term_name,
            'start': start_dt,
            'end': end_dt
        })

    active_terms = [t for t in term_bounds if t['start'] <= today <= t['end']]
    if active_terms:
        # If multiple active terms, pick the one that started most recently
        active_terms.sort(key=lambda x: x['start'], reverse=True)
        default_term = active_terms[0]['term']
    else:
        # Inbetween terms: pick the next upcoming term
        upcoming_terms = [t for t in term_bounds if t['start'] > today]
        if upcoming_terms:
            upcoming_terms.sort(key=lambda x: x['start'])
            default_term = upcoming_terms[0]['term']
        else:
            term_bounds.sort(key=lambda x: x['start'])
            default_term = term_bounds[-1]['term'] if term_bounds else "All Terms"

    # Sidebar
#    st.sidebar.image("https://www.ufl.edu/media/ufl_edu/images/logo.png", width=180)
    st.sidebar.markdown("### 🔍 Filters")

    search_query = st.sidebar.text_input("Search Events", "")

    terms = ["All Terms"] + sorted(list(df_calendar['term'].unique()))
    try:
        default_index = terms.index(default_term)
    except ValueError:
        default_index = 0

    selected_term = st.sidebar.selectbox("Select Academic Term", terms, index=default_index)

    categories = ["All Categories"] + sorted(list(df_calendar['category'].unique()))
    selected_category = st.sidebar.selectbox("Select Event Category", categories)

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    **UF Academic Dates Hub** automatically parses official registrar datasets daily. This keeps academic deadlines, tuition payment dues, registration window bounds, and campus holidays clean and accessible.
    """)

    # Filter Data
    filtered_df = df_calendar.copy()
    if selected_term != "All Terms":
        filtered_df = filtered_df[filtered_df['term'] == selected_term]
    if selected_category != "All Categories":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if search_query:
        filtered_df = filtered_df[filtered_df['event'].str.contains(search_query, case=False, na=False)]

    # 1. Countdown Widgets / Metric Cards
    st.markdown("### ⏱️ Upcoming Academic Milestones")

    # Get next 3 upcoming events (excluding holidays if desired, but let's show all next 3 events)
    upcoming_events = df_calendar[df_calendar['date_dt'] >= today].sort_values('date_dt').head(3)

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    for idx, (_, row) in enumerate(upcoming_events.iterrows()):
        days_left = (row['date_dt'] - today).days
        with cols[idx]:
            st.markdown(f"""
            <div class="metric-card">
                <span style="font-size:0.8rem; text-transform:uppercase; color:#6c757d; font-weight:bold;">{row['term']} • {row['category']}</span>
                <h4 style="margin:5px 0 10px 0; font-size:1.15rem; color:#0021A5; height: 45px; overflow: hidden;">{row['event']}</h4>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.5rem; font-weight:bold; color:#FF4A00;">{days_left} days</span>
                    <span style="font-size:0.9rem; color:#6c757d;">{row['date_dt'].strftime('%b %d, %Y')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Main Tabs
    tab_master, tab_breakdown, tab_api = st.tabs(["📅 Master Calendar Table", "📊 Category Breakdown", "🚀 Streamlit Developer API"])

    with tab_master:
        st.markdown("### Interactive Master Database")
        st.markdown("Explore, search, and export the complete list of academic dates and deadlines.")

        # Display table
        display_cols = ['date', 'end_date', 'event', 'term', 'category', 'raw_date']
        st.dataframe(
            filtered_df[display_cols].rename(columns={
                'date': 'Start Date',
                'end_date': 'End Date',
                'event': 'Academic Event',
                'term': 'Semester',
                'category': 'Category',
                'raw_date': 'Raw Catalog Text'
            }),
            use_container_width=True,
            hide_index=True
        )

        # Download Buttons
        dl_col1, dl_col2, _ = st.columns([1, 1, 8])
        with dl_col1:
            csv_data = filtered_df[display_cols].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download filtered CSV",
                data=csv_data,
                file_name="uf_filtered_dates.csv",
                mime="text/csv"
            )
        with dl_col2:
            json_data = json.dumps(filtered_df[display_cols].to_dict(orient='records'), cls=DateTimeEncoder, indent=2).encode('utf-8')
            st.download_button(
                label="📥 Download filtered JSON",
                data=json_data,
                file_name="uf_filtered_dates.json",
                mime="application/json"
            )

    with tab_breakdown:
        st.markdown("### 📊 Distribution of Events")

        # Count of events by category
        cat_counts = filtered_df['category'].value_counts().reset_index()
        cat_counts.columns = ['Category', 'Number of Events']

        # Use streamlit bar chart
        st.bar_chart(cat_counts.set_index('Category'))

        # Show key stats
        st.markdown("### 📈 Key Highlights")
        h_col1, h_col2, h_col3 = st.columns(3)
        h_col1.metric("Total Events (Filtered)", len(filtered_df))
        h_col2.metric("Terms Covered", len(filtered_df['term'].unique()))
        h_col3.metric("Categories Covered", len(filtered_df['category'].unique()))

    with tab_api:
        st.markdown("### 🚀 Integration Code Generator")
        st.markdown("""
        Integrate these dynamically updated feeds directly inside your Streamlit or Python applications!
        These datasets always pull the absolute latest schedules parsed directly from the UF catalog.
        """)

        feed_type = st.selectbox(
            "Select Feed Data Source",
            ["calendar.json", "deadlines.json", "holidays.json", "registration.json", "commencement.json", "important_dates.json"]
        )

        raw_url = f"https://raw.githubusercontent.com/tyoungg/UF_CALENDAR/main/data/{feed_type}"

        st.markdown("#### **Python Code Snippet**")
        st.code(f"""
import pandas as pd
import streamlit as st

# Load the dynamic UF {feed_type.split('.')[0]} feed
@st.cache_data
def get_uf_dates():
    url = "{raw_url}"
    return pd.read_json(url)

df = get_uf_dates()

# Display in Streamlit
st.dataframe(df, use_container_width=True)
        """, language="python")

        st.markdown("#### **Direct API URL**")
        st.info(raw_url)
