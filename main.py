import os
import csv
import streamlit as st
from tempfile import NamedTemporaryFile

from models.modules import Modules
from helpers.utils import get_trace
from config import STATIC_TOKEN as TOKEN


st.set_page_config(
    page_title="AutoRFP",
    page_icon="fft-logo.jpg",
    layout="wide",
)

st.title("AutoRFP")

def check_token(token: str):
    return token == TOKEN

token_input = st.text_input("Enter Token to use the App", type="password", key="token_input")
is_valid_token = check_token(token_input)

# Only proceed if login is successful
if is_valid_token:
    st.markdown("Upload a PDF, DOCX, XLSX, WAV, or MP3 file to analyze tasks, categories, and estimated hours. Or you can provide a previously generated YAML or JSON file.")

    # File upload
    uploaded_file = st.file_uploader("Upload a file", type=["pdf", "docx", "xlsx", "mp3", "wav", "yaml", "json"])

    # Caching the modules generation
    @st.cache_data
    def generate_modules(file_path, file_extension):
        if file_extension == ".pdf":
            return Modules.from_pdf(file_path)
        elif file_extension == ".docx":
            return Modules.from_docx(file_path)
        elif file_extension == ".xlsx":
            return Modules.from_excel(file_path)
        elif file_extension == ".mp3":
            return Modules.from_mp3(file_path)
        elif file_extension == ".wav":
            return Modules.from_wav(file_path)
        elif file_extension in [".yml", ".yaml", ".json"]:
            return Modules.from_file(file_path)
        else:
            raise ValueError("Unsupported file format!")

    # Display results upon file upload
    if uploaded_file:
        try:
            with NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
                temp_file.write(uploaded_file.read())
                temp_path = temp_file.name

            # Determine the file extension
            file_extension = f".{uploaded_file.name.split('.')[-1]}"

            # Generate modules using the cached function
            modules = generate_modules(temp_path, file_extension)
            json_data = modules.to_json()
            yaml_data = modules.to_yaml()

            # Convert to DataFrame
            df = modules.to_df(title_cased=True)
            pivot_df = modules.to_df(pivot_by_categories=True, title_cased=True)

            col1, col2, col3, col4 = st.columns(4, vertical_alignment="center")

            # Show the total hours for the entire project
            col1.metric(label="Total Estimated Hours", value=df['Hours'].sum(), delta=None)

            # Let the user download in either JSON or YAML format
            col2.download_button(
                label="Download as JSON",
                data=json_data,
                file_name=f"{modules.slug}.json",
                mime="application/json",
                key="download_json",
            )
            col3.download_button(
                label="Download as YAML",
                data=yaml_data,
                file_name=f"{modules.slug}.yaml",
                mime="text/yaml",
                key="download_yaml",
            )
            col4.download_button(
                label="Download as CSV",
                data=df.to_csv(index=False, quoting=csv.QUOTE_NONNUMERIC),
                file_name=f"{modules.slug}.csv",
                mime="text/csv",
                key="download_csv",
            )

            # Display the main DataFrame
            with st.expander("Detailed Task Breakdown", expanded=True):
                st.dataframe(df)

            # Display the pivoted DataFrame
            with st.expander("Pivoted Task View by Categories", expanded=True):
                st.dataframe(pivot_df)

            # Calculate and display aggregated totals by selected columns
            grouping_columns = [
                "Module", 
                "Task", 
                "Category", 
            ]
            selected_columns = st.multiselect(
                "Select columns to group by",
                options=grouping_columns,
                default=["Category"],
            )

            columns = st.columns(len(selected_columns))
            for i, column in enumerate(columns):
                with column:
                    total_hours = df.groupby(selected_columns[i])["Hours"].sum()
                    column.subheader(f"Total Hours by {selected_columns[i]}")
                    column.bar_chart(total_hours)

        except Exception as e:
            st.error(f"An error occurred: {e}")
            print(get_trace(e))
        finally:
            try:
                # Ensure the temporary file is deleted
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
else:
    st.info("Please login to access the app.")
