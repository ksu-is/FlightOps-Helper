import streamlit as st
import pandas as pd
from datetime import datetime, time
from models import Session, Flight
from sqlalchemy.exc import IntegrityError

# ─── Page Configuration ───────────────────────────────────────────────────────
# set_page_config must be the very first Streamlit call in the script.
# layout="wide" uses the full browser width instead of a narrow centered column.
st.set_page_config(page_title="FlightOps Helper", layout="wide")
st.title("FlightOps Helper - Delta Air Lines Operations")
st.markdown("---")  # horizontal rule for visual separation

# Sidebar appears on the left side of every page
st.sidebar.title("Controls")
st.sidebar.markdown("Built for Delta Air Lines")

# ─── Session State ────────────────────────────────────────────────────────────
# Streamlit reruns the entire script from top to bottom on every user interaction.
# st.session_state is a dictionary that persists across those reruns so we don't
# lose data. We initialize 'flights' as an empty list on the very first load.
if 'flights' not in st.session_state:
    st.session_state.flights = []


# ─── Layout: Two Side-by-Side Columns ─────────────────────────────────────────
# col1 = Add Flight form (left), col2 = Flight Board display (right)
col1, col2 = st.columns(2)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — ADD FLIGHT FORM
# ═══════════════════════════════════════════════════════════════════════════════
with col1:
    st.header("Add New Flight")

    # st.form groups all inputs together so Streamlit only reruns the script
    # when the submit button is clicked — not on every individual keystroke.
    # clear_on_submit=True resets all fields after a successful submission.
    with st.form("add_flight", clear_on_submit=True):
        flight_num  = st.text_input("Flight #", "DL123", help="e.g., DL123, AA456")
        destination = st.text_input("Destination", "ATL")

        # Split the time inputs into two mini-columns so date and time sit side by side
        col_time1, col_time2 = st.columns(2)
        with col_time1:
            dep_date = st.date_input("Date", datetime.now())
        with col_time2:
            dep_time = st.time_input("Time", time(14, 30))  # default 2:30 PM

        status = st.selectbox("Status", ["Scheduled", "Delayed", "Boarding", "Departed"])
        gate   = st.text_input("Gate", "A12", help="e.g., A12, B5")

        submitted = st.form_submit_button("Add Flight", use_container_width=True)

        if submitted:
            # Open a new database session for this transaction
            session = Session()
            try:
                # Combine the separate date and time widgets into one datetime object
                # that SQLAlchemy can store in the DateTime column
                new_flight = Flight(
                    flight_num=flight_num,
                    destination=destination,
                    departure_time=datetime.combine(dep_date, dep_time),
                    status=status,
                    gate=gate,
                )
                session.add(new_flight)    # stage the new record
                session.commit()           # write it to the SQLite database
                st.success(f"**{flight_num}** added to Gate {gate}!")

            except IntegrityError:
                # flight_num has a UNIQUE constraint in the database.
                # IntegrityError is raised if you try to insert a duplicate.
                # We roll back to undo the failed transaction before closing.
                session.rollback()
                st.error(f"Flight number **{flight_num}** already exists. Use a unique flight number.")

            except Exception as e:
                # Catch any other unexpected database errors
                session.rollback()
                st.error(f"Error: {e}")

            finally:
                # Always close the session — even if an exception was raised.
                # Without this, connections can leak and lock the database file.
                session.close()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — FLIGHT BOARD + GATE CONFLICT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════
with col2:
    st.header("Flight Board")

    # Fetch a fresh copy of all flights from the database on every rerun.
    # This ensures the board always reflects the latest data, including any
    # updates made by the status-update section below.
    session = Session()
    try:
        db_flights = session.query(Flight).all()
        # Convert each SQLAlchemy object to a plain dictionary so Pandas can
        # build a DataFrame from it. to_dict() also serializes departure_time
        # to an ISO string so the rest of the app handles it consistently.
        st.session_state.flights = [f.to_dict() for f in db_flights]
    finally:
        session.close()

    if st.session_state.flights:
        # Build a Pandas DataFrame from the list of flight dictionaries
        # and render it as an interactive table in the UI
        df = pd.DataFrame(st.session_state.flights)
        st.dataframe(df, use_container_width=True)

        # ── Gate Conflict Detection ────────────────────────────────────────
        st.subheader("Gate Conflict Check")
        conflicts = []
        flights = st.session_state.flights

        # Compare every unique pair of flights (i < j ensures we never check
        # the same pair twice, which would produce duplicate alerts)
        for i in range(len(flights)):
            for j in range(i + 1, len(flights)):
                f1, f2 = flights[i], flights[j]

                # Only care about flights assigned to the same gate
                if f1['gate'] == f2['gate']:
                    # Calculate how many seconds apart their departures are.
                    # We handle both str and datetime here because rows saved
                    # before the to_dict() fix may return a raw datetime object
                    # instead of an ISO string.
                    def to_dt(val):
                        return val if isinstance(val, datetime) else datetime.fromisoformat(val)

                    time_diff = abs(
                        (to_dt(f1['departure_time']) -
                         to_dt(f2['departure_time'])).total_seconds()
                    )

                    # Flag as a conflict if they're within 30 minutes (1800 seconds)
                    if time_diff < 1800:
                        conflicts.append(
                            f"Gate {f1['gate']}: {f1['flight_num']} & {f2['flight_num']}"
                        )

        # Display each conflict as a red error banner, or a green success if clear
        if conflicts:
            for conflict in conflicts:
                st.error(conflict)
        else:
            st.success("No gate conflicts — all clear!")

    else:
        st.info("Add your first flight above!")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — UPDATE FLIGHT STATUS
# ═══════════════════════════════════════════════════════════════════════════════
st.header("Update Flight Status")

if st.session_state.flights:
    col_update1, col_update2 = st.columns(2)

    with col_update1:
        # Build the dropdown from the flight numbers currently in session state
        selected_flight = st.selectbox(
            "Select Flight",
            [f['flight_num'] for f in st.session_state.flights]
        )
    with col_update2:
        new_status = st.selectbox(
            "New Status",
            ["Scheduled", "Delayed", "Boarding", "Departed"]
        )

    if st.button("Update", use_container_width=True):
        session = Session()
        try:
            # Look up the flight record by flight number.
            # .first() returns the record or None if it doesn't exist.
            flight = session.query(Flight).filter_by(flight_num=selected_flight).first()

            if flight is None:
                # Guard against the edge case where the flight was deleted
                # between page load and the button click
                st.warning(f"Flight {selected_flight} not found.")
            else:
                flight.status = new_status  # mutate the record in-place
                session.commit()            # persist the change to the database
                st.success(f"**{selected_flight}** updated to **{new_status}**!")

        except Exception as e:
            session.rollback()
            st.error(f"Error: {e}")

        finally:
            session.close()

        # Force a full rerun so the Flight Board above reflects the new status
        st.rerun()

else:
    st.info("Add flights first!")


# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Built for Delta Air Lines operations by Kelvin Ameyaw")
