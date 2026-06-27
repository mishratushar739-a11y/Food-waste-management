"""
Food Management System — Streamlit + SQLite3
Author: Tushar Kumar Mishra
(Converted from MySQL to SQLite3)

A dashboard for a local food-donation network: providers list surplus
food, receivers (NGOs, shelters, individuals) claim it. This app
uses a local SQLite3 database file, runs the 15 analysis queries,
supports filtering the live food listings, and lets you add/update/
delete listings (CRUD) directly from the UI.

----------------------------------------------------------------------
SETUP
----------------------------------------------------------------------
1. Install dependencies:
     pip install streamlit pandas sqlalchemy plotly

2. Run the app:
     streamlit run app_sqlite.py

3. On first run, open the sidebar -> "Database Setup" -> click
   "Create tables & load CSVs". Point it at the four CSVs
   (providers_data.csv, receivers_data.csv, food_listings_data.csv,
   claims_data.csv). This creates the tables and loads your data.
   You only need to do this once (re-running is safe; it replaces
   the tables).

   The SQLite database file is saved as  food_management.db  in the
   current working directory.
----------------------------------------------------------------------
"""

import os
from datetime import date, datetime

import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


# ----------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Food Management System",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ----------------------------------------------------------------------
# Database connection  (SQLite3 — no credentials needed)
# ----------------------------------------------------------------------
DEFAULT_DB_PATH = os.environ.get("SQLITE_DB_PATH", "food_management.db")


@st.cache_resource(show_spinner=False)
def get_engine(db_path: str):
    """Create a SQLAlchemy engine backed by SQLite3.
    Tables are created immediately so the app never crashes on a fresh DB."""
    url = f"sqlite:///{db_path}?check_same_thread=False"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    # Enable FK enforcement and ensure schema exists
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
        for stmt in SCHEMA_SQL:
            conn.execute(text(stmt))
    return engine


def run_query(engine, sql, params=None):
    """Run a SELECT and return a DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def run_statement(engine, sql, params=None):
    """Run an INSERT/UPDATE/DELETE/DDL statement."""
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.execute(text(sql), params or {})


# ----------------------------------------------------------------------
# Schema + CSV loading
# ----------------------------------------------------------------------
SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS providers_data (
        provider_id INTEGER PRIMARY KEY,
        name        TEXT,
        type        TEXT,
        address     TEXT,
        city        TEXT,
        contact     TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS receivers_data (
        receiver_id INTEGER PRIMARY KEY,
        name        TEXT,
        type        TEXT,
        city        TEXT,
        contact     TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS food_listings_data (
        food_id       INTEGER PRIMARY KEY,
        food_name     TEXT,
        quantity      INTEGER,
        expiry_date   TEXT,
        provider_id   INTEGER,
        provider_type TEXT,
        location      TEXT,
        food_type     TEXT,
        meal_type     TEXT,
        FOREIGN KEY (provider_id) REFERENCES providers_data(provider_id)
            ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS claims_data (
        claim_id    INTEGER PRIMARY KEY,
        food_id     INTEGER,
        receiver_id INTEGER,
        status      TEXT,
        timestamp   TEXT,
        FOREIGN KEY (food_id) REFERENCES food_listings_data(food_id)
            ON DELETE CASCADE,
        FOREIGN KEY (receiver_id) REFERENCES receivers_data(receiver_id)
            ON DELETE CASCADE
    )
    """,
]

# Order matters: drop children before parents, load parents before children
DROP_ORDER = ["claims_data", "food_listings_data", "receivers_data", "providers_data"]
LOAD_ORDER = ["providers_data", "receivers_data", "food_listings_data", "claims_data"]


def create_tables(engine):
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
        for stmt in SCHEMA_SQL:
            conn.execute(text(stmt))


