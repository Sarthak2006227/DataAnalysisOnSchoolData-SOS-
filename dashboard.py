import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Student Performance Dashboard", layout="wide", page_icon="📊")

# ---------- Load Data ----------
@st.cache_data
def load_data():
    files = {
        2023: "data/SOSResults2023.csv",
        2024: "data/SOSResults2024.csv",
        2025: "data/SOSResults2025.csv"
    }
    dfs = []
    
    for year, path in files.items():
        try:
            # First try parsing as Excel (since 2023 and 2024 are xlsx saved as .csv)
            df = pd.read_excel(path)
        except Exception:
            # If it fails, fallback to standard CSV
            df = pd.read_csv(
                path,
                encoding="latin-1",
                engine="python",
                on_bad_lines="skip"
            )
            
        # Remove any existing year column to prevent conflicts
        df = df.loc[:, ~df.columns.str.lower().str.contains("year")]
        
        # Add the explicit Year column
        df["Year"] = year
        dfs.append(df)
        
    data = pd.concat(dfs, ignore_index=True)
    
    # Standardize column names (strip whitespace)
    data.columns = data.columns.str.strip()
    
    return data

with st.spinner("Loading Data..."):
    data = load_data()

# ---------- Data Cleaning ----------
NAME_COL = "Name"
CLASS_COL = "Standard"
SCORE_COL = "tea_score"

# Fix name column
data[NAME_COL] = data[NAME_COL].astype(str)
data = data[data[NAME_COL].str.lower() != "nan"]
data = data.dropna(subset=[NAME_COL])

# Ensure Score is numeric and drop invalid scores
data[SCORE_COL] = pd.to_numeric(data[SCORE_COL], errors='coerce')
data = data.dropna(subset=[SCORE_COL])

if data.empty:
    st.error("No valid data could be loaded. Please check your data files.")
    st.stop()


# ---------- Sidebar Filters ----------
st.sidebar.title("🔍 Filters")
st.sidebar.markdown("---")

# Year filter
available_years = sorted(data["Year"].unique())
selected_year = st.sidebar.selectbox("📅 Select Year", available_years, index=len(available_years)-1)

# School filter
school_col_name = "sch_name" if "sch_name" in data.columns else "School Name" if "School Name" in data.columns else None
if school_col_name:
    available_schools = ["All Schools"] + sorted(data[school_col_name].dropna().unique())
    selected_school = st.sidebar.selectbox("🏫 Select School", available_schools)
else:
    selected_school = "All Schools"

# Student filter
if selected_school != "All Schools" and school_col_name:
    available_students = sorted(data[data[school_col_name] == selected_school][NAME_COL].unique())
else:
    available_students = sorted(data[NAME_COL].unique())
    
selected_student = st.sidebar.selectbox("👤 Select Student", available_students)


# ---------- Dashboard Header ----------
st.title("📊 Student Performance Dashboard")
st.markdown("Monitor and analyze student academic performance across multiple years.")
st.markdown("---")

# ---------- Filter Data ----------
# We filter the overall data by year
year_filtered = data[data["Year"] == selected_year]
if selected_school != "All Schools" and school_col_name:
    year_filtered = year_filtered[year_filtered[school_col_name] == selected_school]

# And we get the specific student data across ALL years for the trend chart
student_data = data[data[NAME_COL] == selected_student].sort_values("Year")

if year_filtered.empty:
    st.warning("No data available for the selected year.")
