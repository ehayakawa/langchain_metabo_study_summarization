import os
import json

from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.text_splitter import CharacterTextSplitter

import logging
import sys

# Load environment variables from .env file (if you're using one)
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Set the API key
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI model
your_chosen_llm = ChatOpenAI(model_name="gpt-3.5-turbo")



# function to read text file of study description (abstracts)
def read_abstracts(file_path):
    l_study_description = []
    current_id = None
    current_abstract = []

    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith('>'):
                if current_id is not None:
                    l_study_description.append((current_id, ' '.join(current_abstract).strip()))
                    current_abstract = []
                current_id = line.strip()[1:]  # Remove '>' from the ID
            else:
                current_abstract.append(line.strip())

    # Add the last abstract
    if current_id is not None:
        l_study_description.append((current_id, ' '.join(current_abstract).strip()))

    return l_study_description




# Function to load TSV file
import csv
from io import StringIO

def read_tab_delimited(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    if not lines:
        return ""

    # Split the header and identify columns to keep
    header = lines[0].strip().split('\t')
    columns_to_keep = [i for i, col in enumerate(header) if 'http' not in col.lower()]
    
    # Filter the header
    filtered_header = [header[i] for i in columns_to_keep]
    
    # Filter the rows, handling cases where a row might have fewer columns
    filtered_lines = []
    for line in lines[1:]:
        split_line = line.strip().split('\t')
        filtered_line = []
        for i in columns_to_keep:
            if i < len(split_line):
                filtered_line.append(split_line[i])
            else:
                filtered_line.append('')  # Add an empty string if the column is missing
        filtered_lines.append('\t'.join(filtered_line))
    
    # Combine the filtered header and rows
    filtered_content = '\t'.join(filtered_header) + '\n' + '\n'.join(filtered_lines)
    
    return filtered_content

# The rest of your code remains the same

# 

# Now 'abstracts' is a list of tuples, where each tuple contains (study_id, abstract_text)
l_my_study_description = read_abstracts('abstracts.txt')



## Define prompt templates, outside the loop
summary_prompt = PromptTemplate(
    input_variables=["abstract"],
    template="Summarize the following research abstract in up to 2 lines, up to 30 words: {abstract}"
)

extract_prompt = PromptTemplate(
    input_variables=["abstract"],
    template="Extract the background, experimental methods, results, and hypothesis from the following abstract. Annotate Gene Ontology together with GO ID: {abstract}"
)

# Create a prompt template for table summarization
table_summary_prompt = PromptTemplate(
    input_variables=["table_content"],
    template="""Analyze the following table content:

{table_content}

Provide a brief summary of the table structure and key information contained 
within it. Summrize experimental groups and its member sample names.
Then make list of sample groups together with their sample names, add dictionary-formatted text.
"""
)

analysis_prompt = PromptTemplate(
    input_variables=["abstract", "table_summary"],
    template="""Analyze the following research abstract and table summary:

Abstract: {abstract}

Table Summary: {table_summary}

Provide a comprehensive analysis of the research, incorporating insights from both the abstract and the table summary."""
)




# Iterate through study descriptions in l_my_study_description
structured_results = []
for study_id, abstract_text in l_my_study_description:
    print(study_id)

    # find correspondint tsv file in "samples" folder   
    sample_table_file_path = os.path.join("samples", f"s_{study_id}.txt")
    table_content = read_tab_delimited(sample_table_file_path)



    # Create new LLM chains for each iteration
    summary_chain = LLMChain(llm=ChatOpenAI(model_name="gpt-3.5-turbo"), prompt=summary_prompt)
    extract_chain = LLMChain(llm=ChatOpenAI(model_name="gpt-3.5-turbo"), prompt=extract_prompt)

    table_summary_chain = LLMChain(llm=ChatOpenAI(model_name="gpt-3.5-turbo"), prompt=table_summary_prompt)
    analysis_chain = LLMChain(llm=ChatOpenAI(model_name="gpt-3.5-turbo"), prompt=analysis_prompt)


    try:
        # Generate summary
        logger.info(f"Generating summary for {study_id}")
        summary = summary_chain.run({"abstract": abstract_text})
        
        # Extract elements
        logger.info(f"Extracting elements for {study_id}")
        extracted_elements = extract_chain.run({"abstract": abstract_text})

        # Generate table summary
        logger.info(f"Generating table summary for {study_id}")
        table_summary = table_summary_chain.run({"table_content": table_content})

        # Generate main analysis
        logger.info(f"Generating analysis for {study_id}")
        analysis = analysis_chain.run({"abstract": abstract_text, "table_summary": table_content})
    except Exception as e:
        logger.error(f"Error processing {study_id}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {sys.exc_info()}")
        continue  # Skip to the next iteration
   
    
    # Append results to structured_results list
    structured_results.append({
        "research_id": study_id,
        "summary": summary,
        "extracted_elements": extracted_elements,
        "table_summary": table_summary,
        "analysis": analysis
    })

# Export structured results as a Markdown file
with open('structured_results.md', 'w', encoding='utf-8') as md_file:
    for result in structured_results:
        md_file.write(f"# Research ID: {result['research_id']}\n\n")
        md_file.write(f"## Summary\n{result['summary']}\n\n")
        md_file.write(f"## Extracted Elements\n{result['extracted_elements']}\n\n")
        md_file.write(f"## Table Summary\n{result['table_summary']}\n\n")
        md_file.write(f"## Analysis\n{result['analysis']}\n\n")
        md_file.write("---\n\n")








# 構造化されたデータをファイルに保存
with open('structured_results.json', 'w') as json_file:
    json.dump(structured_results, json_file, indent=4)