import os
import re
import datetime
import json
import logging
import requests
from bs4 import BeautifulSoup, Tag
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

MONTH_MAP = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sept': 9, 'sep': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12
}

MONTH_RE = re.compile(
    r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)\b',
    re.IGNORECASE
)

def resolve_year(month_name, term_name):
    """
    Dynamically resolve the calendar year for a given month in a term.
    For example:
    - "January" under "Fall 2026" belongs to 2027.
    - "October" under "Spring 2027" belongs to 2026.
    """
    match = re.search(r'\d{4}', term_name)
    if not match:
        return datetime.date.today().year
    term_year = int(match.group())

    month_num = MONTH_MAP[month_name.lower()]
    term_lower = term_name.lower()

    if 'fall' in term_lower:
        if month_num in [1, 2]:
            return term_year + 1
        return term_year
    elif 'spring' in term_lower:
        if month_num in [10, 11, 12]:
            return term_year - 1
        return term_year
    return term_year

def clean_day_str(s):
    """Clean parentheses and extra annotations from a day/date string."""
    s = re.sub(r'\(.*?\)', '', s)
    s = s.replace(':', '').replace('*', '').strip()
    return s

def parse_date_string(date_str, term_name):
    """
    Parse date_str (e.g., "August 20, 21, 24 - 26" or "December 25 - January 1")
    and return a list of ISO formatted strings ['YYYY-MM-DD', ...].
    """
    date_str = date_str.strip()
    if not date_str or date_str.lower() in ['none', 'in class', 'tbd']:
        return []

    parts = [p.strip() for p in date_str.split(',') if p.strip()]
    parsed_dates = []
    current_month = None

    for part in parts:
        part_clean = clean_day_str(part)
        if not part_clean:
            continue

        month_matches = list(MONTH_RE.finditer(part_clean))

        if len(month_matches) == 2:
            # Range across months, e.g. "March 23 - May 7" or "May 11 - May 12"
            hyphen_match = re.search(r'[-–—]', part_clean)
            if hyphen_match:
                start_part = part_clean[:hyphen_match.start()].strip()
                end_part = part_clean[hyphen_match.end():].strip()

                # Parse start
                start_month_match = MONTH_RE.search(start_part)
                start_dt = None
                if start_month_match:
                    start_month = start_month_match.group()
                    start_day_match = re.search(r'\d+', start_part)
                    if start_day_match:
                        start_day = int(start_day_match.group())
                        start_year = resolve_year(start_month, term_name)
                        start_dt = datetime.date(start_year, MONTH_MAP[start_month.lower()], start_day)

                # Parse end
                end_month_match = MONTH_RE.search(end_part)
                end_dt = None
                if end_month_match:
                    end_month = end_month_match.group()
                    end_day_match = re.search(r'\d+', end_part)
                    if end_day_match:
                        end_day = int(end_day_match.group())
                        end_year = resolve_year(end_month, term_name)
                        end_dt = datetime.date(end_year, MONTH_MAP[end_month.lower()], end_day)

                if start_dt and end_dt:
                    curr_dt = start_dt
                    while curr_dt <= end_dt:
                        parsed_dates.append(curr_dt.isoformat())
                        curr_dt += datetime.timedelta(days=1)

                current_month = end_month

        elif len(month_matches) == 1:
            current_month = month_matches[0].group()
            days_part = part_clean.replace(current_month, '').strip()

            hyphen_match = re.search(r'[-–—]', days_part)
            if hyphen_match:
                start_day_match = re.search(r'\d+', days_part[:hyphen_match.start()])
                end_day_match = re.search(r'\d+', days_part[hyphen_match.end():])
                if start_day_match and end_day_match:
                    start_day = int(start_day_match.group())
                    end_day = int(end_day_match.group())
                    year = resolve_year(current_month, term_name)
                    m_num = MONTH_MAP[current_month.lower()]

                    start_dt = datetime.date(year, m_num, start_day)
                    end_dt = datetime.date(year, m_num, end_day)
                    curr_dt = start_dt
                    while curr_dt <= end_dt:
                        parsed_dates.append(curr_dt.isoformat())
                        curr_dt += datetime.timedelta(days=1)
            else:
                day_match = re.search(r'\d+', days_part)
                if day_match:
                    day = int(day_match.group())
                    year = resolve_year(current_month, term_name)
                    m_num = MONTH_MAP[current_month.lower()]
                    parsed_dates.append(datetime.date(year, m_num, day).isoformat())

        else:
            # No month match in this part. Inherit current_month if available.
            if current_month:
                hyphen_match = re.search(r'[-–—]', part_clean)
                if hyphen_match:
                    start_day_match = re.search(r'\d+', part_clean[:hyphen_match.start()])
                    end_day_match = re.search(r'\d+', part_clean[hyphen_match.end():])
                    if start_day_match and end_day_match:
                        start_day = int(start_day_match.group())
                        end_day = int(end_day_match.group())
                        year = resolve_year(current_month, term_name)
                        m_num = MONTH_MAP[current_month.lower()]

                        start_dt = datetime.date(year, m_num, start_day)
                        end_dt = datetime.date(year, m_num, end_day)
                        curr_dt = start_dt
                        while curr_dt <= end_dt:
                            parsed_dates.append(curr_dt.isoformat())
                            curr_dt += datetime.timedelta(days=1)
                else:
                    day_match = re.search(r'\d+', part_clean)
                    if day_match:
                        day = int(day_match.group())
                        year = resolve_year(current_month, term_name)
                        m_num = MONTH_MAP[current_month.lower()]
                        parsed_dates.append(datetime.date(year, m_num, day).isoformat())

    return parsed_dates

