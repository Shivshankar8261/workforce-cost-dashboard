## Interactive Workforce Dashboard (Streamlit)

This dashboard turns the project dataset into an interactive, presentation-ready web experience:

- KPI overview (headcount, salary cost, performance, satisfaction, resignation rate)
- Department drill-down (compare departments on key metrics)
- Productivity drivers (relationships between hours, overtime, projects, training, satisfaction)
- Resignation insights (resignation rate by segments + risk signals)
- Data explorer (filtered table + CSV download)

### Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

### Data

The app loads `Employee_Performance_and_Productivity_Data.xlsx` from the repo root.
