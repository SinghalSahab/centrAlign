import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from app.agent.browser import HTTPBrowser
from app.agent.memory import MemoryManager
from app.knowledge.search import search_knowledge

logger = logging.getLogger("agent.tools")

# Demo Credentials Vault
DEMO_VAULT = {
    "ats": {
        "username": "recruiter_admin",
        "password": "ats_secret_2026",
        "login_url": "/sandbox/ats/login"
    },
    "calendar": {
        "username": "calendar_admin",
        "password": "cal_secret_2026",
        "login_url": "/sandbox/calendar/login"
    }
}

TOOL_DEFINITIONS = [
    {
        "name": "web_open",
        "description": "Open a web URL or relative path inside the company sandbox apps and return a compact text snapshot with numbered links and forms.",
        "type": "read",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {"type": "STRING", "description": "The URL or path to open, e.g. /sandbox/ats/login or /sandbox/ats/"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "web_click",
        "description": "Click a numbered link from the current page snapshot by its ID (e.g. L1, L2).",
        "type": "read",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "link_id": {"type": "STRING", "description": "The short ID of the link to follow (e.g. 'L1', 'L2')"}
            },
            "required": ["link_id"]
        }
    },
    {
        "name": "web_submit",
        "description": "Submit a form from the current page snapshot by its form ID (e.g. F1) with specified form field inputs.",
        "type": "write",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "form_id": {"type": "STRING", "description": "The form ID to submit (e.g. 'F1')"},
                "fields": {"type": "OBJECT", "description": "Key-value dictionary of form input names and their values"}
            },
            "required": ["form_id", "fields"]
        }
    },
    {
        "name": "web_read",
        "description": "Re-read the current page snapshot to check for dynamic updates or fresh alerts.",
        "type": "read",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_credentials",
        "description": "Retrieve login credentials from the company vault for a specific application ('ats' or 'calendar').",
        "type": "read",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app": {"type": "STRING", "description": "Target app name ('ats' or 'calendar')"}
            },
            "required": ["app"]
        }
    },
    {
        "name": "knowledge_search",
        "description": "Search company policy documents, hiring rubrics, and scheduling rules using full-text search.",
        "type": "read",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search terms, e.g. 'hiring rubric', 'notice period policy', 'scheduling rules'"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "memory_write",
        "description": "Save critical facts, scores, decisions, or shortlist reasons into company memory for this run.",
        "type": "read",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Key name, e.g. 'shortlisted_candidates', 'rubric_scores'"},
                "value": {"type": "STRING", "description": "JSON string or text value to remember"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "memory_read",
        "description": "Retrieve previously recorded facts from company memory.",
        "type": "read",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Key to read from memory"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "ask_user",
        "description": "Escalate to a human supervisor for clarification when faced with ambiguity (e.g. multiple matching jobs).",
        "type": "human",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question": {"type": "STRING", "description": "Clarification question for the user"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "request_approval",
        "description": "Request human manager approval before executing a sensitive write operation.",
        "type": "human",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Description of the action requiring approval"},
                "details": {"type": "STRING", "description": "Context and rationale for the request"}
            },
            "required": ["action", "details"]
        }
    },
    {
        "name": "message_candidate",
        "description": "Send a direct message to a candidate to verify interest, notice period, and expected CTC.",
        "type": "write",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "applicant_id": {"type": "INTEGER", "description": "Applicant database ID"},
                "text": {"type": "STRING", "description": "Message text to candidate"}
            },
            "required": ["applicant_id", "text"]
        }
    },
    {
        "name": "wait_for_reply",
        "description": "Wait for a candidate reply on messaging channel.",
        "type": "human",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "applicant_id": {"type": "INTEGER", "description": "Applicant database ID"},
                "timeout_s": {"type": "INTEGER", "description": "Max seconds to wait"}
            },
            "required": ["applicant_id"]
        }
    },
    {
        "name": "finish",
        "description": "Conclude the task with an honest status, concise executive summary, and typed claims for the independent ground-truth verifier.",
        "type": "terminal",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "status": {"type": "STRING", "description": "One of: 'completed', 'failed', 'needs_user'"},
                "summary": {"type": "STRING", "description": "Concise summary of actions taken and final state"},
                "claims": {
                    "type": "ARRAY",
                    "description": "List of typed claims to be verified against the database",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "type": {"type": "STRING", "description": "Claim type (e.g. shortlist_valid, interview_booked, stage_is, policy_respected, count_applicants)"},
                            "details": {"type": "OBJECT", "description": "Key-value details of the claim"}
                        },
                        "required": ["type"]
                    }
                }
            },
            "required": ["status", "summary", "claims"]
        }
    }
]

class ToolExecutor:
    """Executes tools in the context of a run, managing browser, memory, and credentials."""

    def __init__(self, run_id: str, browser: HTTPBrowser, memory: MemoryManager, messenger: Optional[Any] = None):
        self.run_id = run_id
        self.browser = browser
        self.memory = memory
        self.messenger = messenger

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        logger.info(f"Executing tool: {tool_name} with args: {args}")

        if tool_name == "web_open":
            return await self.browser.open(args["url"])

        elif tool_name == "web_click":
            return await self.browser.click(args["link_id"])

        elif tool_name == "web_submit":
            return await self.browser.submit(args["form_id"], args.get("fields", {}))

        elif tool_name == "web_read":
            return await self.browser.read()

        elif tool_name == "get_credentials":
            app = args["app"].lower()
            if app in DEMO_VAULT:
                return DEMO_VAULT[app]
            return f"Error: No credentials found for app '{app}' in vault."

        elif tool_name == "knowledge_search":
            docs = await search_knowledge(args["query"])
            if not docs:
                return "No matching policy documents found."
            results = []
            for d in docs:
                results.append(f"DOCUMENT #{d['id']}: {d['title']}\n{d['body']}")
            return "\n\n---\n\n".join(results)

        elif tool_name == "memory_write":
            return await self.memory.write(args["key"], args["value"])

        elif tool_name == "memory_read":
            val = await self.memory.read(args["key"])
            return val if val is not None else "Key not found in memory."

        elif tool_name == "ask_user":
            return f"[ESCALATED TO USER] Question: {args['question']}"

        elif tool_name == "request_approval":
            return f"[APPROVAL REQUESTED] Action: {args['action']} | Details: {args['details']}"

        elif tool_name == "message_candidate":
            applicant_id = args["applicant_id"]
            text = args["text"]
            if self.messenger:
                msg_id = await self.messenger.send(f"applicant_{applicant_id}", text)
                return f"Message sent to candidate #{applicant_id} (msg_id: {msg_id})."
            return f"[MOCK MESSENGER] Message dispatched to candidate #{applicant_id}: {text}"

        elif tool_name == "wait_for_reply":
            applicant_id = args["applicant_id"]
            if self.messenger:
                reply = await self.messenger.wait_for_reply(applicant_id, timeout_s=args.get("timeout_s", 30))
                if reply:
                    return f"Candidate #{applicant_id} replied: \"{reply}\""
                return f"Timeout: Candidate #{applicant_id} did not reply."
            return f"[MOCK MESSENGER] Candidate #{applicant_id} replied: 'Yes, interested! Notice period is 30 days and expected CTC is 22 LPA.'"

        elif tool_name == "finish":
            return {
                "finished": True,
                "status": args.get("status", "completed"),
                "summary": args.get("summary", ""),
                "claims": args.get("claims", [])
            }

        else:
            return f"Error: Unknown tool '{tool_name}'."
