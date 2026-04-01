import pyodbc
import pandas as pd
#from torch import cosine_similarity

conn= pyodbc.connect(
        "DRIVER="
        "SERVER="
        "DATABASE=;"
        "UID="
        "PWD="
        "TrustServerCertificate=yes;"

)


query= "SELECT * FROM tbl_rootcausecontrol"
df=pd.read_sql(query,conn)
query2="select top 12 *from tbl_rca_feedback order by NEWID();"
df2=pd.read_sql(query2,conn)

#print(df.columns)

I_children= df[(df['Tag']=='I') & (df['Parent_ID']!=0)]
print(len(I_children))
#print("I_children dataframe sample:")
#print(I_children[['Id', 'Parent_ID', 'Immediate_Root_Controls']].sample(5))


df_I=df[df['Tag']=='I'] # Equivalent to select * where tag ='I'
df_R=df[df['Tag']=='R']
df_C=df[df['Tag']=='C']

# Make a list of all I children names 
children_names = []
# for _, row in I_children.iterrows():
#     children_names.append(row['Immediate_Root_Controls'])
#                         OR
children_names = I_children['Immediate_Root_Controls'].tolist()
#print(children_names[:5])



# #Creating embeddings and comparing description to I children names (not anymore): 
# #Encode children names
# from sentence_transformers import SentenceTransformer
# model = SentenceTransformer('all-MiniLM-L6-v2')
# children_embeddings = model.encode(children_names)
# print(children_embeddings.shape) # (number of children, 384)

#description = input("Enter detailed description of the problem: ")
# query_embedding = model.encode([description])

# from sklearn.metrics.pairwise import cosine_similarity as cos_sim

# scores = cos_sim(query_embedding, children_embeddings)
# print(scores.shape)

# top_n=3
# top_indices = scores[0].argsort()[-top_n:][::-1]
# print(top_indices)

# for rank, idx in enumerate(top_indices, 1):
#     print(f"Rank {rank}: {children_names[idx]}  (score: {scores[0][idx]:.4f})")


# we are comparing description to I child as it is more specific than I parent, and we will get the I parent from the I child selected by the model.
# Logic for I child
# prompt = f"""You are a maritime specialist doing Root Cause Analysis.
# Given the Incident description below, pick the TOP 3 most relevant Immediate root causes FROM THE LIST BELOW ONLY.
# Return ONLY a JSON list of 3 Ids like this: [ n1, n2, n3 ], with the most relevant Id at the starting and then lesser relevant and then least.
# Only select Id 8 if the incident is specifically 
# and directly about procedure violation. 
# Do not use it as a generic fallback.
# No explanation. No text. Just the JSON list if Ids.
# No markdown. No code blocks. No explanation.
# Incident: {description} 

# List:
# """

# for _, row in I_children.iterrows():
#     prompt += f"Id {row['Id']}: {row['Immediate_Root_Controls']}\n"
# # This creates a string like:
# #Id 101: Check valve failure



# #also send 10 random rows from new table in the prompt to give the model a better understanding of the data structure and content.
# #sql query to do so:
# query2="select top 10 *from tbl_rca_feedback order by NEWID();"
# df2=pd.read_sql(query2,conn)
# for _,row in df2.iterrows():
#     prompt += f" Description: {row['Description']}, I_Parent_Id: {row['I_Parent_Id']}, I_Child_Id: {row['I_Child_Id']}\n"


# description = input("Enter detailed description of the problem: ")
# prompt = f"""You are a maritime specialist doing Root Cause Analysis.
# Given the Incident description below, pick the TOP 3 most relevant Immediate root controls causes FROM THE LIST BELOW ONLY.
# Return ONLY a JSON list of 3 I Child Ids like this: [ n1, n2, n3 ], with the most relevant Id at the starting and then lesser relevant and then least.
# Only select Id 8 if the incident is specifically and directly about procedure violation. 
# Do not use it as a generic fallback.
# No explanation. No text. Just the JSON list of Ids.
# No markdown. No code blocks. No explanation.

# Here are some past verified incidents for reference:
# """
# for _, row in df2.iterrows():
#     prompt += f"Incident: {row['Description']} → Correct I Child Id: {row['I_Child_Id']}\n"