def drop_tables(engine):
    """Drop all tables.  SQLite doesn't need FOREIGN_KEY_CHECKS tricks;
    we just drop in child-first order with foreign keys temporarily off."""
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        for tbl in DROP_ORDER:
            conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
        conn.execute(text("PRAGMA foreign_keys = ON"))


def load_csvs_to_sqlite(engine, file_map):
    """
    file_map: dict of table_name -> uploaded file-like object (or path)
    Replaces existing tables and bulk-loads the CSVs.
    """
    drop_tables(engine)
    create_tables(engine)

    dataframes = {}
    for table in LOAD_ORDER:
        f = file_map[table]
        df = pd.read_csv(f)
        dataframes[table] = df

    # Type cleanup — store dates as ISO strings (SQLite TEXT affinity)
    dataframes["food_listings_data"]["expiry_date"] = pd.to_datetime(
        dataframes["food_listings_data"]["expiry_date"]
    ).dt.strftime("%Y-%m-%d")
    dataframes["claims_data"]["timestamp"] = pd.to_datetime(
        dataframes["claims_data"]["timestamp"]
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
        for table in LOAD_ORDER:
            dataframes[table].to_sql(table, conn, if_exists="append", index=False)

    return {t: len(dataframes[t]) for t in LOAD_ORDER}


# ----------------------------------------------------------------------
# The 15 analysis queries
# (MySQL-specific syntax replaced with SQLite equivalents)
# ----------------------------------------------------------------------
QUERIES = {
    "1. Providers per city": """
        SELECT city, COUNT(*) AS providers
        FROM providers_data
        GROUP BY city
        ORDER BY providers DESC
    """,
    "2. Receivers per city": """
        SELECT city, COUNT(*) AS receivers
        FROM receivers_data
        GROUP BY city
        ORDER BY receivers DESC
    """,
    "3. Provider type contributing most food (by quantity)": """
        SELECT provider_type, SUM(quantity) AS total_food
        FROM food_listings_data
        GROUP BY provider_type
        ORDER BY total_food DESC
    """,
    "4. Providers in a specific city": """
        SELECT name, type, address, contact
        FROM providers_data
        WHERE city = :city
    """,
    "5. Receivers who claimed the most food": """
        SELECT r.name, r.type, COUNT(c.claim_id) AS claims
        FROM receivers_data r
        JOIN claims_data c ON r.receiver_id = c.receiver_id
        GROUP BY r.name, r.type
        ORDER BY claims DESC
    """,
    "6. Total quantity of food available": """
        SELECT SUM(quantity) AS total_food
        FROM food_listings_data
    """,
    "7. City with the highest number of food listings": """
        SELECT location, COUNT(*) AS listings
        FROM food_listings_data
        GROUP BY location
        ORDER BY listings DESC
    """,
    "8. Most common food type": """
        SELECT food_type, COUNT(*) AS total
        FROM food_listings_data
        GROUP BY food_type
        ORDER BY total DESC
    """,
    "9. Number of claims per food item": """
        SELECT f.food_name, COUNT(c.claim_id) AS claims
        FROM food_listings_data f
        JOIN claims_data c ON f.food_id = c.food_id
        GROUP BY f.food_name
        ORDER BY claims DESC
    """,
    "10. Provider with the highest successful (Completed) claims": """
        SELECT p.name, COUNT(*) AS successful_claims
        FROM providers_data p
        JOIN food_listings_data f ON p.provider_id = f.provider_id
        JOIN claims_data c ON f.food_id = c.food_id
        WHERE c.status = 'Completed'
        GROUP BY p.name
        ORDER BY successful_claims DESC
    """,
    "11. Percentage breakdown of claim status": """
        SELECT status,
               ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM claims_data), 2) AS percentage
        FROM claims_data
        GROUP BY status
        ORDER BY percentage DESC
    """,
    "12. Average quantity claimed per receiver": """
        SELECT r.name, ROUND(AVG(f.quantity), 1) AS avg_quantity_claimed
        FROM receivers_data r
        JOIN claims_data c ON r.receiver_id = c.receiver_id
        JOIN food_listings_data f ON c.food_id = f.food_id
        GROUP BY r.name
        ORDER BY avg_quantity_claimed DESC
    """,
    "13. Most claimed meal type": """
        SELECT meal_type, COUNT(*) AS claims
        FROM food_listings_data f
        JOIN claims_data c ON f.food_id = c.food_id
        GROUP BY meal_type
        ORDER BY claims DESC
    """,
    "14. Total quantity of food donated by each provider": """
        SELECT p.name, SUM(f.quantity) AS total_donated
        FROM providers_data p
        JOIN food_listings_data f ON p.provider_id = f.provider_id
        GROUP BY p.name
        ORDER BY total_donated DESC
    """,
    "15. Top 5 cities by total food availability": """
        SELECT location, SUM(quantity) AS total_quantity
        FROM food_listings_data
        GROUP BY location
        ORDER BY total_quantity DESC
        LIMIT 5
    """,
}

# Queries that need a parameter (handled specially in the UI)
PARAMETERIZED = {"4. Providers in a specific city"}


# ----------------------------------------------------------------------
# Sidebar: connection + setup
# ----------------------------------------------------------------------
def sidebar_connection():
    st.sidebar.title("🍱 Food Wastage Management")
    st.sidebar.caption("Tushar Kumar Mishra")
    st.sidebar.divider()

    st.sidebar.subheader("Database")
    db_path = st.sidebar.text_input("SQLite file path", value=DEFAULT_DB_PATH)

    # Clear the engine cache when the user changes the db path
    if st.session_state.get("_last_db_path") != db_path:
        get_engine.clear()
        st.session_state["_last_db_path"] = db_path

    engine = None
    connected = False
    try:
        engine = get_engine(db_path)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        connected = True
        st.sidebar.success(f"Connected to SQLite ✅  (`{db_path}`)")
    except Exception as e:
        st.sidebar.error("Could not open SQLite database.")
        st.sidebar.caption(str(e).split("\n")[0])

    st.sidebar.divider()
    st.sidebar.subheader("Database setup")
    with st.sidebar.expander("Create tables & load CSVs", expanded=not connected):
        st.caption("Upload the 4 source CSVs to (re)build the database.")
        f_providers = st.file_uploader("providers_data.csv", type="csv", key="up_prov")
        f_receivers = st.file_uploader("receivers_data.csv", type="csv", key="up_recv")
        f_food = st.file_uploader("food_listings_data.csv", type="csv", key="up_food")
        f_claims = st.file_uploader("claims_data.csv", type="csv", key="up_claims")

        if st.button("⚙️ Create tables & load data", use_container_width=True):
            if not all([f_providers, f_receivers, f_food, f_claims]):
                st.warning("Please upload all 4 CSV files first.")
            elif not connected:
                st.error("Fix the database connection above first.")
            else:
                try:
                    with st.spinner("Creating tables and loading data..."):
                        counts = load_csvs_to_sqlite(engine, {
                            "providers_data": f_providers,
                            "receivers_data": f_receivers,
                            "food_listings_data": f_food,
                            "claims_data": f_claims,
                        })
                    st.success(
                        f"Loaded: providers={counts['providers_data']}, "
                        f"receivers={counts['receivers_data']}, "
                        f"food={counts['food_listings_data']}, "
                        f"claims={counts['claims_data']}"
                    )
                    st.rerun()
                except SQLAlchemyError as e:
                    st.error(f"Load failed: {e}")

    return engine, connected


# ----------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------
def tab_overview(engine):
    st.subheader("Overview")

    try:
        n_providers = run_query(engine, "SELECT COUNT(*) n FROM providers_data")["n"][0]
        n_receivers = run_query(engine, "SELECT COUNT(*) n FROM receivers_data")["n"][0]
        n_listings = run_query(engine, "SELECT COUNT(*) n FROM food_listings_data")["n"][0]
        n_claims = run_query(engine, "SELECT COUNT(*) n FROM claims_data")["n"][0]
        total_qty = run_query(engine, "SELECT COALESCE(SUM(quantity),0) q FROM food_listings_data")["q"][0]
    except Exception:
        st.info("No data yet. Use the sidebar → **Create tables & load CSVs** to get started.")
        return

    if n_providers == 0 and n_listings == 0:
        st.info("Tables are ready but empty. Upload your 4 CSVs via **Database setup** in the sidebar.")
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Providers", f"{n_providers:,}")
    c2.metric("Receivers", f"{n_receivers:,}")
    c3.metric("Food Listings", f"{n_listings:,}")
    c4.metric("Claims", f"{n_claims:,}")
    c5.metric("Total Food Quantity", f"{int(total_qty):,}")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        df = run_query(engine, QUERIES["8. Most common food type"])
        if not df.empty:
            fig = px.pie(df, names="food_type", values="total", title="Food Type Breakdown", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        df = run_query(engine, QUERIES["11. Percentage breakdown of claim status"])
        if not df.empty:
            fig = px.pie(df, names="status", values="percentage", title="Claim Status Breakdown", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

    df = run_query(engine, QUERIES["15. Top 5 cities by total food availability"])
    if not df.empty:
        fig = px.bar(df, x="location", y="total_quantity",
                     title="Top 5 Cities by Food Availability", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

    # Expiring soon alert — SQLite date arithmetic replaces MySQL DATE_ADD / CURDATE
    try:
        expiring = run_query(engine, """
            SELECT food_name, quantity, expiry_date, location, provider_type
            FROM food_listings_data
            WHERE expiry_date <= date('now', '+3 days')
            ORDER BY expiry_date ASC
        """)
        if not expiring.empty:
            st.warning(f"⚠️ {len(expiring)} listing(s) expiring within 3 days")
            st.dataframe(expiring, use_container_width=True, hide_index=True)
    except SQLAlchemyError:
        pass


def tab_browse_filter(engine):
    st.subheader("Browse & Filter Food Listings")

    try:
        cities = run_query(engine, "SELECT DISTINCT location FROM food_listings_data ORDER BY location")["location"].tolist()
        ptypes = run_query(engine, "SELECT DISTINCT provider_type FROM food_listings_data ORDER BY provider_type")["provider_type"].tolist()
        ftypes = run_query(engine, "SELECT DISTINCT food_type FROM food_listings_data ORDER BY food_type")["food_type"].tolist()
        mtypes = run_query(engine, "SELECT DISTINCT meal_type FROM food_listings_data ORDER BY meal_type")["meal_type"].tolist()
    except SQLAlchemyError:
        st.info("No data yet. Use the sidebar to create tables and load your CSVs.")
        return

    f1, f2, f3, f4 = st.columns(4)
    sel_city = f1.multiselect("City", cities)
    sel_ptype = f2.multiselect("Provider Type", ptypes)
    sel_ftype = f3.multiselect("Food Type", ftypes)
    sel_mtype = f4.multiselect("Meal Type", mtypes)

    sql = "SELECT * FROM food_listings_data"
    conditions = []
    if sel_city:
        conditions.append("location IN (" + ",".join(f"'{c}'" for c in sel_city) + ")")
    if sel_ptype:
        conditions.append("provider_type IN (" + ",".join(f"'{c}'" for c in sel_ptype) + ")")
    if sel_ftype:
        conditions.append("food_type IN (" + ",".join(f"'{c}'" for c in sel_ftype) + ")")
    if sel_mtype:
        conditions.append("meal_type IN (" + ",".join(f"'{c}'" for c in sel_mtype) + ")")
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY expiry_date ASC"

    df = run_query(engine, sql)
    st.caption(f"{len(df)} listing(s) match your filters")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Contact lookup, mirrors Query 4 from SQL_ANALYSIS.sql
    st.divider()
    st.markdown("**Find provider contacts in a city** (Query 4)")
    city_pick = st.selectbox("City", [""] + cities, key="contact_city")
    if city_pick:
        contacts = run_query(engine, QUERIES["4. Providers in a specific city"], {"city": city_pick})
        st.dataframe(contacts, use_container_width=True, hide_index=True)


def tab_analysis(engine):
    st.subheader("Analysis — 15 SQL Queries")
    st.caption("Run live against the SQLite database.")

    try:
        run_query(engine, "SELECT 1 FROM food_listings_data LIMIT 1")
    except SQLAlchemyError:
        st.info("No data yet. Use the sidebar to create tables and load your CSVs.")
        return

    query_names = [q for q in QUERIES.keys() if q not in PARAMETERIZED]
    choice = st.selectbox("Choose a query", query_names)

    df = run_query(engine, QUERIES[choice])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Auto-chart where it makes sense (2 columns, one numeric)
    if df.shape[1] == 2:
        num_col = df.columns[1]
        cat_col = df.columns[0]
        if pd.api.types.is_numeric_dtype(df[num_col]):
            chart_df = df.head(15)
            fig = px.bar(chart_df, x=cat_col, y=num_col, title=choice, text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("View SQL"):
        st.code(QUERIES[choice].strip(), language="sql")


def tab_manage_listings(engine):
    st.subheader("Manage Food Listings (CRUD)")

    try:
        providers = run_query(engine, "SELECT provider_id, name, type, city FROM providers_data ORDER BY name")
    except SQLAlchemyError:
        st.info("No data yet. Use the sidebar to create tables and load your CSVs.")
        return

    if providers.empty:
        st.warning("No providers found — load providers_data.csv first.")
        return

    add_tab, update_tab, delete_tab = st.tabs(["➕ Add listing", "✏️ Update listing", "🗑️ Delete listing"])

    with add_tab:
        with st.form("add_listing_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            food_name = c1.text_input("Food name")
            quantity = c2.number_input("Quantity", min_value=1, step=1)

            c3, c4 = st.columns(2)
            expiry = c3.date_input("Expiry date", value=date.today())
            provider_label = c4.selectbox(
                "Provider",
                providers.apply(lambda r: f"{r['provider_id']} — {r['name']} ({r['city']})", axis=1),
            )

            c5, c6 = st.columns(2)
            food_type = c5.selectbox("Food type", ["Vegetarian", "Non-Vegetarian", "Vegan"])
            meal_type = c6.selectbox("Meal type", ["Breakfast", "Lunch", "Dinner", "Snacks"])

            submitted = st.form_submit_button("Add listing", use_container_width=True)
            if submitted:
                if not food_name.strip():
                    st.error("Food name is required.")
                else:
                    provider_id = int(provider_label.split(" — ")[0])
                    provider_row = providers[providers["provider_id"] == provider_id].iloc[0]
                    try:
                        next_id = run_query(engine, "SELECT COALESCE(MAX(food_id),0)+1 AS nid FROM food_listings_data")["nid"][0]
                        run_statement(engine, """
                            INSERT INTO food_listings_data
                                (food_id, food_name, quantity, expiry_date, provider_id,
                                 provider_type, location, food_type, meal_type)
                            VALUES
                                (:fid, :fname, :qty, :exp, :pid, :ptype, :loc, :ftype, :mtype)
                        """, {
                            "fid": int(next_id), "fname": food_name.strip(), "qty": int(quantity),
                            "exp": expiry.strftime("%Y-%m-%d"), "pid": provider_id,
                            "ptype": provider_row["type"], "loc": provider_row["city"],
                            "ftype": food_type, "mtype": meal_type,
                        })
                        st.success(f"Added '{food_name}' (food_id={int(next_id)}).")
                        st.rerun()
                    except SQLAlchemyError as e:
                        st.error(f"Insert failed: {e}")

    with update_tab:
        listings = run_query(engine, "SELECT * FROM food_listings_data ORDER BY food_id DESC")
        if listings.empty or "food_id" not in listings.columns:
            st.info("No listings to update yet. Load data via 'Database setup' in the sidebar, or check the Raw Tables tab.")
        else:
            pick = st.selectbox(
                "Choose listing",
                listings.apply(lambda r: f"{r['food_id']} — {r['food_name']} ({r['location']})", axis=1),
                key="update_pick",
            )
            food_id = int(pick.split(" — ")[0])
            row = listings[listings["food_id"] == food_id].iloc[0]

            with st.form("update_listing_form"):
                c1, c2 = st.columns(2)
                new_qty = c1.number_input("Quantity", min_value=0, step=1, value=int(row["quantity"]))
                new_exp = c2.date_input(
                    "Expiry date",
                    value=pd.to_datetime(row["expiry_date"]).date()
                    if not pd.isna(row["expiry_date"]) else date.today(),
                )
                st.caption(f"Provider: {row['provider_type']} · Location: {row['location']}")
                submitted = st.form_submit_button("Save changes", use_container_width=True)
                if submitted:
                    try:
                        run_statement(engine, """
                            UPDATE food_listings_data
                            SET quantity = :qty, expiry_date = :exp
                            WHERE food_id = :fid
                        """, {"qty": int(new_qty), "exp": new_exp.strftime("%Y-%m-%d"), "fid": food_id})
                        st.success("Updated.")
                        st.rerun()
                    except SQLAlchemyError as e:
                        st.error(f"Update failed: {e}")

    with delete_tab:
        listings = run_query(engine, "SELECT * FROM food_listings_data ORDER BY food_id DESC")
        if listings.empty or "food_id" not in listings.columns:
            st.info("No listings to delete yet. Load data via 'Database setup' in the sidebar, or check the Raw Tables tab.")
        else:
            pick = st.selectbox(
                "Choose listing to delete",
                listings.apply(lambda r: f"{r['food_id']} — {r['food_name']} ({r['location']})", axis=1),
                key="delete_pick",
            )
            food_id = int(pick.split(" — ")[0])
            st.caption("Deleting a listing also removes its related claims.")
            confirm = st.checkbox("I understand this cannot be undone.")
            if st.button("Delete listing", type="primary", disabled=not confirm):
                try:
                    run_statement(engine, "DELETE FROM food_listings_data WHERE food_id = :fid", {"fid": food_id})
                    st.success("Deleted.")
                    st.rerun()
                except SQLAlchemyError as e:
                    st.error(f"Delete failed: {e}")


def tab_raw_tables(engine):
    st.subheader("Raw Tables")
    table = st.radio(
        "Table", ["providers_data", "receivers_data", "food_listings_data", "claims_data"],
        horizontal=True,
    )
    try:
        df = run_query(engine, f"SELECT * FROM {table}")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(df)} row(s)")
    except SQLAlchemyError:
        st.info("No data yet. Use the sidebar to create tables and load your CSVs.")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    st.title("🍱 Food Management System")
    st.caption("Connecting surplus food providers with receivers — built on SQLite3")

    engine, connected = sidebar_connection()

    if not connected:
        st.error(
            "Could not open the SQLite database. Check the file path in the sidebar."
        )
        st.info(
            "First time? The database file will be created automatically once you "
            "specify a path and click **Create tables & load data**."
        )
        return

    tabs = st.tabs(["Overview", "Browse & Filter", "Analysis (15 Queries)", "Manage Listings", "Raw Tables"])
    with tabs[0]:
        tab_overview(engine)
    with tabs[1]:
        tab_browse_filter(engine)
    with tabs[2]:
        tab_analysis(engine)
    with tabs[3]:
        tab_manage_listings(engine)
    with tabs[4]:
        tab_raw_tables(engine)


if __name__ == "__main__":
    main()
