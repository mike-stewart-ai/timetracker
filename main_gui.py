# Leap Time Tracker - main_gui.py (Entry Point)

import streamlit as st
import requests
import datetime
import re
import pandas as pd
from itertools import groupby
import altair as alt

st.set_page_config(layout="wide")

def get_working_days_in_range(start, end):
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += datetime.timedelta(days=1)
    return days

def calculate_expected_hours(working_days, standard_daily_hours):
    total = 0
    for day in working_days:
        total += standard_daily_hours.get(day.strftime("%A"), 0)
    return total

left, main, right = st.columns([1, 4, 1])
with main:
    # Help Guide at the very top (now inside main)
    with st.expander("❓ Help Guide", expanded=False):
        st.markdown("""
        ### Welcome to Leap Time Tracker!

        This guide will walk you through using the app from start to finish:

        **1. What is Leap Time Tracker?**
        - This web app helps you track your working hours, compare them to your expected hours, and see if you owe time or have extra hours. It integrates with your Harvest account and lets you add holidays (including bulk import from Xero).

        **2. Logging In**
        - Log in to your [Harvest account](https://id.getharvest.com/).
        - Go to **Settings > Developers > API V2 Tokens**.
        - Copy your **Personal Access Token** (API Token) and **Account ID**.
        - Enter these into the app's fields. The app will fetch your user info and available time entry dates.

        **3. Set Up Your Working Hours**
        - Enter your standard daily hours for each weekday (defaults to 7.5 for Mon–Fri).
        - Click **Save Standard Hours** if you make changes.

        **4. Add Holidays**
        - To add a single holiday or a range, use the **Add Holiday** section.
        - To import multiple holidays from Xero, paste your Xero holiday export (e.g., `Holiday\tChristmas\t25 Dec - 31 Dec 2025\tApproved`) into the **Bulk Add Holidays from Xero** box and click the button.

        **5. Select Your Date Range**
        - The app will automatically set the start and end dates to match your earliest and latest Harvest time entries.
        - You can adjust these dates if you want to focus on a specific period.

        **6. View Your Results**
        - Click **Calculate Balance** to see your hours owed or extra hours.
        - Use the **Show Hours Graph** button to compare contractual vs. worked hours over time.
        - Use the **Show Cumulative Balance Graph** to see how your hours owed/extra build up over time.

        **7. Troubleshooting**
        - If you see authentication errors, double-check your API token and account ID.
        - Your data is not saved between sessions for privacy.
        - If you have issues with date pickers, check your browser and system date settings.
        - For further help, contact your admin.

        Enjoy tracking your time!
        """)
    st.title("Leap Time Tracker")

    # API credentials (not saved)
    st.subheader("Harvest API Settings")
    api_token = st.text_input("Harvest API Token", type="password")
    account_id = st.text_input("Harvest Account ID")

    # Fetch user ID on the fly
    def fetch_user_id(api_token, account_id):
        url = "https://api.harvestapp.com/api/v2/users/me"
        headers = {
            "Harvest-Account-ID": account_id,
            "Authorization": f"Bearer {api_token}",
            "User-Agent": "Harvest API Example"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["id"]

    user_id = None
    if api_token and account_id:
        try:
            user_id = fetch_user_id(api_token, account_id)
            st.success(f"User ID fetched: {user_id}")
        except Exception as e:
            st.error(f"Failed to fetch user ID: {e}")

    def get_earliest_time_entry_date(user_id, api_token, account_id):
        url = "https://api.harvestapp.com/api/v2/time_entries"
        headers = {
            "Harvest-Account-ID": account_id,
            "Authorization": f"Bearer {api_token}",
            "User-Agent": "Harvest API Example"
        }
        params = {
            "user_id": user_id,
            "per_page": 1,
            "page": 1
        }
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        total_pages = data.get("total_pages", 1)
        if total_pages > 1:
            params["page"] = total_pages
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
        if data["time_entries"]:
            return datetime.datetime.strptime(data["time_entries"][0]["spent_date"], "%Y-%m-%d").date()
        else:
            return def_start

    def get_latest_time_entry_date(user_id, api_token, account_id):
        url = "https://api.harvestapp.com/api/v2/time_entries"
        headers = {
            "Harvest-Account-ID": account_id,
            "Authorization": f"Bearer {api_token}",
            "User-Agent": "Harvest API Example"
        }
        params = {
            "user_id": user_id,
            "per_page": 1,
            "page": 1
        }
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data["time_entries"]:
            return datetime.datetime.strptime(data["time_entries"][0]["spent_date"], "%Y-%m-%d").date()
        else:
            return def_end

    # Date range selection
    st.subheader("Select Date Range")

    def_date = datetime.date.today()
    def_start = def_date.replace(day=1)
    def_end = def_date

    # Initialize earliest/latest entry dates in session state before using them
    if "earliest_entry_date" not in st.session_state:
        st.session_state.earliest_entry_date = def_start
    if "latest_entry_date" not in st.session_state:
        st.session_state.latest_entry_date = def_end

    # Fetch and update earliest/latest entry dates BEFORE rendering widgets
    if user_id and api_token and account_id:
        try:
            earliest = get_earliest_time_entry_date(user_id, api_token, account_id)
            if earliest != st.session_state.earliest_entry_date:
                st.session_state.earliest_entry_date = earliest
                st.session_state.start_date = earliest
        except Exception as e:
            st.warning(f"Could not fetch earliest entry date: {e}")
        try:
            latest = get_latest_time_entry_date(user_id, api_token, account_id)
            if latest != st.session_state.latest_entry_date:
                st.session_state.latest_entry_date = latest
                st.session_state.end_date = latest
        except Exception as e:
            st.warning(f"Could not fetch latest entry date: {e}")

    # Now initialize start_date and end_date in session state
    if "start_date" not in st.session_state:
        st.session_state.start_date = st.session_state.earliest_entry_date
    if "end_date" not in st.session_state:
        st.session_state.end_date = st.session_state.latest_entry_date

    col_start, col_end = st.columns(2)
    with col_start:
        start_date = st.date_input("Start Date", key="start_date", format="DD/MM/YYYY")
    with col_end:
        end_date = st.date_input("End Date", key="end_date", format="DD/MM/YYYY")

    # Standard working hours (in-session only)
    st.subheader("Standard Working Hours")
    def def_default_hours():
        return {day: 7.5 for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]} | {"Saturday": 0.0, "Sunday": 0.0}
    if "standard_daily_hours" not in st.session_state:
        st.session_state.standard_daily_hours = def_default_hours()
    daily_hours = st.session_state.standard_daily_hours
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    inputs = {}
    for i, day in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
        with [col1, col2, col3, col4, col5, col6, col7][i]:
            inputs[day] = st.number_input(day, min_value=0.0, max_value=24.0, value=float(daily_hours.get(day, 0)), step=0.25, key=f"hours_{day}")
    if st.button("Save Standard Working Hours"):
        for day in daily_hours:
            daily_hours[day] = float(inputs[day])
        st.session_state.standard_daily_hours = daily_hours
        st.success("Standard working hours saved (session only).")

    # Leave management (in-session only)
    st.subheader("Leave Management")
    if "holidays" not in st.session_state:
        st.session_state.holidays = []

    # Bulk Add Holidays from Xero
    st.markdown("**Bulk Add Holidays from Xero:**")
    xero_bulk = st.text_area("Paste Xero leave requests here", height=120, key="xero_bulk")

    def parse_xero_holidays(text):
        holidays = []
        for line in text.strip().splitlines():
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            desc = parts[1].strip() if parts[1].strip() else "Holiday"
            date_range = parts[2].strip()
            # Match date ranges like "05 Jan - 08 Jan 2026" or "25 Dec - 31 Dec 2025"
            match = re.match(r"(\d{2} \w{3})\s*-\s*(\d{2} \w{3} \d{4})", date_range)
            if match:
                start_str, end_str = match.groups()
                # If start_str doesn't have a year, take it from end_str
                if len(start_str.split()) == 2:
                    start_str += " " + end_str.split()[-1]
                try:
                    start_date = datetime.datetime.strptime(start_str, "%d %b %Y").date()
                    end_date = datetime.datetime.strptime(end_str, "%d %b %Y").date()
                    holidays.append((desc, start_date, end_date))
                except Exception:
                    continue
        return holidays

    if st.button("Bulk Add Holidays from Xero"):
        holidays = parse_xero_holidays(xero_bulk)
        count = 0
        for desc, start_date, end_date in holidays:
            current = start_date
            while current <= end_date:
                st.session_state.holidays.append({"date": current.isoformat(), "reason": desc})
                current += datetime.timedelta(days=1)
                count += 1
        st.success(f"Added {count} holiday days from Xero.")

    # Add Holiday
    st.markdown("**Add Holiday (range):**")
    hcol1, hcol2 = st.columns(2)
    holiday_start = hcol1.date_input("Holiday Start", key="holiday_start", format="DD/MM/YYYY")
    holiday_end = hcol2.date_input("Holiday End", key="holiday_end", format="DD/MM/YYYY")
    holiday_reason = st.text_input("Holiday Description", value="Approved Holiday", key="holiday_reason")
    if st.button("Add Holiday"):
        if holiday_start > holiday_end:
            st.error("Holiday start date must be before end date.")
        else:
            current = holiday_start
            while current <= holiday_end:
                iso_date = current.isoformat()
                st.session_state.holidays.append({"date": iso_date, "reason": holiday_reason})
                current += datetime.timedelta(days=1)
            st.success("Holiday(s) added (session only).")

    def display_leave_records(leave_list, leave_type, key_prefix):
        if not leave_list:
            st.write(f"No {leave_type.lower()}s recorded.")
            return
        if leave_type == "Holiday":
            # Sort by description then date
            sorted_list = sorted(leave_list, key=lambda x: (x.get("reason") or "(No description)", x["date"]))
            for i, (desc, group) in enumerate(groupby(sorted_list, key=lambda x: x.get("reason") or "(No description)")):
                dates = [datetime.datetime.strptime(item["date"], "%Y-%m-%d") for item in group]
                dates.sort()
                # Group consecutive dates
                ranges = []
                for date in dates:
                    if not ranges or (date - ranges[-1][-1]).days > 1:
                        ranges.append([date, date])
                    else:
                        ranges[-1][-1] = date
                for j, (start, end) in enumerate(ranges):
                    start_str = start.strftime("%d/%m/%Y")
                    end_str = end.strftime("%d/%m/%Y")
                    period = f"{start_str} - {end_str}" if start != end else start_str
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"**{leave_type}:** {desc} | {period}")
                    with col2:
                        if st.button("Remove", key=f"{key_prefix}_{i}_{j}"):
                            to_remove = set((start + datetime.timedelta(days=k)).strftime("%Y-%m-%d")
                                            for k in range((end - start).days + 1))
                            leave_list[:] = [item for item in leave_list if not (
                                (item.get('reason') or "(No description)") == desc and item["date"] in to_remove
                            )]
                            st.rerun()

    st.markdown("---")
    st.markdown("### Leave Records")
    display_leave_records(st.session_state.holidays, "Holiday", "holiday")

    # Fetch time entries from Harvest (stateless)
    def fetch_time_entries(start, end, user_id, api_token, account_id):
        url = "https://api.harvestapp.com/api/v2/time_entries"
        headers = {
            "Harvest-Account-ID": account_id,
            "Authorization": f"Bearer {api_token}",
            "User-Agent": "Harvest API Example"
        }
        params = {
            "user_id": user_id,
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d")
        }
        entries = []
        page = 1
        while True:
            params["page"] = page
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            entries.extend(data["time_entries"])
            if not data.get("next_page"):
                break
            page += 1
        return entries

    def calculate_balance(start, end, user_id, api_token, account_id, daily_hours, holidays):
        time_entries = fetch_time_entries(start, end, user_id, api_token, account_id)
        logged_hours = sum(e["hours"] for e in time_entries)
        working_days = get_working_days_in_range(start, end)
        expected_hours = calculate_expected_hours(working_days, daily_hours)
        holiday_days = [datetime.datetime.strptime(h["date"], "%Y-%m-%d") for h in holidays if start <= datetime.datetime.strptime(h["date"], "%Y-%m-%d") <= end]
        reduced_hours = sum(daily_hours.get(day.strftime("%A"), 0) for day in holiday_days)
        balance = round(logged_hours - expected_hours + reduced_hours, 2)
        with st.expander("Calculation Details"):
            st.write(f"**Logged hours:** {logged_hours}")
            st.write(f"**Expected hours:** {expected_hours}")
            st.write(f"**Reduced hours (holidays):** {reduced_hours}")
            st.write(f"**Balance:** {balance}")
        return balance

    if st.button("Calculate Balance", type="primary"):
        if not (api_token and account_id and user_id):
            st.error("Please enter valid API credentials.")
        else:
            try:
                start = datetime.datetime.combine(start_date, datetime.time.min)
                end = datetime.datetime.combine(end_date, datetime.time.max)
                if start > end:
                    st.error("Start date must be before end date.")
                else:
                    balance = calculate_balance(
                        start, end, user_id, api_token, account_id,
                        st.session_state.standard_daily_hours,
                        st.session_state.holidays
                    )
                    if balance > 0:
                        st.success(f"You are owed {balance} hours.")
                    elif balance < 0:
                        st.warning(f"You owe {abs(balance)} hours.")
                    else:
                        st.info("You are exactly on track. No hours owed or owing.")
            except Exception as e:
                st.error(f"Failed to calculate balance: {e}")

    if st.button("Show Hours Graph"):
        all_dates = pd.date_range(start=start_date, end=end_date)
        weekday_hours = st.session_state.standard_daily_hours
        expected = []
        for d in all_dates:
            if any(h["date"] == d.date().isoformat() for h in st.session_state.holidays):
                expected.append(0)
            else:
                expected.append(weekday_hours.get(d.strftime("%A"), 0))
        time_entries = fetch_time_entries(
            datetime.datetime.combine(start_date, datetime.time.min),
            datetime.datetime.combine(end_date, datetime.time.max),
            user_id, api_token, account_id
        )
        actual_dict = {}
        for entry in time_entries:
            actual_dict.setdefault(entry["spent_date"], 0)
            actual_dict[entry["spent_date"]] += entry["hours"]
        actual = [actual_dict.get(d.date().isoformat(), 0) for d in all_dates]
        # Build DataFrame for legend-enabled overlayed bar chart
        data = []
        for date, exp, act in zip(all_dates, expected, actual):
            if exp == 0:
                continue
            # Contractual bar (always from 0 to exp)
            data.append({"Date": date, "Type": "Contractual Hours", "y0": 0, "y1": exp, "Value": exp})
            # Overtime bar (from exp to act, if act > exp)
            if act > exp:
                data.append({"Date": date, "Type": "Overtime", "y0": exp, "y1": act, "Value": act - exp})
            # Shortfall bar (from act to exp, if act < exp)
            if act < exp:
                data.append({"Date": date, "Type": "Shortfall", "y0": act, "y1": exp, "Value": exp - act})
        df = pd.DataFrame(data)
        color_scale = alt.Scale(domain=["Contractual Hours", "Overtime", "Shortfall"], range=["#2471A3", "#D7263D", "#21A179"])
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("Date:T", title="Date", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("y0:Q", title="Hours"),
            y2=alt.Y2("y1:Q"),
            color=alt.Color("Type:N", scale=color_scale, legend=alt.Legend(title="Type")),
            tooltip=["Date:T", "Type:N", alt.Tooltip("Value:Q", title="Hours")]
        ).properties(title="Contractual, Overtime, and Shortfall Hours").configure_axis(labelFontSize=11)
        st.altair_chart(chart, use_container_width=True)

    if st.button("Show Cumulative Balance Graph"):
        all_dates = pd.date_range(start=start_date, end=end_date)
        weekday_hours = st.session_state.standard_daily_hours
        expected = []
        for d in all_dates:
            if any(h["date"] == d.date().isoformat() for h in st.session_state.holidays):
                expected.append(0)
            else:
                expected.append(weekday_hours.get(d.strftime("%A"), 0))
        time_entries = fetch_time_entries(
            datetime.datetime.combine(start_date, datetime.time.min),
            datetime.datetime.combine(end_date, datetime.time.max),
            user_id, api_token, account_id
        )
        actual_dict = {}
        for entry in time_entries:
            actual_dict.setdefault(entry["spent_date"], 0)
            actual_dict[entry["spent_date"]] += entry["hours"]
        actual = [actual_dict.get(d.date().isoformat(), 0) for d in all_dates]
        # Calculate cumulative sums
        df_cum = pd.DataFrame({
            "Date": all_dates,
            "Contractual Hours": pd.Series(expected).cumsum(),
            "Hours Worked": pd.Series(actual).cumsum()
        })
        df_cum_melt = df_cum.melt("Date", var_name="Type", value_name="Cumulative Hours")
        color_scale = alt.Scale(domain=["Hours Worked", "Contractual Hours"], range=["#29335C", "#E4572E"])
        chart_cum = alt.Chart(df_cum_melt).mark_line(point=True).encode(
            x=alt.X("Date:T", title="Date"),
            y=alt.Y("Cumulative Hours:Q", title="Cumulative Hours"),
            color=alt.Color("Type:N", scale=color_scale, legend=alt.Legend(title="")),
            tooltip=["Date:T", "Type:N", "Cumulative Hours:Q"]
        ).properties(title="Cumulative Contractual vs Hours Worked")
        st.altair_chart(chart_cum, use_container_width=True)