else:
    # ---------- KPI Section ----------
    col1, col2, col3 = st.columns(3)
    col1.metric(f"Average Score ({selected_year})", round(year_filtered[SCORE_COL].mean(), 2))
    col2.metric(f"Highest Score ({selected_year})", round(year_filtered[SCORE_COL].max(), 2))
    col3.metric(f"Lowest Score ({selected_year})", round(year_filtered[SCORE_COL].min(), 2))

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- Charts Section 1 ----------
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader(f"📈 Score Distribution ({selected_year})")
        fig1 = px.histogram(
            year_filtered, 
            x=SCORE_COL, 
            nbins=20, 
            color_discrete_sequence=["#00C4B4"],
            labels={SCORE_COL: "Score"},
            marginal="box",
            opacity=0.85
        )
        fig1.update_layout(
            showlegend=False, 
            plot_bgcolor="rgba(0,0,0,0)", 
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)", zeroline=False),
            margin=dict(l=0, r=0, t=30, b=20)
        )
        fig1.update_traces(marker_line_width=1, marker_line_color="rgba(255,255,255,0.3)")
        st.plotly_chart(fig1, use_container_width=True)

    with chart_col2:
        st.subheader(f"📊 Class-wise Performance ({selected_year})")
        if CLASS_COL in year_filtered.columns:
            class_perf = year_filtered.groupby(CLASS_COL)[SCORE_COL].agg(["mean","max","min"]).reset_index()
            # Convert values to 2 decimal places purely for display if possible, or just plot
            class_perf = class_perf.round(2)
            fig2 = px.bar(
                class_perf, 
                x=CLASS_COL, 
                y=["mean","max","min"], 
                barmode="group",
                labels={"value": "Score", "variable": "Metric", CLASS_COL: "Class Standard"},
                color_discrete_sequence=["#FF7A59", "#00B4D8", "#8A2BE2"]
            )
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", 
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, zeroline=False, tickmode="linear"),
                yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)", zeroline=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
                margin=dict(l=0, r=0, t=30, b=20)
            )
            fig2.update_traces(marker_line_width=0, opacity=0.9)
            st.plotly_chart(fig2, use_container_width=True)

    # ---------- School-wise Analysis ----------
    st.markdown("---")
    
    # Identify the correct school column name dynamically
    school_col_name = "sch_name" if "sch_name" in year_filtered.columns else "School Name" if "School Name" in year_filtered.columns else None
    
    if school_col_name and school_col_name in year_filtered.columns:
        if selected_school == "All Schools":
            st.subheader(f"🏫 School-wise Analysis ({selected_year})")
            school_perf = year_filtered.groupby(school_col_name)[SCORE_COL].agg(["mean", "count"]).reset_index()
            school_perf = school_perf.rename(columns={"mean": "Average Score", "count": "Total Students"})
            school_perf = school_perf.round(2)
            
            school_chart_col, school_data_col = st.columns([2, 1])
            with school_chart_col:
                fig_school = px.bar(
                    school_perf.sort_values("Average Score", ascending=False),
                    x=school_col_name,
                    y="Average Score",
                    text="Average Score",
                    hover_data=["Total Students"],
                    labels={school_col_name: "School Name", "Average Score": "Average Score"},
                    color="Average Score",
                    color_continuous_scale="Plasma",
                )
                fig_school.update_traces(
                    texttemplate='<b>%{text}</b>', 
                    textposition='outside',
                    outsidetextfont=dict(size=12),
                    marker_line_width=0
                )
                fig_school.update_layout(
                    xaxis_tickangle=-45, 
                    coloraxis_showscale=False,
                    plot_bgcolor="rgba(0,0,0,0)", 
                    paper_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False, zeroline=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)", zeroline=False),
                    margin=dict(l=0, r=0, t=30, b=80)
                )
                st.plotly_chart(fig_school, use_container_width=True)
                
            with school_data_col:
                st.dataframe(school_perf.sort_values("Average Score", ascending=False).set_index(school_col_name), use_container_width=True)
        else:
            st.subheader(f"🏫 School Insights: {selected_school}")
            
            sch_kpi1, sch_kpi2, sch_kpi3 = st.columns(3)
            
            avg_school_score = round(year_filtered[SCORE_COL].mean(), 2) if not year_filtered.empty else 0
            total_students_yr = len(year_filtered)
            
            sch_kpi1.metric(f"School Average Score ({selected_year})", avg_school_score)
            sch_kpi2.metric(f"Total Students ({selected_year})", total_students_yr)
            
            if "Age_Group" in year_filtered.columns and not year_filtered.empty:
                prominent_age = year_filtered["Age_Group"].mode()[0]
                sch_kpi3.metric(f"Prominent Age Group ({selected_year})", prominent_age)
            else:
                sch_kpi3.metric(f"Prominent Age Group ({selected_year})", "N/A")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            sch_col1, sch_col2 = st.columns(2)
            with sch_col1:
                st.markdown(f"**👨‍🎓 Age Group Analysis ({selected_year})**")
                if "Age_Group" in year_filtered.columns and not year_filtered.empty:
                    age_data = year_filtered.groupby("Age_Group").size().reset_index(name="Count")
                    fig_age = px.pie(
                        age_data, 
                        names="Age_Group", 
                        values="Count",
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig_age.update_traces(textposition='inside', textinfo='percent+label')
                    fig_age.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=0, r=0, t=30, b=20),
                        showlegend=False
                    )
                    st.plotly_chart(fig_age, use_container_width=True)
                else:
                    st.info("Age group data not available.")
            
            with sch_col2:
                st.markdown(f"**📚 Grade-wise Analysis ({selected_year})**")
                if CLASS_COL in year_filtered.columns and not year_filtered.empty:
                    grade_avg = year_filtered.groupby(CLASS_COL)[SCORE_COL].mean().reset_index()
                    grade_avg = grade_avg.round(2)
                    fig_grade = px.bar(
                        grade_avg,
                        x=CLASS_COL,
                        y=SCORE_COL,
                        text=SCORE_COL,
                        labels={CLASS_COL: "Grade", SCORE_COL: "Average Score"},
                        color=SCORE_COL,
                        color_continuous_scale="Tealgrn"
                    )
                    fig_grade.update_traces(
                        texttemplate='<b>%{text}</b>', 
                        textposition='outside',
                        marker_line_width=0
                    )
                    fig_grade.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(showgrid=False, zeroline=False, type="category" if grade_avg[CLASS_COL].dtype == object else "category"),
                        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)", zeroline=False),
                        margin=dict(l=0, r=0, t=30, b=20),
                        coloraxis_showscale=False
                    )
                    st.plotly_chart(fig_grade, use_container_width=True)
                else:
                    st.info("Grade data not available.")
    else:
        st.info("School information is not available in the dataset for this year.")