def clean_event_name(event_name):
    """Remove trailing footnote digits and clean up name."""
    event_name = re.sub(r'([A-Za-z\.\)]+)(\d+)\b', r'\1', event_name)
    event_name = event_name.replace('^1', '').replace('^2', '').replace('^3', '').replace('^4', '')
    return event_name.strip()

def determine_category(event_name):
    """Categorize events based on their descriptions."""
    name_lower = event_name.lower()
    if any(k in name_lower for k in ['holiday', 'break', 'closed', 'thanksgiving', 'memorial day', 'juneteenth', 'labor day', 'homecoming', 'veterans day', 'independence day']):
        return 'Holiday'
    if any(k in name_lower for k in ['registration', 'drop', 'add', 'eep', 'non-degree', 's/u grade option']):
        return 'Registration'
    if any(k in name_lower for k in ['fee', 'payment', 'bursar', 'refund', 'liability']):
        return 'Financial'
    if any(k in name_lower for k in ['commencement', 'graduation']):
        return 'Commencement'
    return 'Academic'

def is_important_event(event_name, category):
    """Determine if the event is a key academic deadline."""
    if category in ['Holiday', 'Commencement']:
        return True
    name_lower = event_name.lower()
    if any(k in name_lower for k in ['classes begin', 'classes end', 'drop deadline', 'fee payments', 'regular registration', 'reading days', 'final exams', 'grades available']):
        return True
    return False

