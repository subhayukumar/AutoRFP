import os
import json
from pathlib import Path

from openai_wrapper import get_chatgpt_response
from docx_reader import read_docx
from pdf_reader import read_pdf
from md2pdfdoc import convert_markdown_to_pdf_and_csv, convert_markdown_to_pdf_and_word

OUTPUT_DIR = Path("Generated_Proposal")



EXPERIENCE_MULTIPLIERS = {
    "beginner": 1.5,
    "intermediate": 1.0,
    "expert": 0.8
}

def sanitize_csv(csv: str, separator: str = ";"): 
    """
    Sanitizes a CSV string by replacing any non-integer values with json.dumps representations
    and replacing the separator with a comma.
    """
    return "\n".join(
        ",".join(
            value if value.isdigit() else json.dumps(value) 
            for value in line.split(separator)
        ) 
        for line in csv.split("\n")
    )


def generate_project_plan_from_sow(file_path: str, experience_level: str):
    # Read the SOW based on file extension
    sow = read_docx(file_path) if file_path.endswith('.docx') else read_pdf(file_path)

    # Extract the base name of the input file (without extension)
    base_name = Path(file_path).stem

    # Ensure experience level is valid
    if experience_level not in EXPERIENCE_MULTIPLIERS:
        raise ValueError("Invalid experience level. Must be one of: beginner, intermediate, expert.")

    multiplier = EXPERIENCE_MULTIPLIERS[experience_level]

    prompt = f"""
    You are a project manager. Based on the requirements outlined in the State of Work (SOW) provided below, create a detailed MVP (Minimum Viable Product) project plan in CSV format. The plan must include **all tasks** mentioned in the SOW without reducing or omitting any tasks. Your goal is to adjust the time estimates precisely based on the experience levels.

    ### Instructions:
    1. **Reference**: Use the **State of Work (SOW)** provided below as the primary input for generating the project plan.
    2. **Expertise Levels**:
        - Frontend Developer Expertise: {experience_level}.
        - Backend Developer Expertise: {experience_level}.
        - AI Engineer Expertise: {experience_level} (only for tasks involving AI).
        - Adjust time estimates **precisely** based on the expertise level:
            - **Beginner**: 1.5x the standard time estimate.
            - **Intermediate**: Use the standard time estimates (industry best practices).
            - **Expert**: 0.8x the standard time estimate.
    3. **Estimation Guidelines**:
        - Break down the tasks into **backend**, **frontend**, and **AI development** efforts for each subtask where applicable (e.g., database schema creation, API development, UI/UX design, AI model integration).
        - Provide **precise time estimates** for each subtask, factoring in the dependencies and task complexity based on the **experience level** and applying the multiplier ({multiplier}).
        - **Ensure no task is skipped** in the final list, and all tasks from the SOW must be included and considered once.
        - **Classifying Frontend Tasks**:
            - Any task related to UI/UX design, layout, user interactions, or any frontend framework integration should be classified under the "Frontend" category. Ensure all frontend tasks are properly estimated and included.
            - Even small tasks like UI mockups, button designs, or page layouts must be classified as "Frontend."
        - **Handling Backend and Frontend Task Dependencies**:
            - If there is a backend task that involves **user interaction**, **API integration**, **data fetching**, or **data display**, assume there is a **corresponding frontend task**. 
            - For example, if the backend task is about integrating an API to retrieve restaurant data, assume that the frontend will need to display that data in a user interface (e.g., a restaurant listing page, booking system UI).
            - For every backend API integration or service setup task, a corresponding frontend task should be inferred to display the results of those services to the user (e.g., creating forms, buttons, layouts).
    4. **CSV Format**:
        - Provide the output in CSV format using a semicolon (;) as a delimiter, ensuring it can be directly saved as a .csv file.
        - Ensure proper alignment of all values with the columns listed below.
        - Use quotes around fields if they contain special characters or line breaks.
    5. **CSV Columns**:
        - **S.No**: Sequential task number for tracking.
        - **Module Name**: Name of the primary functionality or module.
        - **Subtask Detail**: A granular breakdown of each subtask.
        - **Description**: A detailed explanation of the feature or task.
        - **Estimated Effort (Backend)**: Time in days required for backend development (5-day working week).
        - **Estimated Effort (Frontend)**: Time in days required for frontend development (5-day working week).
        - **Estimated Effort (AI)**: Time in days required for AI-related tasks (if applicable).
    6. **Task Granularity**:
        - Break down modules into technical subtasks where applicable, such as:
            - Database schema creation
            - API development
            - UI/UX design
            - AI model integration or training (if applicable)
            - Testing and debugging
    7. **Feature Prioritization**:
        - Include **all features** listed in the SOW and prioritize critical functionalities for the MVP in the plan.
    8. **Total Days Calculation**:
        - After providing all the individual task estimates, **accurately calculate the total days required for each category**: Backend, Frontend, and AI Engineer.
        - **Sum all the days** for backend tasks and display the total backend days in the last row under the "Estimated Effort (Backend)" column.
        - **Sum all the days** for frontend tasks and display the total frontend days in the last row under the "Estimated Effort (Frontend)" column.
        - **Sum all the days** for AI Engineer tasks and display the total AI Engineer days in the last row under the "Estimated Effort (AI Engineer)" column.
        - Ensure the totals accurately reflect the individual task estimates, adjusted by the experience level multiplier.
    9. **Handling Missing Classifications**:
        - If there are any tasks from the SOW that are unclear in classification or don't fit neatly into one of the categories, **infer** the appropriate classification (either Backend, Frontend, or AI Engineering) based on the task description.
        - Ensure that **no task is skipped** or omitted, even if it requires logical inference to place it into the correct category.

    10. **Sample Output**:
        S.No;Module Name;Subtask Detail;Description;Estimated Effort (Backend);Estimated Effort (Frontend);Estimated Effort (AI Engineer);
        1;Account Creation;Splash screens and social login integration;Enables users to create an account with splash screens and social logins;3;4;0;
        2;User Verification;OTP verification for users;Verifies users via OTP;2;2;0;
        3;Dashboard;Analytics chart integration;Displays user activity insights using interactive charts;5;4;0;
        4;Recommendations;AI-based recommendation engine setup;Suggests personalized content for users based on AI model;4;3;5;
        5;Notifications;Push notification system setup;Enables users to receive real-time notifications;5;3;0;
        Total; ; ; ;19;16;5;

    ### **State of Work (SOW)**:
    {sow}

    ### Expectations:
    - **Include all tasks** from the SOW with detailed breakdowns.
    - **Precise time estimates** based on the experience level of backend, frontend, and AI engineers.
    - **Ensure no tasks are repeated**.
    - **All tasks should be clearly described**, with no tasks reduced or omitted from the final breakdown.
    - **If AI work is required**, ensure that AI-related tasks are estimated separately under the "AI Engineer" column and clearly classified in the "Description" column.

    ### Notes:
    - Assume the development team is familiar with modern frameworks (e.g., React for frontend, Node.js for backend, and TensorFlow/PyTorch for AI).
    - Align subtasks with standard industry development workflows (e.g., API CRUD operations, form validations, AI model training).
    - Each subtask should be estimated based on the **actual complexity** of the task, with adjustments for **experience level** made accordingly.
    
    **VERY IMPORTANT**: **ONLY RESPOND WITH THE CSV FORMATTED OUTPUT.**
"""

    # Generate the response using the prompt
    generated_rfp_sections = get_chatgpt_response(prompt)
    print("generated_rfp_sections:", generated_rfp_sections)

    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save markdown output
    markdown_file_path = OUTPUT_DIR / f"{base_name}_generated_rfp.md"
    with open(markdown_file_path, "w") as f:
        f.write(generated_rfp_sections)

    # Generate unique file names for PDF, Word, and CSV
    pdf_file_path = OUTPUT_DIR / f"{base_name}_output.pdf"
    word_file_path = OUTPUT_DIR / f"{base_name}_new_output.docx"
    excel_file_path = OUTPUT_DIR / f"{base_name}_MVP.csv"

    # Convert markdown to PDF, Word, and CSV
    convert_markdown_to_pdf_and_csv(markdown_file_path, excel_file_path)
    convert_markdown_to_pdf_and_word(markdown_file_path, pdf_file_path, word_file_path)

    return generated_rfp_sections