# ---------- Charts Section 2 (Student Specific) ----------
st.markdown("---")
st.subheader(f"🎓 Individual Insights & Journey: {selected_student}")

if not student_data.empty:
    
    # Setup Data for Insights & Comparison
    latest_year_student = student_data.iloc[-1]
    latest_score = latest_year_student[SCORE_COL]
    
    # Calculate comparative metrics
    # Compare student against their standard (class) average for the latest year
    latest_standard = latest_year_student[CLASS_COL] if CLASS_COL in latest_year_student else None
    
    comparative_df = data[(data["Year"] == latest_year_student["Year"]) & (data[CLASS_COL] == latest_standard)]
    class_average = round(comparative_df[SCORE_COL].mean(), 2) if not comparative_df.empty else 0
    
    diff_from_avg = round(latest_score - class_average, 2)
    diff_indicator = "above" if diff_from_avg >= 0 else "below"
    
    # Student specific KPIs
    st_kpi1, st_kpi2, st_kpi3, st_kpi4 = st.columns(4)
    st_kpi1.metric(f"Latest Score ({latest_year_student['Year']})", latest_score)
    st_kpi2.metric("Class Average", class_average, f"{diff_from_avg} vs Avg")
    st_kpi3.metric("Personal Best", student_data[SCORE_COL].max())
    st_kpi4.metric("Avg Score (All Years)", round(student_data[SCORE_COL].mean(), 2))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Setup Columns for Insights and Charts
    student_col1, student_col2 = st.columns([2, 1])
    
    with student_col1:
        st.markdown("**Performance Trend Over Years**")
        
        # Calculate class averages across all available years for the student's standards
        trend_data = student_data.copy()
        class_avgs = []
        for _, row in trend_data.iterrows():
            yr = row["Year"]
            std = row[CLASS_COL]
            avg_score = data[(data["Year"] == yr) & (data[CLASS_COL] == std)][SCORE_COL].mean()
            class_avgs.append(avg_score)
        
        trend_data["Class_Avg"] = class_avgs
        
        # Melt data for grouped line plotting
        trend_melt = trend_data.melt(id_vars=["Year"], value_vars=[SCORE_COL, "Class_Avg"], 
                                     var_name="Metric", value_name="Value")
        trend_melt["Metric"] = trend_melt["Metric"].replace({SCORE_COL: "Student Score", "Class_Avg": "Class Average"})
        
        fig3 = px.line(
            trend_melt,
            x="Year",
            y="Value",
            color="Metric",
            markers=True,
            text="Value",
            labels={"Value": "Score", "Year": "Year"},
            color_discrete_sequence=["#00D2D3", "#FF6B6B"]
        )
        fig3.update_traces(
            textposition="top center", 
            texttemplate='<b>%{text:.2s}</b>',
            line=dict(width=3),
            marker=dict(size=10, line=dict(width=2, color="white"))
        )
        fig3.update_layout(
            xaxis=dict(
                tickmode='array', 
                tickvals=available_years, 
                ticktext=[str(y) for y in available_years],
                showgrid=False, zeroline=False
            ),
            yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)", zeroline=False),
            plot_bgcolor="rgba(0,0,0,0)", 
            paper_bgcolor="rgba(0,0,0,0)",
            legend_title_text='',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=30, b=20)
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    with student_col2:
        st.markdown("**Automated Insights Summary**")
        
        # Generate some smart insights based on data
        insights = []
        
        # Insight 1: Performance against avg
        if diff_from_avg >= 0:
            insights.append(f"🟢 **Exceeding Expectations**: Scored **{diff_from_avg} points above** the class average in {latest_year_student['Year']}.")
        else:
            insights.append(f"🔴 **Needs Attention**: Scored **{abs(diff_from_avg)} points below** the class average in {latest_year_student['Year']}.")
            
        # Insight 2: Improvement
        if len(student_data) > 1:
            first_score = student_data.iloc[0][SCORE_COL]
            score_diff = round(latest_score - first_score, 2)
            if score_diff > 0:
                insights.append(f"📈 **Trending Up**: Improved overall by **{score_diff} points** since {student_data.iloc[0]['Year']}.")
            elif score_diff < 0:
                insights.append(f"📉 **Trending Down**: Performance dropped by **{abs(score_diff)} points** since {student_data.iloc[0]['Year']}.")
            else:
                insights.append(f"➡️ **Consistent**: Performance has remained steady since {student_data.iloc[0]['Year']}.")
        
        # Insight 3: Percentile or rank estimation (if available)
        if "tea_rank" in latest_year_student and pd.notna(latest_year_student["tea_rank"]):
            insights.append(f"🏆 **Current Rank**: Holds rank **{latest_year_student['tea_rank']}** in standard {latest_standard} ({latest_year_student['Year']}).")
        
        # Render Insights visually appealing
        for ins in insights:
            st.info(ins)
            
        st.markdown("<br>**Student Records:**", unsafe_allow_html=True)
        cols_to_show = ["Year", CLASS_COL, SCORE_COL]
        # Only include tea_rank if available
        if "tea_rank" in student_data.columns:
            cols_to_show.append("tea_rank")
            
        display_df = student_data[cols_to_show].reset_index(drop=True)
        st.dataframe(display_df, use_container_width=True)
else:
    st.warning(f"No records found for {selected_student}.")