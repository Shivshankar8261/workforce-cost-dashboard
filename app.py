from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


DATA_PATH = "Employee_Performance_and_Productivity_Data.xlsx"
SHEET_NAME = "Extended_Employee_Performance_a"
APP_DATA_VERSION = "2026-04-29-headcount-fix"


@st.cache_data(show_spinner=False)
def load_data(
    path: str = DATA_PATH, sheet_name: str = SHEET_NAME, _data_version: str = APP_DATA_VERSION
) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")

    # Normalize types
    if "Hire_Date" in df.columns:
        # Match the notebook's `to_date` behavior (date-level granularity).
        # This prevents default date-range filtering from excluding rows on the max date
        # due to time-of-day components coming from Excel.
        df["Hire_Date"] = pd.to_datetime(df["Hire_Date"], errors="coerce").dt.normalize()

    # Derived columns (match the notebook logic)
    df["Resigned_Numeric"] = np.where(df["Resigned"] == True, 1, 0)

    df["Salary_Category"] = np.select(
        [
            df["Monthly_Salary"] < 5000,
            (df["Monthly_Salary"] >= 5000) & (df["Monthly_Salary"] < 10000),
        ],
        ["Low", "Medium"],
        default="High",
    )

    df["Productivity_Level"] = np.select(
        [
            df["Performance_Score"] < 3,
            (df["Performance_Score"] >= 3) & (df["Performance_Score"] < 4),
        ],
        ["Low", "Average"],
        default="High",
    )

    df["Overtime_Status"] = np.select(
        [
            df["Overtime_Hours"] == 0,
            (df["Overtime_Hours"] > 0) & (df["Overtime_Hours"] <= 10),
        ],
        ["No Overtime", "Moderate Overtime"],
        default="High Overtime",
    )

    return df


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.subheader("Filters")

    dept = st.sidebar.multiselect("Department", sorted(df["Department"].dropna().unique().tolist()))
    gender = st.sidebar.multiselect("Gender", sorted(df["Gender"].dropna().unique().tolist()))
    job = st.sidebar.multiselect("Job Title", sorted(df["Job_Title"].dropna().unique().tolist()))
    edu = st.sidebar.multiselect("Education", sorted(df["Education_Level"].dropna().unique().tolist()))

    salary_cat = st.sidebar.multiselect(
        "Salary Category", ["Low", "Medium", "High"], default=["Low", "Medium", "High"]
    )
    prod = st.sidebar.multiselect(
        "Productivity Level", ["Low", "Average", "High"], default=["Low", "Average", "High"]
    )
    overtime = st.sidebar.multiselect(
        "Overtime Status",
        ["No Overtime", "Moderate Overtime", "High Overtime"],
        default=["No Overtime", "Moderate Overtime", "High Overtime"],
    )
    resigned = st.sidebar.multiselect("Resigned", [False, True], default=[False, True])

    if "Hire_Date" in df.columns and df["Hire_Date"].notna().any():
        min_d = df["Hire_Date"].min().date()
        max_d = df["Hire_Date"].max().date()
        d1, d2 = st.sidebar.date_input("Hire Date Range", value=(min_d, max_d))
    else:
        d1 = d2 = None

    out = df.copy()
    if dept:
        out = out[out["Department"].isin(dept)]
    if gender:
        out = out[out["Gender"].isin(gender)]
    if job:
        out = out[out["Job_Title"].isin(job)]
    if edu:
        out = out[out["Education_Level"].isin(edu)]
    if salary_cat:
        out = out[out["Salary_Category"].isin(salary_cat)]
    if prod:
        out = out[out["Productivity_Level"].isin(prod)]
    if overtime:
        out = out[out["Overtime_Status"].isin(overtime)]
    if resigned:
        out = out[out["Resigned"].isin(resigned)]
    if d1 and d2 and "Hire_Date" in out.columns:
        # Compare on date granularity (inclusive) to avoid dropping rows due to time components.
        hd = pd.to_datetime(out["Hire_Date"], errors="coerce").dt.date
        out = out[(hd >= d1) & (hd <= d2)]

    return out


def kpis(df: pd.DataFrame) -> dict[str, float]:
    if len(df) == 0:
        return {
            "Headcount": 0,
            "Monthly salary cost": 0.0,
            "Avg performance": float("nan"),
            "Avg satisfaction": float("nan"),
            "Avg overtime": float("nan"),
            "Resignation rate": float("nan"),
        }

    return {
        "Headcount": int(len(df)),
        "Monthly salary cost": float(df["Monthly_Salary"].sum()),
        "Avg performance": float(df["Performance_Score"].mean()),
        "Avg satisfaction": float(df["Employee_Satisfaction_Score"].mean()),
        "Avg overtime": float(df["Overtime_Hours"].mean()),
        "Resignation rate": float(df["Resigned_Numeric"].mean()),
    }


