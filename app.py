import streamlit as st
import boto3
import os
from io import StringIO
import openai
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document

# S3 Setup
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name="us-west-1"
)
bucket_name = "doc-summarizer-uploads"

# Streamlit file upload
def upload_file_to_s3(file):
    try:
        
        existing_files = [obj['Key'] for obj in s3_client.list_objects_v2(Bucket=bucket_name).get('Contents', [])]
        if file.name in existing_files:
            st.info(f"File '{file.name}' already exists in S3.")
            return file.name
    
        s3_client.upload_fileobj(file, bucket_name, file.name)
        st.success(f"File '{file.name}' uploaded successfully to S3!")
        return file.name
    except Exception as e:
        st.error(f"Failed to upload file: {e}")
        return None

st.title("Document Summarizer")
st.write("Upload your document below:")

def get_file_from_s3(file_name):
    try:
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_name)
        file_content = file_obj['Body'].read()
        return file_content
    except Exception as e:
        st.error(f"Error fetching the file from S3: {e}")
        return None

openai.api_key = os.getenv("OPENAI_API_KEY")

def summarize_text(text):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            # telling model to behave as a "helpful assistant" before summarizing
            messages=[
                {"role": "system", "content": "Behave like a helpful academic assistant"},
                {"role": "user", "content": f"Summarize this document in 4 concise sentences:\n\n{text}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating summary: {e}")
        return None

def extract_text_from_pdf(file_content):
    try:
        pdf_reader = PdfReader(BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error extracting PDF text: {e}")
        return None

def extract_text_from_docx(file_content):
    try:
        doc = Document(BytesIO(file_content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        st.error(f"Error extracting DOCX text: {e}")
        return None

uploaded_file = st.file_uploader("Choose a file", type=["txt", "pdf", "docx"])

if uploaded_file is not None:
    file_name = upload_file_to_s3(uploaded_file)
    
    if file_name:
        file_content = get_file_from_s3(file_name)
        if file_content:
            
            # Extract text based on file type
            if uploaded_file.type == "application/pdf":
                file_content = extract_text_from_pdf(file_content)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                file_content = extract_text_from_docx(file_content)
            else:
                 # Assuming text file for other cases
                file_content = file_content.decode("utf-8")
                
            # Summarize the document and display
            if file_content:
                summary = summarize_text(file_content)
                if summary:
                    st.subheader("Document Summary:")
                    st.write(summary)
                else:
                    st.error("Unable to generate a summary.")
            else:
                st.error("Failed to extract text from the document.")
        else:
            st.error("Failed to retrieve file content from S3.")
