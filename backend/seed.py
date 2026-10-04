import asyncio
import json
import logging
from app.db import init_db, close_db, execute, fetch_all, is_postgres

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

JOBS = [
    {
        "id": 1,
        "title": "Senior Backend Engineer (Python/FastAPI)",
        "jd_text": (
            "We are looking for a Senior Backend Engineer to lead our core microservices platform.\n"
            "Requirements:\n"
            "- 3+ years of production experience in Python and FastAPI or Django.\n"
            "- Deep understanding of PostgreSQL (query optimization, indexing, transactions) and Redis.\n"
            "- Experience building scalable async APIs, distributed task workers, and clean service architectures.\n"
            "- Strong system design, automated testing, and observability practices."
        ),
        "status": "active",
        "expected_shortlist_ids": [1, 2] # Aarav Sharma and Neha Patel
    },
    {
        "id": 2,
        "title": "Backend Engineer (Distributed Systems)",
        "jd_text": (
            "We are seeking a Backend Engineer focused on distributed storage and consensus protocols.\n"
            "Requirements:\n"
            "- 2+ years experience in distributed systems, Go or Rust.\n"
            "- Experience with Kafka, Raft consensus, and Kubernetes infrastructure."
        ),
        "status": "active",
        "expected_shortlist_ids": [9, 10]
    },
    {
        "id": 3,
        "title": "Data Analyst / Analytics Engineer",
        "jd_text": (
            "Seeking an Analyst to extract product insights and maintain data pipelines.\n"
            "Requirements:\n"
            "- Strong SQL and Python (pandas, numpy) proficiency.\n"
            "- 2+ years analyzing user behavior, creating KPI dashboards, and tracking conversion funnels."
        ),
        "status": "active",
        "expected_shortlist_ids": [12, 13]
    }
]