def fmt_money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.0f}"


def fmt_rate(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x*100:.2f}%"


def main() -> None:
    st.set_page_config(page_title="Workforce Cost & Productivity Dashboard", layout="wide")

    st.title("Workforce Cost Optimization & Productivity Dashboard")
    st.caption(
        "Interactive view of performance, productivity drivers, workforce cost patterns, and resignation signals "
        "based on the 100,000-row dataset."
    )

    # Streamlit Cloud can keep cached data across redeploys.
    # Provide a clear-cache control so the displayed KPIs always reflect the latest code + data.
    with st.sidebar:
        st.divider()
        if st.button("Clear cache & reload", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    df = load_data()
    filt = apply_filters(df)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    metrics = kpis(filt)
    c1.metric("Headcount", f"{metrics['Headcount']:,}")
    c2.metric("Monthly salary cost", fmt_money(metrics["Monthly salary cost"]))
    c3.metric("Avg performance", f"{metrics['Avg performance']:.2f}" if metrics["Headcount"] else "—")
    c4.metric("Avg satisfaction", f"{metrics['Avg satisfaction']:.2f}" if metrics["Headcount"] else "—")
    c5.metric("Avg overtime hours", f"{metrics['Avg overtime']:.2f}" if metrics["Headcount"] else "—")
    c6.metric("Resignation rate", fmt_rate(metrics["Resignation rate"]))

    st.divider()

    tab_overview, tab_dept, tab_drivers, tab_resign, tab_data = st.tabs(
        ["Overview", "Department drill-down", "Drivers", "Resignation insights", "Data explorer"]
    )

    with tab_overview:
        dept_summary = (
            filt.groupby("Department", dropna=False)
            .agg(
                avg_performance_score=("Performance_Score", "mean"),
                avg_monthly_salary=("Monthly_Salary", "mean"),
                avg_overtime_hours=("Overtime_Hours", "mean"),
                avg_satisfaction_score=("Employee_Satisfaction_Score", "mean"),
                avg_resignation_rate=("Resigned_Numeric", "mean"),
                employee_count=("Employee_ID", "count"),
            )
            .reset_index()
            .sort_values("employee_count", ascending=False)
        )

        st.subheader("Key visualizations")
        st.caption("Simple charts aligned with your report section (performance, salary, productivity, overtime).")

        r1c1, r1c2 = st.columns(2)
        with r1c1:
            fig = px.bar(
                dept_summary,
                x="Department",
                y="avg_performance_score",
                title="Department-wise performance analysis (average performance score)",
                labels={"avg_performance_score": "Avg performance score"},
                text_auto=".2f",
            )
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
            fig.update_yaxes(range=[0, 5])
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Insight: helps identify high-performing departments and departments needing improvement.")

        with r1c2:
            fig = px.bar(
                dept_summary,
                x="Department",
                y="avg_monthly_salary",
                title="Salary distribution analysis (average monthly salary by department)",
                labels={"avg_monthly_salary": "Avg monthly salary"},
                text_auto=".0f",
            )
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Insight: highlights cost-heavy departments for budgeting and workforce cost optimization.")

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            p1 = (
                filt.groupby("Productivity_Level")
                .size()
                .reset_index(name="employee_count")
                .sort_values("employee_count", ascending=False)
            )
            fig2 = px.pie(
                p1,
                names="Productivity_Level",
                values="employee_count",
                title="Productivity level distribution (Low / Average / High)",
                hole=0.45,
                category_orders={"Productivity_Level": ["Low", "Average", "High"]},
            )
            fig2.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Insight: shows overall workforce efficiency and productivity balance.")

        with r2c2:
            ot = (
                filt.groupby("Overtime_Status")
                .size()
                .reset_index(name="employee_count")
            )
            ot_order = ["No Overtime", "Moderate Overtime", "High Overtime"]
            ot["Overtime_Status"] = pd.Categorical(ot["Overtime_Status"], ot_order, ordered=True)
            ot = ot.sort_values("Overtime_Status")
            fig3 = px.bar(
                ot,
                x="Overtime_Status",
                y="employee_count",
                title="Overtime analysis (distribution of overtime status)",
                labels={"employee_count": "Employees", "Overtime_Status": "Overtime status"},
                text_auto=True,
            )
            fig3.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(fig3, use_container_width=True)
            st.caption("Insight: indicates overtime workload intensity across the workforce.")

        st.subheader("Department summary (matches notebook aggregation)")
        st.dataframe(
            dept_summary.assign(
                avg_resignation_rate=lambda d: (d["avg_resignation_rate"] * 100).round(2).astype(str) + "%"
            ),
            use_container_width=True,
            hide_index=True,
        )

    with tab_dept:
        dept_pick = st.selectbox("Select a department", sorted(filt["Department"].dropna().unique().tolist()))
        ddf = filt[filt["Department"] == dept_pick]

        left, right = st.columns([1.0, 1.0])
        with left:
            fig = px.histogram(
                ddf,
                x="Monthly_Salary",
                nbins=30,
                title=f"{dept_pick}: Salary distribution",
            )
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with right:
            fig = px.box(
                ddf,
                x="Productivity_Level",
                y="Employee_Satisfaction_Score",
                title=f"{dept_pick}: Satisfaction by productivity level",
                category_orders={"Productivity_Level": ["Low", "Average", "High"]},
            )
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Quick stats")
        ms = kpis(ddf)
        st.write(
            {
                "Headcount": ms["Headcount"],
                "Avg salary": round(float(ddf["Monthly_Salary"].mean()), 2) if ms["Headcount"] else None,
                "Avg performance": round(ms["Avg performance"], 3) if ms["Headcount"] else None,
                "Avg satisfaction": round(ms["Avg satisfaction"], 3) if ms["Headcount"] else None,
                "Avg overtime": round(ms["Avg overtime"], 3) if ms["Headcount"] else None,
                "Resignation rate": fmt_rate(ms["Resignation rate"]),
            }
        )

    with tab_drivers:
        st.subheader("Productivity & cost drivers")
        st.caption(
            "Simple, presentation-ready views of the same relationships. "
            "These charts are designed to be easy to explain in a viva/presentation."
        )

        view_mode = st.radio(
            "Chart style",
            ["Simple (recommended)", "Advanced (scatter/density)"],
            horizontal=True,
        )

        c1, c2 = st.columns(2)

        if view_mode == "Simple (recommended)":
            with c1:
                # 1) Line chart: average satisfaction across training-hour bins
                b = filt[["Training_Hours", "Employee_Satisfaction_Score"]].dropna()
                if len(b):
                    b = b.copy()
                    b["Training_Bin"] = pd.cut(
                        b["Training_Hours"],
                        bins=[0, 20, 40, 60, 80, 100],
                        include_lowest=True,
                    ).astype(str)
                    sat_by_bin = (
                        b.groupby("Training_Bin")["Employee_Satisfaction_Score"]
                        .mean()
                        .reset_index(name="avg_satisfaction")
                    )
                    fig = px.line(
                        sat_by_bin,
                        x="Training_Bin",
                        y="avg_satisfaction",
                        markers=True,
                        title="Average satisfaction across training hour ranges",
                        labels={"avg_satisfaction": "Avg satisfaction score", "Training_Bin": "Training hours (range)"},
                    )
                    fig.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10))
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("Interpretation: the line shows how the average satisfaction score changes across training ranges.")
                else:
                    st.info("Not enough data after filters to build the training chart.")

            with c2:
                # 2) Pie chart: productivity distribution (already used elsewhere, repeated here for storytelling)
                p = (
                    filt.groupby("Productivity_Level")
                    .size()
                    .reset_index(name="employee_count")
                    .sort_values("employee_count", ascending=False)
                )
                fig = px.pie(
                    p,
                    names="Productivity_Level",
                    values="employee_count",
                    title="Productivity mix (share of employees)",
                    hole=0.45,
                    category_orders={"Productivity_Level": ["Low", "Average", "High"]},
                )
                fig.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
                st.plotly_chart(fig, use_container_width=True)

        else:
            # Advanced views (kept for exploration)
            with c1:
                fmt1 = st.selectbox(
                    "Work hours vs performance format",
                    ["Scatter (sampled)", "2D density heatmap", "Binned box plot"],
                    index=0,
                )

                base1 = filt if len(filt) == 0 else filt.copy()
                s1 = base1.sample(min(len(base1), 8000), random_state=7) if (fmt1 == "Scatter (sampled)") else base1

                if fmt1 == "2D density heatmap":
                    fig = px.density_heatmap(
                        s1,
                        x="Work_Hours_Per_Week",
                        y="Performance_Score",
                        title="Work hours vs performance (2D density)",
                        nbinsx=40,
                        nbinsy=20,
                        color_continuous_scale="Blues",
                    )
                    fig.update_traces(
                        hovertemplate="Work hours bin=%{x}<br>Performance bin=%{y}<br>Count=%{z}<extra></extra>"
                    )
                elif fmt1 == "Binned box plot":
                    b = s1.copy()
                    b["Work_Hours_Bin"] = pd.qcut(b["Work_Hours_Per_Week"], q=4, duplicates="drop").astype(str)
                    fig = px.box(
                        b,
                        x="Work_Hours_Bin",
                        y="Performance_Score",
                        color="Overtime_Status",
                        title="Performance distribution by work-hours quartile (colored by overtime status)",
                    )
                    fig.update_xaxes(title="Work hours per week (quartiles)")
                else:
                    fig = px.scatter(
                        s1,
                        x="Work_Hours_Per_Week",
                        y="Performance_Score",
                        color="Overtime_Status",
                        title="Work hours vs performance (colored by overtime status)",
                        opacity=0.35,
                    )
                fig.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10))
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                fmt2 = st.selectbox(
                    "Training hours vs satisfaction format",
                    ["Scatter (sampled)", "2D density heatmap", "Binned violin plot"],
                    index=0,
                )

                base2 = filt if len(filt) == 0 else filt.copy()
                s2 = base2.sample(min(len(base2), 8000), random_state=9) if (fmt2 == "Scatter (sampled)") else base2

                if fmt2 == "2D density heatmap":
                    fig = px.density_heatmap(
                        s2,
                        x="Training_Hours",
                        y="Employee_Satisfaction_Score",
                        title="Training hours vs satisfaction (2D density)",
                        nbinsx=40,
                        nbinsy=25,
                        color_continuous_scale="Purples",
                    )
                    fig.update_traces(
                        hovertemplate="Training bin=%{x}<br>Satisfaction bin=%{y}<br>Count=%{z}<extra></extra>"
                    )
                elif fmt2 == "Binned violin plot":
                    b = s2.copy()
                    b["Training_Hours_Bin"] = pd.qcut(b["Training_Hours"], q=4, duplicates="drop").astype(str)
                    fig = px.violin(
                        b,
                        x="Training_Hours_Bin",
                        y="Employee_Satisfaction_Score",
                        color="Productivity_Level",
                        box=True,
                        points=False,
                        title="Satisfaction distribution by training-hours quartile (colored by productivity level)",
                        category_orders={"Productivity_Level": ["Low", "Average", "High"]},
                    )
                    fig.update_xaxes(title="Training hours (quartiles)")
                else:
                    fig = px.scatter(
                        s2,
                        x="Training_Hours",
                        y="Employee_Satisfaction_Score",
                        color="Productivity_Level",
                        title="Training hours vs satisfaction (colored by productivity level)",
                        opacity=0.35,
                        category_orders={"Productivity_Level": ["Low", "Average", "High"]},
                    )
                fig.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10))
                st.plotly_chart(fig, use_container_width=True)

        corr_cols = [
            "Performance_Score",
            "Monthly_Salary",
            "Work_Hours_Per_Week",
            "Projects_Handled",
            "Overtime_Hours",
            "Sick_Days",
            "Remote_Work_Frequency",
            "Team_Size",
            "Training_Hours",
            "Promotions",
            "Employee_Satisfaction_Score",
            "Resigned_Numeric",
        ]
        corr = filt[corr_cols].corr(numeric_only=True)
        fig = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            title="Correlation heatmap (numeric columns)",
        )
        fig.update_layout(height=560, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with tab_resign:
        st.subheader("Resignation / attrition signals")

        seg = st.selectbox(
            "Segment by",
            ["Department", "Job_Title", "Education_Level", "Productivity_Level", "Salary_Category", "Overtime_Status"],
        )
        resign_by = (
            filt.groupby(seg, dropna=False)["Resigned_Numeric"]
            .mean()
            .reset_index(name="resignation_rate")
            .sort_values("resignation_rate", ascending=False)
        )

        fig = px.bar(
            resign_by,
            x=seg,
            y="resignation_rate",
            title=f"Resignation rate by {seg}",
            labels={"resignation_rate": "Resignation rate"},
        )
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10))
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

        st.caption("Tip for presentation: highlight the top segments, then propose targeted interventions.")
        st.dataframe(
            resign_by.assign(resignation_rate=lambda d: (d["resignation_rate"] * 100).round(2).astype(str) + "%"),
            use_container_width=True,
            hide_index=True,
        )

    with tab_data:
        st.subheader("Filtered dataset")
        st.caption("Download the currently filtered data for further reporting or Power BI/Tableau import.")

        show_n = st.slider("Rows to display", 50, 1000, 200)
        st.dataframe(filt.head(show_n), use_container_width=True, hide_index=True)

        csv = filt.to_csv(index=False).encode("utf-8")
        st.download_button("Download filtered CSV", data=csv, file_name="filtered_workforce_data.csv")


if __name__ == "__main__":
    main()

