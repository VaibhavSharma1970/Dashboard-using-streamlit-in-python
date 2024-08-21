import streamlit as st
import pandas as pd
import requests
import altair as alt
import json

FASTAPI_ENDPOINT = "http://localhost:8000"
TOKEN_STORAGE = "token.json"

# Helper function to load and save token
def save_token(token):
    with open(TOKEN_STORAGE, "w") as f:
        json.dump({"token": token}, f)

def load_token():
    try:
        with open(TOKEN_STORAGE, "r") as f:
            return json.load(f).get("token")
    except FileNotFoundError:
        return None

# Streamlit App UI
st.title("Interactive Data Dashboard")

token = load_token()

if token:
    headers = {"Authorization": f"Bearer {token}"}
    st.sidebar.header("User Menu")
    if st.sidebar.button("Logout"):
        save_token(None)
        st.experimental_set_query_params(logout="true")
        st.write("You have been logged out. Please refresh the page.")

    # Upload file section
    uploaded_file = st.file_uploader("Upload a file", type=["csv", "json", "xlsx", "parquet"])

    if uploaded_file is not None:
        file_type = uploaded_file.name.split(".")[-1]
        files = {"file": (uploaded_file.name, uploaded_file, f"text/{file_type}")}
        response = requests.post(f"{FASTAPI_ENDPOINT}/upload/", files=files, headers=headers)

        if response.status_code == 200:
            file_id = response.json().get("file_id")
            st.success("File uploaded successfully!")

            # Fetch data by file_id
            data_response = requests.get(f"{FASTAPI_ENDPOINT}/data/{file_id}", headers=headers)

            if data_response.status_code == 200:
                data = data_response.json().get("data")
                df = pd.DataFrame(data)

                # Display dataframe
                st.write(df)

                # Create graphs
                st.header("Graphs")

                # Select chart type
                chart_type = st.selectbox("Select Chart Type", ["Line", "Bar", "Area", "Scatter", "Histogram"])

                if df.empty:
                    st.error("Data is empty. Please upload a valid file.")
                else:
                    # Select columns for X and Y axes
                    columns = df.columns.tolist()
                    x_axis = st.selectbox("Select X-axis", options=columns)
                    y_axis = st.selectbox("Select Y-axis", options=columns)

                    if chart_type == "Line":
                        chart = alt.Chart(df).mark_line().encode(
                            x=alt.X(x_axis, title=x_axis),
                            y=alt.Y(y_axis, title=y_axis)
                        )
                    elif chart_type == "Bar":
                        chart = alt.Chart(df).mark_bar().encode(
                            x=alt.X(x_axis, title=x_axis),
                            y=alt.Y(y_axis, title=y_axis)
                        )
                    elif chart_type == "Area":
                        chart = alt.Chart(df).mark_area().encode(
                            x=alt.X(x_axis, title=x_axis),
                            y=alt.Y(y_axis, title=y_axis)
                        )
                    elif chart_type == "Scatter":
                        chart = alt.Chart(df).mark_point().encode(
                            x=alt.X(x_axis, title=x_axis),
                            y=alt.Y(y_axis, title=y_axis)
                        )
                    elif chart_type == "Histogram":
                        chart = alt.Chart(df).mark_bar().encode(
                            alt.X(x_axis, bin=True, title=x_axis),
                            y=alt.Y('count():Q', title='Count')
                        )
                    
                    st.altair_chart(chart, use_container_width=True)
        else:
            st.error("Failed to upload file")

else:
    st.sidebar.header("Authentication")
    choice = st.sidebar.selectbox("Select an option", ["Sign In", "Sign Up"])

    if choice == "Sign Up":
        st.subheader("Create a new account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Sign Up"):
            response = requests.post(f"{FASTAPI_ENDPOINT}/signup/", json={"username": username, "password": password})
            if response.status_code == 200:
                st.success("Account created successfully!")
            else:
                st.error("Failed to create account")

    elif choice == "Sign In":
        st.subheader("Sign In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Sign In"):
            response = requests.post(f"{FASTAPI_ENDPOINT}/token/", data={"username": username, "password": password})
            if response.status_code == 200:
                token = response.json().get("access_token")
                save_token(token)
                st.write("Signed in successfully! Please refresh the page to access the dashboard.")
            else:
                st.error("Invalid username or password")