APPLICANTS = [
    # Applicants for Job 1: Senior Backend Engineer
    {
        "id": 1,
        "job_id": 1,
        "name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
        "phone": "+91-9811122334",
        "resume_text": (
            "Aarav Sharma - Senior Software Engineer\n"
            "Experience: 4.2 years\n"
            "Current: Razorpay (Senior Backend Engineer, 2 years)\n"
            "- Architected high-throughput payment settlement microservice using FastAPI and PostgreSQL handling 5k req/sec.\n"
            "- Optimized slow SQL queries, reducing p99 response times by 40% via composite indexing and query rewrites.\n"
            "- Built Redis distributed locking mechanism to prevent race conditions during bulk payouts.\n"
            "Previous: Swiggy (Software Engineer, 2.2 years)\n"
            "- Developed order delivery tracking APIs using Python, Celery, and PostgreSQL.\n"
            "Skills: Python, FastAPI, PostgreSQL, Redis, Docker, System Design, Unit Testing."
        ),
        "stage": "Applied"
    },
    {
        "id": 2,
        "job_id": 1,
        "name": "Neha Patel",
        "email": "neha.patel@example.com",
        "phone": "+91-9822233445",
        "resume_text": (
            "Neha Patel - Backend Developer\n"
            "Experience: 3.5 years\n"
            "Current: Zepto (Backend SDE-2, 1.8 years)\n"
            "- Built inventory reconciliation engine in FastAPI with AsyncIO, processing 2M SKU events daily.\n"
            "- Managed Postgres database schemas, read replicas, and connection pooling with PgBouncer.\n"
            "- Authored comprehensive test suites (pytest) maintaining 90%+ code coverage on critical billing services.\n"
            "Previous: CarDekho (Software Engineer, 1.7 years)\n"
            "- Built REST APIs using Django and Postgres for dealer management portals.\n"
            "Skills: Python, FastAPI, AsyncIO, PostgreSQL, Redis, Pytest, Docker, CI/CD."
        ),
        "stage": "Applied"
    },
    {
        "id": 3,
        "job_id": 1,
        "name": "Rohan Verma",
        "email": "rohan.verma@example.com",
        "phone": "+91-9833344556",
        "resume_text": (
            "Rohan Verma - Lead Python Developer\n"
            "Experience: 5.5 years\n"
            "Current: Infosys (Technical Specialist, 3 years)\n"
            "- Led a 5-person team building enterprise backend services using FastAPI and Postgres.\n"
            "- Integrated OAuth2 and role-based access control for banking client apps.\n"
            "Notice Period: 90 days (standard corporate policy).\n"
            "Skills: Python, FastAPI, PostgreSQL, Jenkins, AWS, Enterprise Architecture."
        ),
        "stage": "Applied"
    },
    {
        "id": 4,
        "job_id": 1,
        "name": "Vikram Malhotra",
        "email": "vikram.malhotra@example.com",
        "phone": "+91-9844455667",
        "resume_text": (
            "Vikram Malhotra - Full Stack & AI Specialist\n"
            "Experience: 1.1 years\n"
            "Skills: Python, FastAPI, Django, Flask, PostgreSQL, MySQL, MongoDB, Redis, Kafka, Kubernetes, "
            "Docker, AWS, GCP, Azure, React, Next.js, Web3, Blockchain, PyTorch, LangChain, CI/CD, Microservices.\n"
            "Projects:\n"
            "- College capstone project: Todo app with AI suggestions.\n"
            "- Personal website hosted on Vercel with Python backend.\n"
            "Looking for high growth opportunities."
        ),
        "stage": "Applied"
    },
    {
        "id": 5,
        "job_id": 1,
        "name": "Pooja Sundaram",
        "email": "pooja.sundaram@example.com",
        "phone": "+91-9855566778",
        "resume_text": (
            "Pooja Sundaram - Senior Software Engineer\n"
            "Experience: 4 years\n"
            "Current: Freshworks (Backend Engineer, 2.5 years)\n"
            "- Scaled ticketing backend using FastAPI and Postgres; optimized query response from 120ms to 25ms.\n"
            "Skills: Python, FastAPI, PostgreSQL, Redis, Kafka, Microservices."
        ),
        "stage": "Applied"
    },
    {
        "id": 6,
        "job_id": 1,
        "name": "Ananya Iyer",
        "email": "ananya.iyer@example.com",
        "phone": "+91-9866677889",
        "resume_text": (
            "Ananya Iyer - Junior Python Engineer\n"
            "Experience: 1.4 years\n"
            "Worked on simple Flask scripts and Django admin pages. Looking to transition into FastAPI."
        ),
        "stage": "Applied"
    },
    {
        "id": 7,
        "job_id": 1,
        "name": "Karthik Reddy",
        "email": "karthik.reddy@example.com",
        "phone": "+91-9877788990",
        "resume_text": (
            "Karthik Reddy - Frontend Engineer\n"
            "Experience: 3 years\n"
            "React, CSS, Tailwind, basic Node.js Express. Limited backend experience in Python."
        ),
        "stage": "Applied"
    },
    {
        "id": 8,
        "job_id": 1,
        "name": "Siddharth Nair",
        "email": "siddharth.nair@example.com",
        "phone": "+91-9888899001",
        "resume_text": (
            "Siddharth Nair - Python Developer\n"
            "Experience: 2.2 years\n"
            "Built internal reporting tools using Django and PostgreSQL. Good foundations, developing system design skills."
        ),
        "stage": "Applied"
    },

    # Job 2 Applicants
    {
        "id": 9,
        "job_id": 2,
        "name": "Meera Krishnan",
        "email": "meera.krishnan@example.com",
        "phone": "+91-9899900112",
        "resume_text": "Meera Krishnan - 4 years experience in Go, Raft consensus, distributed key-value stores.",
        "stage": "Applied"
    },
    {
        "id": 10,
        "job_id": 2,
        "name": "Aditya Joshi",
        "email": "aditya.joshi@example.com",
        "phone": "+91-9800011223",
        "resume_text": "Aditya Joshi - 3.5 years experience in C++ and Go, Kafka pipeline scaling and Kubernetes.",
        "stage": "Applied"
    },
    {
        "id": 11,
        "job_id": 2,
        "name": "Tanvi Deshmukh",
        "email": "tanvi.deshmukh@example.com",
        "phone": "+91-9812345678",
        "resume_text": "Tanvi Deshmukh - 2.8 years experience in stream processing with Flink and Kafka.",
        "stage": "Applied"
    },

    # Job 3 Applicants (Data Analyst)
    {
        "id": 12,
        "job_id": 3,
        "name": "Rajesh Gupta",
        "email": "rajesh.gupta@example.com",
        "phone": "+91-9823456789",
        "resume_text": (
            "Rajesh Gupta - Senior Data Analyst\n"
            "Experience: 3.5 years\n"
            "Advanced SQL queries, window functions, Python (pandas, matplotlib, numpy) analysis, Tableau dashboards."
        ),
        "stage": "Applied"
    },
    {
        "id": 13,
        "job_id": 3,
        "name": "Sneha Nair",
        "email": "sneha.nair@example.com",
        "phone": "+91-9834567890",
        "resume_text": (
            "Sneha Nair - Analytics Engineer\n"
            "Experience: 4 years\n"
            "Python data modeling, dbt, PostgreSQL analytics, conversion funnel metrics, cohort retention."
        ),
        "stage": "Applied"
    },
    {
        "id": 14,
        "job_id": 3,
        "name": "Kunal Shah",
        "email": "kunal.shah@example.com",
        "phone": "+91-9845678901",
        "resume_text": (
            "Kunal Shah - Junior Analyst\n"
            "Experience: 1.5 years\n"
            "Excel, basic SQL queries, weekly reporting."
        ),
        "stage": "Applied"
    },
    {
        "id": 15,
        "job_id": 3,
        "name": "Divya Pillai",
        "email": "divya.pillai@example.com",
        "phone": "+91-9856789012",
        "resume_text": (
            "Divya Pillai - Business Intelligence Analyst\n"
            "Experience: 3 years\n"
            "PowerBI, SQL, Python for exploratory data analysis."
        ),
        "stage": "Applied"
    }
]

