# Maritime Root Cause Analysis (RCA) System

A domain-specific **RAG (Retrieval Augmented Generation)** system that helps maritime investigators identify root causes of incidents using AI. Built with FastAPI and GPT-4o.

---

## What It Does

Given a description of a maritime incident, the system:
1. Suggests the **top 3 most relevant Immediate Causes (I)** from a structured database
2. Maps each I cause to its **Root Causes (R)** using pre-defined relationships
3. Learns from **human feedback** to improve suggestions over time

---

## How It Works

```
User describes incident
        ↓
GPT-4o matches against I children (using few-shot examples from feedback)
        ↓
Top 3 I children selected → mapped to their I parents
        ↓
Each I parent linked to Root Causes (R) via database
        ↓
3 complete suggestions returned
        ↓
User picks correct suggestion → stored as feedback
        ↓
Feedback used to improve future suggestions (few-shot prompting)
```

---

## Tech Stack

- **Python** — core language
- **FastAPI** — REST API framework
- **GPT-4o** — AI model for intelligent matching
- **SQL Server** — database for RCA tree structure and feedback
- **pandas** — data manipulation
- **uvicorn** — ASGI server

---

## Project Structure

```
├── main.py          # FastAPI application with endpoints
├── ssms2.py         # Old CLI version with feedback collection
├── requirements.txt
└── README.md        
```

---

## API Endpoints

### `POST /suggestions`
Returns top 3 root cause suggestions for a given incident description.

**Request:**
```json
{
  "description": "Engine room caught fire due to fuel oil leak",
  "vessel_id": 1
}
```

**Response:**
```json
[
  {
    "suggestion_number": 1,
    "i_parent_id": 14,
    "i_parent_name": "Machinery and Equipments (Unsafe Act)",
    "i_child_id": 19,
    "i_child_name": "Issues related to servicing of the Machinery/equipment",
    "root_causes": [
      "Maintenance / Inspection inadequacies",
      "Extensive Wear/Tear",
      "Incorrect tool/equipment/machinery/device"
    ]
  }
]
```

---

### `POST /feedback`
Saves the correct suggestion chosen by the investigator.

**Request:**
```json
{
  "description": "Engine room caught fire due to fuel oil leak",
  "i_parent_id": 14,
  "i_child_id": 19,
  "vessel_id": 1,
  "company_id": 1,
  "user_id": 1
}
```

**Response:**
```json
{
  "message": "Feedback saved successfully!"
}
```

---

## Authentication

All endpoints are protected with an API key. Include it in every request header:

```
X-API-Key: your-secret-key-here
```

Requests without a valid key will receive a `403 Forbidden` response.

---

## Database Structure

The system uses three hierarchical trees stored in one table:

| Tag | Description |
|-----|-------------|
| `I` | Immediate Causes — what directly caused the incident |
| `R` | Root Causes — why it happened |
| `C` | Controls — what should have prevented it |

Each I parent is linked to relevant R causes via a `Usual_Root_Causes` column containing comma-separated R IDs.

---

## Few-Shot Learning

The system improves over time using verified feedback:
- Vessel-specific feedback is prioritized (if available)
- Falls back to overall latest feedback if vessel has fewer than 5 records
- Up to 10 past verified incidents are sent to GPT as examples with each request

---

## Setup

### 1. Install dependencies
```bash
pip install fastapi uvicorn openai pandas pyodbc
```
OR 
```bash
pip install -r requirements.txt
```

### 2. Configure environment
Update the following in `main.py`:
- Database connection string
- OpenAI API key
- API key for authentication

### 3. Run the server
```bash
python main.py
```

### 4. Access Swagger UI
```
http://localhost:8000/docs
```

---

## Key Learnings & Design Decisions

- **GPT over embeddings** — short database labels made semantic similarity ineffective; GPT's world knowledge bridges the gap
- **SQL over vector DB** — structured hierarchical data is better served by SQL queries than vector search
- **Few-shot prompting over fine-tuning** — with ~500 records per year, few-shot is more practical than fine-tuning
- **Vessel-specific feedback first** — incidents on the same vessel are more likely to be similar

---

## Future Improvements

- Fine-tune GPT once 1000+ feedback records are collected
- Add C (Controls) suggestions
- Build frontend UI
- Deploy to production server