# prompt += f"""
# Now classify this new incident:
# Incident: {description}
# List of available I Child Ids to choose from:
# """
# for _, row in I_children.iterrows():
#     prompt += f"I Child Id {row['Id']}: {row['Immediate_Root_Controls']}\n"
# # # This creates a string like:
# # #Id 101: Check valve failure

# print(prompt)  # verify it looks correct before making API call

description = input("Enter detailed description of the problem: ")

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
# dataframe.iterrows() → pandas method to iterate row by row
# row → Python object (actually a pandas Series) Even if you rename it: It is still a pandas Series internally
 
prompt += f"\nHere are some past verified incidents with Correct I Child Ids for your reference:\n"
for _, row in df2.iterrows():
    prompt += f"Incident: {row['Description']} → Correct I Child Id: {row['I_Child_Id']}\n"


prompt += f"""
Now classify this new incident:
Incident: {description}
"""

#print(prompt) 


from openai import OpenAI
import json

client = OpenAI(api_key="")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a maritime root cause analysis specialist."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.5
)

# Extract the text response
result = response.choices[0].message.content
#print(result)

result = result.strip().removeprefix("```json").removesuffix("```").strip()
ids = json.loads(result)
#print(ids)
#print(type(ids))

# checking if the I chidren ids exist in the dataframe, if they do select them
matched = I_children[I_children['Id'].isin(ids)]
#print(matched[[ 'Id','Immediate_Root_Controls']])

# Get parent IDs from matched children
parent_ids = matched['Parent_ID'].tolist()
#print(parent_ids)

top_level_R= df[(df['Tag']=='R') & (df['Parent_ID']==0)]
top_level_I= df[(df['Tag']=='I') & (df['Parent_ID']==0)]
#checking if the I parent ids exist in the dataframe
matched_parents = top_level_I[top_level_I['Id'].isin(parent_ids)]#.drop_duplicates(subset='Id')
#print(matched_parents[['Id', 'Immediate_Root_Controls']])













#For each child row, find the parent row where child's `Parent_ID` equals parent's `Id` — and combine them into one row.
paired = matched.merge(
    matched_parents[['Id', 'Immediate_Root_Controls', 'Usual_Root_Causes']], 
    left_on='Parent_ID', 
    right_on='Id',
    suffixes=('_child', '_parent')
)

#print(paired.columns.tolist())
# print(paired.shape)
print(paired[['Immediate_Root_Controls_parent', 'Immediate_Root_Controls_child']])
# print(paired.columns.tolist())
for i, row in enumerate(paired.itertuples(), 1):
    print(f"Suggestion {i}: {row.Usual_Root_Causes_parent}")
    usual_r = row.Usual_Root_Causes_parent
    r_ids = [int(x) for x in usual_r.split(',') if x.strip()]
    #print(r_ids)
    matched_r_parents = top_level_R[top_level_R['Id'].isin(r_ids)] #From top_level_R fetch only rows whose Id is in our r_ids list
    print(matched_r_parents[['Id', 'Immediate_Root_Controls']])




#clean ouput till now 
print("\n")
print("=" * 60)
print(f"INCIDENT: {description}")
print("=" * 60)

for i, row in enumerate(paired.itertuples(), 1):
    
    usual_r = row.Usual_Root_Causes_parent
    r_ids = [int(x) for x in usual_r.split(',') if x.strip()]
    matched_r_parents = top_level_R[top_level_R['Id'].isin(r_ids)]

    print(f"\n{'='*20} SUGGESTION {i} {'='*20}")
    print(f"\nImmediate Cause:")
    print(f"   Parent : {row.Immediate_Root_Controls_parent}[{row.Id_parent}]")
    print(f"   Child  : {row.Immediate_Root_Controls_child}[{row.Id_child}]")
    print(f"\nRoot Causes:")
    for _, r_row in matched_r_parents.iterrows():
        print(f"   - {r_row['Immediate_Root_Controls']}")
    print("\n" + "-" * 60)