INTERVIEWERS = [
    {"id": 1, "name": "Siddharth Roy", "email": "siddharth.roy@company.internal", "role": "Lead Architect"},
    {"id": 2, "name": "Priya Menon", "email": "priya.menon@company.internal", "role": "Engineering Manager"},
    {"id": 3, "name": "Amitabh Banerjee", "email": "amitabh.b@company.internal", "role": "VP Engineering"}
]

# 45-minute slots on upcoming weekdays (Monday to Wednesday, 10:00 AM - 5:00 PM IST)
SLOTS = [
    {"id": 1, "interviewer_id": 1, "start_ts": "2026-10-12T10:00:00+05:30"},
    {"id": 2, "interviewer_id": 1, "start_ts": "2026-10-12T11:00:00+05:30"},
    {"id": 3, "interviewer_id": 1, "start_ts": "2026-10-12T14:00:00+05:30"},
    {"id": 4, "interviewer_id": 2, "start_ts": "2026-10-13T10:30:00+05:30"},
    {"id": 5, "interviewer_id": 2, "start_ts": "2026-10-13T15:00:00+05:30"},
    {"id": 6, "interviewer_id": 3, "start_ts": "2026-10-14T11:00:00+05:30"},
    {"id": 7, "interviewer_id": 3, "start_ts": "2026-10-14T16:00:00+05:30"}
]

