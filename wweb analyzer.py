import streamlit as st
import pandas as pd
import io

# Page configuration
st.set_page_config(
    page_title="Fund Analyzer Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern look
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f5;
    }
    .stButton>button {
        width: 100%;
        background-color: #2563eb;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
    }
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1 {
        color: #1e293b;
    }
    .stDataFrame {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'df_raw' not in st.session_state:
    st.session_state.df_raw = None
if 'df_final' not in st.session_state:
    st.session_state.df_final = None

# Header
st.title("📊 Genco & Beneficiary Fund Analyzer")
st.markdown("### Analyze and export fund data with ease")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📁 Upload & Filter")

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['xlsx', 'xls', 'csv'],
        help="Upload Excel or CSV file containing fund data"
    )

    if uploaded_file is not None:
        st.success("✅ File uploaded successfully!")

    st.markdown("---")

    # Region filter (will be populated after file upload)
    if st.session_state.df_raw is not None:
        if 'REGION' in st.session_state.df_raw.columns:
            regions = ['All Regions'] + sorted(
                st.session_state.df_raw['REGION'].dropna().unique().tolist()
            )
            selected_region = st.selectbox(
                "🔍 Filter by Region",
                regions,
                key='region_filter'
            )
        else:
            selected_region = 'All Regions'
            st.info("ℹ️ No REGION column found")

    st.markdown("---")
    st.markdown("### 📋 Required Columns")
    st.code("""
- GENCO/ERD
- BENEFICIARIES
- FUND
- AMOUNT
- REGION (optional)
    """)

# Main content area
if uploaded_file is None:
    # Welcome screen
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("👈 Upload a file from the sidebar to get started")
        st.markdown("""
        ### How to use:
        1. **Upload** your Excel or CSV file
        2. **Filter** by region (optional)
        3. **View** analyzed results
        4. **Download** the processed data
        """)
else:
    # Process uploaded file
    try:
        # Read file
        if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
except Exception as e:
    st.error(f"Error reading file: {str(e)}")
    st.info("Tip: Try converting your Excel file to CSV format and upload again")
    st.stop()

        # Validate columns
        required_columns = ['GENCO/ERD', 'BENEFICIARIES', 'FUND', 'AMOUNT']
        missing_cols = [col for col in required_columns if col not in df.columns]

        if missing_cols:
            st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
            st.info(f"**Found columns:** {', '.join(df.columns.tolist())}")
            st.stop()

        # Store raw data
        st.session_state.df_raw = df.copy()

        # Apply region filter
        if 'region_filter' in st.session_state and st.session_state.region_filter != 'All Regions':
            df_filtered = df[df['REGION'] == st.session_state.region_filter].copy()
        else:
            df_filtered = df.copy()


        # Analysis function
        def analyze_data(df):
            # Clean data
            df_clean = df.dropna(subset=['GENCO/ERD', 'FUND', 'AMOUNT']).copy()
            df_clean['BENEFICIARIES'] = df_clean['BENEFICIARIES'].fillna('Unknown')
            df_clean['AMOUNT'] = pd.to_numeric(df_clean['AMOUNT'], errors='coerce').fillna(0)

            if len(df_clean) == 0:
                return None

            # Pivot table
            pivot = df_clean.pivot_table(
                index=['GENCO/ERD', 'BENEFICIARIES'],
                columns='FUND',
                values='AMOUNT',
                aggfunc='sum',
                fill_value=0
            )

            # Ensure columns exist
            target_cols = ['EF', 'DLF', 'RWMHEEF']
            for col in target_cols:
                if col not in pivot.columns:
                    pivot[col] = 0.0

            pivot = pivot[target_cols]

            # Create main df
            main_df = pivot.reset_index()

            # Calculate subtotals
            subtotals = main_df.groupby('GENCO/ERD')[target_cols].sum().reset_index()
            subtotals['BENEFICIARIES'] = 'TOTAL'

            # Combine
            main_df['sort_helper'] = 0
            subtotals['sort_helper'] = 1

            combined = pd.concat([main_df, subtotals], ignore_index=True)
            combined = combined.sort_values(['GENCO/ERD', 'sort_helper', 'BENEFICIARIES'])

            return combined.drop(columns='sort_helper')


        # Perform analysis
        df_result = analyze_data(df_filtered)

        if df_result is None or len(df_result) == 0:
            st.warning("⚠️ No valid data to analyze after filtering")
            st.stop()

        st.session_state.df_final = df_result

        # Calculate statistics
        data_rows = df_result[df_result['BENEFICIARIES'] != 'TOTAL']
        total_rows = len(data_rows)
        unique_gencos = data_rows['GENCO/ERD'].nunique()
        unique_beneficiaries = data_rows['BENEFICIARIES'].nunique()
        total_amount = data_rows[['EF', 'DLF', 'RWMHEEF']].sum().sum()

        # Display metrics
        st.markdown("### 📈 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="📄 Total Rows",
                value=f"{total_rows:,}"
            )

        with col2:
            st.metric(
                label="🏢 Unique Gencos",
                value=f"{unique_gencos:,}"
            )

        with col3:
            st.metric(
                label="👥 Beneficiaries",
                value=f"{unique_beneficiaries:,}"
            )

        with col4:
            st.metric(
                label="💰 Total Amount",
                value=f"₱{total_amount:,.2f}"
            )

        st.markdown("---")

        # Display data
        st.markdown("### 📋 Analysis Results")

        # Format display dataframe
        display_df = df_result.copy()
        display_df['EF'] = display_df['EF'].apply(lambda x: f"₱{x:,.2f}")
        display_df['DLF'] = display_df['DLF'].apply(lambda x: f"₱{x:,.2f}")
        display_df['RWMHEEF'] = display_df['RWMHEEF'].apply(lambda x: f"₱{x:,.2f}")


        # Highlight subtotals
        def highlight_subtotals(row):
            if row['BENEFICIARIES'] == 'TOTAL':
                return ['background-color: #dbeafe; font-weight: bold'] * len(row)
            return [''] * len(row)


        styled_df = display_df.style.apply(highlight_subtotals, axis=1)

        st.dataframe(
            styled_df,
            use_container_width=True,
            height=400
        )

        # Download section
        st.markdown("---")
        st.markdown("### 💾 Download Results")

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            # Excel download
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_result.to_excel(writer, sheet_name='Analysis', index=False)

            st.download_button(
                label="📥 Download Excel",
                data=buffer.getvalue(),
                file_name="fund_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col2:
            # CSV download
            csv = df_result.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="fund_analysis.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.success("✅ Analysis complete! You can download the results above.")

    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.info("Please check your file format and try again.")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #6b7280; padding: 1rem;'>
        <p>Fund Analyzer Pro | Built with Streamlit</p>
    </div>
""", unsafe_allow_html=True)

