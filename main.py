# Imports
from fastapi import Header, HTTPException
import pyodbc
import pandas as pd
from openai import OpenAI
import json
from fastapi import FastAPI


from pydantic import BaseModel


#AUTHORIZATION
API_KEY = ""
def verify_key(x_api_key: str = Header(...)):    # Header(...)→ This tells FastAPI:“Get this value from the HTTP request headers”
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")


# FastAPI app
app = FastAPI()

# Database connection
conn = pyodbc.connect(
    "DRIVER="
    "SERVER=;"
    "DATABASE="
    "UID="
    "PWD="
    "TrustServerCertificate=yes;"
)

# OpenAI client
client = OpenAI(api_key="")

# Load data once at startup
df = pd.read_sql("SELECT * FROM tbl_rootcausecontrol", conn)


top_level_R= df[(df['Tag']=='R') & (df['Parent_ID']==0)]
top_level_I= df[(df['Tag']=='I') & (df['Parent_ID']==0)]


#FIRST FUNCTION
def get_suggestions(description: str, vessel_id: int = None):
    
    # Step 1 - Get I children
    I_children = df[(df['Tag'] == 'I') & (df['Parent_ID'] != 0)]

    if vessel_id:
        query2 = f"SELECT TOP 10 * FROM tbl_rca_feedback WHERE Vessel_Id = {vessel_id} ORDER BY Id DESC"
        df2 = pd.read_sql(query2, conn)
        if len(df2) < 5:
            query2 = "SELECT TOP 10 * FROM tbl_rca_feedback ORDER BY Id DESC"
            df2 = pd.read_sql(query2, conn)
    else:
        query2 = "SELECT TOP 10 * FROM tbl_rca_feedback ORDER BY Id DESC"
        df2 = pd.read_sql(query2, conn)
    # Step 2 - Build prompt
    prompt = f"""You are a maritime specialist doing Root Cause Analysis.
    Given the Incident description below, pick the TOP 3 most relevant Immediate root causes FROM THE LIST BELOW ONLY.
    Return ONLY a JSON list of 3 I Child Ids like this: [ n1, n2, n3 ], with the most relevant Id at the starting and then lesser relevant and then least.
    Only select Id 8 if the incident is specifically and directly about procedure violation. Do not use it as a generic fallback.
    No explanation. No text. Just give the JSON list of Ids.
    No markdown. No code blocks. No explanation.

    List of available I Child Ids to choose from:
    """
    for _, row in I_children.iterrows():
        prompt += f"I Child Id {row['Id']}: {row['Immediate_Root_Controls']}\n"
   
 
    if len(df2) > 0:
        prompt += f"\nHere are some past verified incidents with Correct I Child Ids for your reference:\n"
        for _, row in df2.iterrows():
            prompt += f"Incident: {row['Description']} → Correct I Child Id: {row['I_Child_Id']}\n"


    prompt += f"""
    Now classify this new incident:
    Incident: {description}
    """

    # Step 3 - Call GPT
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a maritime root cause analysis specialist."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )

    # Step 4 - Parse response
    result = response.choices[0].message.content
    result = result.strip().removeprefix("```json").removesuffix("```").strip()
    ids = json.loads(result)

    # Step 5 - Get matched I children and parents
    matched = I_children[I_children['Id'].isin(ids)]
    parent_ids = matched['Parent_ID'].tolist()
    matched_parents = top_level_I[top_level_I['Id'].isin(parent_ids)]

    # Step 6 - Merge
    paired = matched.merge(
        matched_parents[['Id', 'Immediate_Root_Controls', 'Usual_Root_Causes']], 
        left_on='Parent_ID', 
        right_on='Id',
        suffixes=('_child', '_parent')
    )
    
    # Step 7 - Build suggestions list and return it
    suggestions = []
    for i, row in enumerate(paired.itertuples(), 1):
        usual_r = row.Usual_Root_Causes_parent
        r_ids = [int(x) for x in usual_r.split(',') if x.strip()]
        matched_r_parents = top_level_R[top_level_R['Id'].isin(r_ids)]
        
        suggestions.append({
            "suggestion_number": i,
            "i_parent_id": int(row.Id_parent),
            "i_parent_name": row.Immediate_Root_Controls_parent,
            "i_child_id": int(row.Id_child),
            "i_child_name": row.Immediate_Root_Controls_child,
            "root_causes": matched_r_parents['Immediate_Root_Controls'].tolist()
        })
    
    return suggestions




def save_feedback(description: str, i_parent_id: int, i_child_id: int, vessel_id: int, company_id: int, user_id: int):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tbl_rca_feedback 
        (Description, I_Parent_Id, I_Child_Id, Vessel_Id, Company_Id, User_Id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, description, i_parent_id, i_child_id, vessel_id, company_id, user_id)
    conn.commit()
    return {"message": "Feedback saved successfully!"}



class DescriptionInput(BaseModel):
    description: str
    vessel_id: int = None

class FeedbackInput(BaseModel):
    description: str
    i_parent_id: int
    i_child_id: int
    vessel_id: int
    company_id: int
    user_id: int


@app.post("/suggestions")
def suggestions_endpoint(data: DescriptionInput, x_api_key: str = Header(...)):
    verify_key(x_api_key)
    return get_suggestions(data.description, data.vessel_id)

 
@app.post("/feedback")
def feedback_endpoint(data: FeedbackInput, x_api_key: str = Header(...)):
    verify_key(x_api_key)
    return save_feedback(
        data.description,
        data.i_parent_id,
        data.i_child_id,
        data.vessel_id,
        data.company_id,
        data.user_id
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) 

 