KNOWLEDGE_DOCS = [
    {
        "id": 1,
        "title": "Engineering Hiring Rubric & Scoring Guide",
        "body": (
            "CentrAlign Engineering Hiring Rubric:\n"
            "1. Technical Skills & Architecture (40% weight): Core proficiency in required framework (FastAPI/Python), "
            "PostgreSQL query optimization, caching (Redis), API design, and asynchronous programming. "
            "Penalize superficial keyword stuffing without concrete architectural ownership.\n"
            "2. Production Experience & Impact (30% weight): Minimum 3+ years of hands-on production engineering required for Senior roles. "
            "Look for evidence of measurable impact (e.g. latency reduction, scale handled, throughput numbers).\n"
            "3. Code Quality, Reliability & Testing (20% weight): Automated testing suites (pytest), error handling, CI/CD, "
            "monitoring, and clean code principles.\n"
            "4. Communication & Clarity (10% weight): Clear resume narrative, well-explained project contributions.\n"
            "Decision Rule: A candidate must score at least 80/100 across these criteria to be shortlisted. Shortlist the top 2 qualifying candidates per requisition."
        )
    },
    {
        "id": 2,
        "title": "Candidate Notice Period & Compensation Policy",
        "body": (
            "CentrAlign Talent Acquisition Policy:\n"
            "1. Maximum Notice Period Rule: The maximum acceptable notice period for any hire is 60 calendar days. "
            "Candidates with a notice period exceeding 60 days (e.g., 90 days standard corporate notice) CANNOT be scheduled for an interview "
            "under any circumstances without prior executive waiver. Update their ATS status to 'Rejected' with note 'Notice period exceeds 60-day company maximum policy'.\n"
            "2. Expected CTC Policy: The approved budget band for Senior Backend Engineer is up to 28 LPA. "
            "Expected CTC must be recorded as a valid numeric figure in Lakhs Per Annum (LPA)."
        )
    },
    {
        "id": 3,
        "title": "Interview Scheduling Rules & Guidelines",
        "body": (
            "CentrAlign Scheduling Protocol:\n"
            "1. Slot Duration: All technical screening interviews must be exactly 45 minutes long.\n"
            "2. Days: Interviews must be conducted strictly on weekdays (Monday through Friday), between 10:00 AM and 6:00 PM IST.\n"
            "3. Prerequisites: A candidate MUST be in the 'Intent Confirmed' stage before booking any calendar slot.\n"
            "4. Conflict Prohibition: Slots must be currently unbooked (free). Double booking an interviewer or scheduling two candidates in the same slot is strictly forbidden.\n"
            "5. Post-Booking: Immediately upon successful calendar booking, the candidate's stage in the ATS must be updated to 'Interview Scheduled'."
        )
    }
]

async def seed_all():
    logger.info("Starting database seed...")
    await init_db()

    # Clear existing sandbox data only (preserve platform runs, steps, eval_results)
    tables = ["interviews", "slots", "interviewers", "applicants", "jobs", "knowledge_docs"]
    for t in tables:
        try:
            await execute(f"DELETE FROM {t}")
        except Exception:
            pass


    # Seed Jobs
    for j in JOBS:
        if is_postgres():
            await execute(
                "INSERT INTO jobs (id, title, jd_text, status, expected_shortlist_ids) VALUES (%s, %s, %s, %s, %s)",
                (j["id"], j["title"], j["jd_text"], j["status"], j["expected_shortlist_ids"])
            )
        else:
            await execute(
                "INSERT INTO jobs (id, title, jd_text, status, expected_shortlist_ids) VALUES (%s, %s, %s, %s, %s)",
                (j["id"], j["title"], j["jd_text"], j["status"], json.dumps(j["expected_shortlist_ids"]))
            )

    # Seed Applicants
    for a in APPLICANTS:
        await execute(
            "INSERT INTO applicants (id, job_id, name, email, phone, resume_text, stage) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (a["id"], a["job_id"], a["name"], a["email"], a["phone"], a["resume_text"], a["stage"])
        )

    # Seed Interviewers
    for i in INTERVIEWERS:
        await execute(
            "INSERT INTO interviewers (id, name, email, role) VALUES (%s, %s, %s, %s)",
            (i["id"], i["name"], i["email"], i["role"])
        )

    # Seed Slots
    for s in SLOTS:
        await execute(
            "INSERT INTO slots (id, interviewer_id, start_ts, booked_applicant_id) VALUES (%s, %s, %s, NULL)",
            (s["id"], s["interviewer_id"], s["start_ts"])
        )

    # Seed Knowledge Docs
    for d in KNOWLEDGE_DOCS:
        await execute(
            "INSERT INTO knowledge_docs (id, title, body) VALUES (%s, %s, %s)",
            (d["id"], d["title"], d["body"])
        )

    logger.info("Seed completed successfully!")
    await close_db()

if __name__ == "__main__":
    asyncio.run(seed_all())