def get_academic_year_url():
    """Scrape the main dates & deadlines catalog page and find the current/next years' pages."""
    base_url = "https://catalog.ufl.edu/UGRD/dates-deadlines/"
    logging.info(f"Fetching main dates-deadlines page: {base_url}")

    try:
        response = requests.get(base_url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to fetch main dates-deadlines page: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # Calculate target academic years
    today = datetime.date.today()
    current_start = today.year - 1 if today.month < 5 else today.year
    target_years = [f"{current_start}-{current_start+1}", f"{current_start+1}-{current_start+2}"]
    logging.info(f"Target academic years determined: {target_years}")

    urls = []
    # Find links matching the target academic years
    for link in soup.find_all('a', href=True):
        href = link['href']
        for yr in target_years:
            if yr in href and href.endswith('/'):
                full_url = requests.compat.urljoin(base_url, href)
                if full_url not in urls:
                    urls.append(full_url)

    # If no matching URLs found, default to current year
    if not urls:
        default_url = f"{base_url}{current_start}-{current_start+1}/"
        logging.warning(f"No explicit links found in HTML. Defaulting to: {default_url}")
        urls.append(default_url)

    return urls

def scrape_academic_year_page(url):
    """Scrape and parse academic deadlines and events from a specific year's catalog page."""
    logging.info(f"Scraping academic year page: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to scrape academic year page {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    events_list = []
    h2_elements = soup.find_all('h2')
    logging.info(f"Found {len(h2_elements)} h2 header elements on the page.")

    for h2 in h2_elements:
        term_text = h2.text.strip()
        # Check if this h2 looks like an academic term, e.g., "Fall 2026", "Summer A/C 2026", etc.
        if not any(k in term_text.lower() for k in ['fall', 'spring', 'summer']):
            continue

        logging.info(f"Processing term section: {term_text}")

        # Find next sibling table before the next h2
        next_h2 = h2.find_next('h2')
        curr = h2.next_sibling
        table = None
        while curr and curr != next_h2:
            if isinstance(curr, Tag):
                if curr.name == 'table':
                    table = curr
                    break
                t = curr.find('table')
                if t:
                    table = t
                    break
            curr = curr.next_sibling

        if not table:
            logging.warning(f"No table found for term section: {term_text}")
            continue

        # Determine table column headers
        headers = []
        first_tr = table.find('tr')
        if first_tr:
            headers = [th.text.strip() for th in first_tr.find_all(['th', 'td'])]

        # State tracker for sub-categories
        active_event = ""
        active_category = "Academic"

        rows = table.find_all('tr')
        for r_idx, row in enumerate(rows):
            # Skip header row
            if row.find('th') and r_idx == 0:
                continue
            cols = row.find_all('td')
            if not cols:
                continue

            col_texts = [td.text.strip() for td in cols]

            # If the number of columns doesn't match headers, skip
            if len(col_texts) < len(headers):
                continue

            if len(headers) == 3:
                # 3-column table (usually Summer A/C)
                # columns: Event, Summer A Date, Summer C Date
                event_cell = col_texts[0]
                date_cell_a = col_texts[1]
                date_cell_c = col_texts[2]

                if event_cell:
                    active_event = clean_event_name(event_cell)
                    active_category = determine_category(active_event)

                # Process Summer A
                if date_cell_a:
                    sub_cat_a = active_category
                    if not event_cell and (active_category == 'Holiday' or ':' in date_cell_a):
                        sub_cat_a = 'Holiday'

                    if ':' in date_cell_a and not ('(' in date_cell_a and ')' in date_cell_a and date_cell_a.index('(') < date_cell_a.index(':') < date_cell_a.index(')')):
                        parts = date_cell_a.split(':', 1)
                        if MONTH_RE.search(parts[0]):
                            resolved_event = clean_event_name(parts[1])
                            resolved_date_txt = parts[0].strip()
                        else:
                            resolved_event = active_event
                            resolved_date_txt = date_cell_a
                    else:
                        resolved_event = active_event
                        resolved_date_txt = date_cell_a

                    # Reconstruct term name for Summer A
                    term_a = term_text.replace('Summer A/C', 'Summer A').strip()
                    parsed_dts = parse_date_string(resolved_date_txt, term_a)
                    if parsed_dts:
                        events_list.append({
                            'term': term_a,
                            'event': resolved_event,
                            'category': sub_cat_a,
                            'raw_date': date_cell_a,
                            'date': parsed_dts[0],
                            'end_date': parsed_dts[-1]
                        })

                # Process Summer C
                if date_cell_c:
                    sub_cat_c = active_category
                    if not event_cell and (active_category == 'Holiday' or ':' in date_cell_c):
                        sub_cat_c = 'Holiday'

                    if ':' in date_cell_c and not ('(' in date_cell_c and ')' in date_cell_c and date_cell_c.index('(') < date_cell_c.index(':') < date_cell_c.index(')')):
                        parts = date_cell_c.split(':', 1)
                        if MONTH_RE.search(parts[0]):
                            resolved_event = clean_event_name(parts[1])
                            resolved_date_txt = parts[0].strip()
                        else:
                            resolved_event = active_event
                            resolved_date_txt = date_cell_c
                    else:
                        resolved_event = active_event
                        resolved_date_txt = date_cell_c

                    # Reconstruct term name for Summer C
                    term_c = term_text.replace('Summer A/C', 'Summer C').strip()
                    parsed_dts = parse_date_string(resolved_date_txt, term_c)
                    if parsed_dts:
                        events_list.append({
                            'term': term_c,
                            'event': resolved_event,
                            'category': sub_cat_c,
                            'raw_date': date_cell_c,
                            'date': parsed_dts[0],
                            'end_date': parsed_dts[-1]
                        })

            else:
                # 2-column table (e.g. Summer B, Fall, Spring)
                # columns: Event, Date
                event_cell = col_texts[0]
                date_cell = col_texts[1]

                if event_cell:
                    active_event = clean_event_name(event_cell)
                    active_category = determine_category(active_event)

                if date_cell:
                    sub_cat = active_category
                    if not event_cell and (active_category == 'Holiday' or ':' in date_cell):
                        sub_cat = 'Holiday'

                    if ':' in date_cell and not ('(' in date_cell and ')' in date_cell and date_cell.index('(') < date_cell.index(':') < date_cell.index(')')):
                        parts = date_cell.split(':', 1)
                        if MONTH_RE.search(parts[0]):
                            resolved_event = clean_event_name(parts[1])
                            resolved_date_txt = parts[0].strip()
                        else:
                            resolved_event = active_event
                            resolved_date_txt = date_cell
                    else:
                        resolved_event = active_event
                        resolved_date_txt = date_cell

                    parsed_dts = parse_date_string(resolved_date_txt, term_text)
                    if parsed_dts:
                        events_list.append({
                            'term': term_text,
                            'event': resolved_event,
                            'category': sub_cat,
                            'raw_date': date_cell,
                            'date': parsed_dts[0],
                            'end_date': parsed_dts[-1]
                        })

    return events_list

def main():
    os.makedirs('data', exist_ok=True)
    logging.info("Starting UF Academic Dates parser...")

    # Fetch and parse pages
    urls = get_academic_year_url()
    all_events = []

    for url in urls:
        year_events = scrape_academic_year_page(url)
        all_events.extend(year_events)

    if not all_events:
        logging.error("No events were scraped. Exiting script.")
        return

    # Deduplicate events (some events may be duplicated if scraping multiple sources)
    unique_events = []
    seen = set()
    for ev in all_events:
        # Create a unique key
        key = (ev['term'], ev['event'], ev['date'], ev['end_date'])
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)

    # Sort master list chronologically by date, then term, then event
    unique_events.sort(key=lambda x: (x['date'], x['term'], x['event']))

    logging.info(f"Total parsed unique events: {len(unique_events)}")

    # Write master calendar files
    master_df = pd.DataFrame(unique_events)
    master_df.to_json('data/calendar.json', orient='records', indent=2)
    master_df.to_csv('data/calendar.csv', index=False)
    logging.info("Saved calendar.json and calendar.csv")

    # Also save as uf_dates.json/csv for backwards/direct compatibility
    master_df.to_json('data/uf_dates.json', orient='records', indent=2)
    master_df.to_csv('data/uf_dates.csv', index=False)
    logging.info("Saved uf_dates.json and uf_dates.csv")

    # Filter & save Deadlines
    deadlines_df = master_df[master_df['category'] != 'Holiday']
    deadlines_df.to_json('data/deadlines.json', orient='records', indent=2)
    deadlines_df.to_csv('data/deadlines.csv', index=False)
    logging.info(f"Saved deadlines.json and deadlines.csv ({len(deadlines_df)} events)")

    # Filter & save Holidays
    holidays_df = master_df[master_df['category'] == 'Holiday']
    holidays_df.to_json('data/holidays.json', orient='records', indent=2)
    holidays_df.to_csv('data/holidays.csv', index=False)
    logging.info(f"Saved holidays.json and holidays.csv ({len(holidays_df)} events)")

    # Filter & save Registration
    registration_df = master_df[master_df['category'] == 'Registration']
    registration_df.to_json('data/registration.json', orient='records', indent=2)
    registration_df.to_csv('data/registration.csv', index=False)
    logging.info(f"Saved registration.json and registration.csv ({len(registration_df)} events)")

    # Filter & save Commencement
    commencement_df = master_df[master_df['category'] == 'Commencement']
    commencement_df.to_json('data/commencement.json', orient='records', indent=2)
    commencement_df.to_csv('data/commencement.csv', index=False)
    logging.info(f"Saved commencement.json and commencement.csv ({len(commencement_df)} events)")

    # Filter & save Important Dates
    important_events = [ev for ev in unique_events if is_important_event(ev['event'], ev['category'])]
    important_df = pd.DataFrame(important_events)
    important_df.to_json('data/important_dates.json', orient='records', indent=2)
    important_df.to_csv('data/important_dates.csv', index=False)
    logging.info(f"Saved important_dates.json and important_dates.csv ({len(important_df)} events)")

    # Save last update timestamp
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    with open('data/last_update.txt', 'w') as f:
        f.write(timestamp)
    logging.info(f"Saved last update timestamp: {timestamp}")

if __name__ == '__main__':
    main()