choice = int(input("\nWhich suggestion was correct? Enter 1, 2 or 3: "))
selected = paired.iloc[choice - 1]
print("Best_I_Parent_ID")
print(selected['Id_parent'])
print("Best_I_Child_Id")
print(selected['Id_child'])


cursor = conn.cursor()
cursor.execute("""
    INSERT INTO tbl_rca_feedback 
    (Description, I_Parent_Id, I_Child_Id)
    VALUES (?, ?, ?)
""", description, int(selected['Id_parent']), int(selected['Id_child']))
conn.commit()
print("Feedback saved successfully!")












#CLAUDE 30/03
# print(top_level_I[['Id', 'Immediate_Root_Controls', 'Usual_Root_Causes']].head(10).to_string())

# # Test with I parent Id = 1
# top_level_R = df[(df['Tag'] == 'R') & (df['Parent_ID'] == 0)]
# i_parent_row = top_level_I[top_level_I['Id'] == 1].iloc[0]
# usual_r = i_parent_row['Usual_Root_Causes']
# print(usual_r)
# print(type(usual_r))

# r_ids = [int(x) for x in usual_r.split(',') if x.strip()]
# print(r_ids)
 
# matched_r_parents = top_level_R[top_level_R['Id'].isin(r_ids)]
# print(matched_r_parents[['Id', 'Immediate_Root_Controls']])





#no need now
# # NEED TO FIX THIS , this is problematic
# top_level_R= df[(df['Tag']=='R') & (df['Parent_ID']==0)]
# top_level_C= df[(df['Tag']=='C') & (df['Parent_ID']==0)]



# print("=" * 60)
# print(f"INCIDENT: {description}")
# print("=" * 60)

# for i, row in enumerate(paired.itertuples(), 1):
    
#     # Build RC prompt for this specific I child
#     rc_prompt = f"""You are a maritime root cause analysis specialist.
# Given the incident and immediate cause below, select the ONE most relevant Root Cause parent and ONE most relevant Control parent.
# Return ONLY a JSON object like: {{"R": 73, "C": 199}}
# No explanation. No text. Just the JSON.

# Incident: {description}
# I Parent: {row.Immediate_Root_Controls_parent}
# I Child: {row.Immediate_Root_Controls_child}

# Root Cause Parents:
# """
#     for _, r_row in top_level_R.iterrows():
#         rc_prompt += f"Id {r_row['Id']}: {r_row['Immediate_Root_Controls']}\n"

#     rc_prompt += "\nControl Parents:\n"
#     for _, c_row in top_level_C.iterrows():
#         rc_prompt += f"Id {c_row['Id']}: {c_row['Immediate_Root_Controls']}\n"

#     # API call
#     rc_response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[
#             {"role": "system", "content": "You are a maritime root cause analysis specialist."},
#             {"role": "user", "content": rc_prompt}
#         ],
#         temperature=0.4
#     )

#     rc_result = rc_response.choices[0].message.content
#     rc_result = rc_result.strip().removeprefix("```json").removesuffix("```").strip()
#     rc_ids = json.loads(rc_result)
   
#     r_id = rc_ids['R']
#     c_id = rc_ids['C']

#     r_parent = top_level_R[top_level_R['Id'] == r_id]
#     r_children = df[(df['Tag'] == 'R') & (df['Parent_ID'] == r_id)]

#     c_parent = top_level_C[top_level_C['Id'] == c_id]
#     c_children = df[(df['Tag'] == 'C') & (df['Parent_ID'] == c_id)]


#     # Print suggestion
#     print(f"\n{'='*20} SUGGESTION {i} {'='*20}")
#     print(f"I Parent: {row.Immediate_Root_Controls_parent}")
#     print(f"I Child:  {row.Immediate_Root_Controls_child}")
#     print(f"\nR Parent: {r_parent['Immediate_Root_Controls'].values[0]}")
#     for child in r_children['Immediate_Root_Controls'].tolist():
#         print(f"   - {child}")
#     print(f"\nC Parent: {c_parent['Immediate_Root_Controls'].values[0]}")
#     for child in c_children['Immediate_Root_Controls'].tolist():
#         print(f"   - {child}")
#     print("-" * 60)

