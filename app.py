import streamlit as st
import pandas as pd
from datetime import datetime, time
from models import Session, Flight

st.set_page_config(page_title="FlightOps Helper", layout="wide")
st.title("FlightOps Helper - Delta Air Lines Operations")
st.markdown("---")

# Sidebar with Delta branding
st.sidebar.title(" Controls")
st.sidebar.markdown("Built for Delta Air Lines")

# Initialize session state
if 'flights' not in st.session_state:
    st.session_state.flights = []

# === ADD FLIGHT FORM ===
col1, col2 = st.columns(2)
with col1:
    st.header("Add New Flight")
    with st.form("add_flight", clear_on_submit=True):
        flight_num = st.text_input("Flight #", "DL123", help="e.g., DL123, AA456")
        destination = st.text_input("Destination", "ATL")
        
        col_time1, col_time2 = st.columns(2)
        with col_time1:
            dep_date = st.date_input("Date", datetime.now())
        with col_time2:
            dep_time = st.time_input("Time", time(14, 30))
        
        status = st.selectbox("Status", ["Scheduled", "Delayed", "Boarding", "Departed"])
        gate = st.text_input("Gate", "A12", help="e.g., A12, B5")
        
        submitted = st.form_submit_button("➕ Add Flight", use_container_width=True)
        if submitted:
            try:
                session = Session()
                new_flight = Flight(
                    flight_num=flight_num,
                    destination=destination,
                    departure_time=datetime.combine(dep_date, dep_time),
                    status=status,
                    gate=gate
                )
                session.add(new_flight)
                session.commit()
                st.session_state.flights.append(new_flight.to_dict())
                st.success(f"**{flight_num}** added to Gate {gate}!")
                session.close()
            except Exception as e:
                st.error(f" Error: {e}")

# === DISPLAY FLIGHTS + GATE CONFLICTS ===
with col2:
    st.header("Flight Board")
    
    # Load flights from DB
    session = Session()
    db_flights = session.query(Flight).all()
    st.session_state.flights = [f.to_dict() for f in db_flights]
    session.close()
    
    if st.session_state.flights:
        df = pd.DataFrame(st.session_state.flights)
        st.dataframe(df, use_container_width=True)
        
        # GATE CONFLICT DETECTION 
        st.subheader(" **Gate Conflict Check**")
        conflicts = []
        for i, f1 in enumerate(st.session_state.flights):
            for j, f2 in enumerate(st.session_state.flights):
                if i != j and f1['gate'] == f2['gate']:
                    time_diff = abs((datetime.fromisoformat(f1['departure_time']) - 
                                   datetime.fromisoformat(f2['departure_time'])).total_seconds())
                    if time_diff < 1800:  # 30 minutes
                        conflicts.append(f" **Gate {f1['gate']}**: {f1['flight_num']} & {f2['flight_num']}")
        
        if conflicts:
            for conflict in conflicts:
                st.error(conflict)
        else:
            st.success(" **No gate conflicts** - All clear!")
    else:
        st.info(" Add your first flight above!")

# === UPDATE STATUS ===
st.header(" Update Flight Status")
if st.session_state.flights:
    col_update1, col_update2 = st.columns(2)
    with col_update1:
        selected_flight = st.selectbox("Select Flight", 
                                     [f['flight_num'] for f in st.session_state.flights])
    with col_update2:
        new_status = st.selectbox("New Status", ["Scheduled", "Delayed", "Boarding", "Departed"])
        if st.button(" Update", use_container_width=True):
            session = Session()
            flight = session.query(Flight).filter_by(flight_num=selected_flight).first()
            flight.status = new_status
            session.commit()
            st.success(f" **{selected_flight}** updated to **{new_status}**!")
            session.close()
            st.rerun()
else:
    st.info("Add flights first!")

st.markdown("---")
st.caption(" Built for Delta Air Lines operations by [Your Name]")
