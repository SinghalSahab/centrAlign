import logging
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import httpx

logger = logging.getLogger("agent.browser")

class HTMLSnapshotParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.title = ""
        self.in_title = False
        
        self.links: List[Dict[str, str]] = [] # {id, text, href}
        self.in_a = False
        self.current_a: Dict[str, str] = {}
        self.current_a_text: List[str] = []
        
        self.forms: List[Dict[str, Any]] = [] # {id, action, method, fields: [{name, type, value, options}]}
        self.current_form: Optional[Dict[str, Any]] = None
        
        self.current_select: Optional[Dict[str, Any]] = None
        self.current_option: Optional[Dict[str, Any]] = None
        
        self.alerts: List[str] = []
        self.in_alert = False
        self.current_alert_text: List[str] = []
        
        self.text_parts: List[str] = []
        self.skip_tags = {"script", "style", "svg", "path"}
        self.current_skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        
        if tag.lower() in self.skip_tags:
            self.current_skip_depth += 1
            return

        if self.current_skip_depth > 0:
            return

        classes = attr_dict.get("class", "").split()
        tag_id = attr_dict.get("id", "")
        if "flash-error" in classes or "flash-success" in classes or tag_id.startswith("flash-"):
            self.in_alert = True
            self.current_alert_text = []

        if tag.lower() == "title":
            self.in_title = True

        elif tag.lower() == "a":
            href = attr_dict.get("href", "")
            if href:
                full_href = urljoin(self.base_url, href)
                self.in_a = True
                self.current_a = {
                    "id": f"L{len(self.links) + 1}",
                    "href": full_href,
                    "rel_href": href,
                    "id_attr": attr_dict.get("id", "")
                }
                self.current_a_text = []

        elif tag.lower() == "form":
            action = attr_dict.get("action", "")
            full_action = urljoin(self.base_url, action)
            method = attr_dict.get("method", "GET").upper()
            form_id = f"F{len(self.forms) + 1}"
            self.current_form = {
                "id": form_id,
                "id_attr": attr_dict.get("id", ""),
                "action": full_action,
                "rel_action": action,
                "method": method,
                "fields": []
            }
            self.forms.append(self.current_form)

        elif tag.lower() == "input" and self.current_form:
            name = attr_dict.get("name")
            if name:
                self.current_form["fields"].append({
                    "name": name,
                    "type": attr_dict.get("type", "text"),
                    "value": attr_dict.get("value", ""),
                    "placeholder": attr_dict.get("placeholder", "")
                })

        elif tag.lower() == "textarea" and self.current_form:
            name = attr_dict.get("name")
            if name:
                self.current_form["fields"].append({
                    "name": name,
                    "type": "textarea",
                    "value": attr_dict.get("value", ""),
                    "placeholder": attr_dict.get("placeholder", "")
                })

        elif tag.lower() == "select" and self.current_form:
            name = attr_dict.get("name")
            if name:
                self.current_select = {
                    "name": name,
                    "type": "select",
                    "options": [],
                    "value": None
                }
                self.current_form["fields"].append(self.current_select)

        elif tag.lower() == "option" and self.current_select:
            is_selected = "selected" in attr_dict
            self.current_option = {
                "value": attr_dict.get("value", ""),
                "selected": is_selected,
                "text": []
            }

    def handle_endtag(self, tag: str):
        if tag.lower() in self.skip_tags:
            self.current_skip_depth = max(0, self.current_skip_depth - 1)
            return

        if self.current_skip_depth > 0:
            return

        if self.in_alert and tag.lower() in ["div", "p", "span"]:
            text = " ".join(self.current_alert_text).strip()
            if text:
                self.alerts.append(text)
            self.in_alert = False

        if tag.lower() == "title":
            self.in_title = False

        elif tag.lower() == "a" and self.in_a:
            text = " ".join(self.current_a_text).strip()
            self.current_a["text"] = text or self.current_a["rel_href"]
            self.links.append(self.current_a)
            self.in_a = False

        elif tag.lower() == "form":
            self.current_form = None

        elif tag.lower() == "select":
            self.current_select = None

        elif tag.lower() == "option" and self.current_select and self.current_option:
            opt_text = " ".join(self.current_option["text"]).strip()
            self.current_option["label"] = opt_text or self.current_option["value"]
            if self.current_option["selected"]:
                self.current_select["value"] = self.current_option["value"]
            self.current_select["options"].append(self.current_option)
            self.current_option = None

    def handle_data(self, data: str):
        if self.current_skip_depth > 0:
            return

        clean = data.strip()
        if not clean:
            return

        if self.in_title:
            self.title += data + " "
        if self.in_alert:
            self.current_alert_text.append(clean)
        if self.in_a:
            self.current_a_text.append(clean)
        if self.current_option:
            self.current_option["text"].append(clean)

        self.text_parts.append(clean)

class CompactSnapshot:
    def __init__(self, url: str, status_code: int, title: str, text: str, links: List[Dict[str, str]], forms: List[Dict[str, Any]], alerts: List[str]):
        self.url = url
        self.status_code = status_code
        self.title = title.strip()
        self.text = text
        self.links = links
        self.forms = forms
        self.alerts = alerts

    def to_compact_string(self) -> str:
        lines = [
            f"PAGE TITLE: {self.title}",
            f"URL: {self.url}",
            f"STATUS: {self.status_code}"
        ]

        if self.alerts:
            lines.append("\n[FLASH ALERTS / MESSAGES]")
            for a in self.alerts:
                lines.append(f"! {a}")

        # Trim main text to 1500 chars to respect free-tier Gemini token limits
        trimmed_text = self.text
        if len(trimmed_text) > 1500:
            trimmed_text = trimmed_text[:1500] + "... [trimmed for brevity]"

        lines.append(f"\nPAGE CONTENT:\n{trimmed_text}")

        if self.links:
            lines.append("\nAVAILABLE LINKS:")
            for l in self.links:
                lines.append(f"- [{l['id']}] \"{l['text']}\" -> {l['rel_href']}")

        if self.forms:
            lines.append("\nAVAILABLE FORMS:")
            for f in self.forms:
                field_strs = []
                for fld in f["fields"]:
                    if fld["type"] == "select":
                        opts = [f"{o['value']}{' (selected)' if o.get('selected') else ''}" for o in fld.get("options", [])]
                        field_strs.append(f"{fld['name']} [select: {', '.join(opts)}]")
                    else:
                        cur = f"='{fld['value']}'" if fld.get("value") else ""
                        field_strs.append(f"{fld['name']} [{fld['type']}{cur}]")
                lines.append(f"- [{f['id']}] {f['method']} {f['rel_action']} (inputs: {', '.join(field_strs)})")

        return "\n".join(lines)

class HTTPBrowser:
    """HTTP Browser with cookie session persistence and compact snapshot generation."""
    def __init__(self, base_url: str = "http://localhost:8000", run_id: Optional[str] = None, app_instance: Optional[Any] = None):
        self.base_url = base_url.rstrip("/")
        self.run_id = run_id
        headers = {"X-Run-Id": run_id} if run_id else {}
        
        # Support in-memory ASGI client or network client
        if app_instance is not None:
            self.client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app_instance),
                base_url=self.base_url,
                headers=headers,
                follow_redirects=True,
                timeout=30.0
            )
        else:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                follow_redirects=True,
                timeout=30.0
            )

        self.current_snapshot: Optional[CompactSnapshot] = None
        self.current_url: str = ""

    async def close(self):
        await self.client.aclose()

    def _parse_response(self, response: httpx.Response, url: str) -> CompactSnapshot:
        parser = HTMLSnapshotParser(base_url=str(response.url))
        parser.feed(response.text)
        
        # Clean text
        raw_text = "\n".join(parser.text_parts)
        cleaned_text = re.sub(r"\n\s*\n", "\n", raw_text).strip()
        
        snapshot = CompactSnapshot(
            url=str(response.url),
            status_code=response.status_code,
            title=parser.title,
            text=cleaned_text,
            links=parser.links,
            forms=parser.forms,
            alerts=parser.alerts
        )
        self.current_snapshot = snapshot
        self.current_url = str(response.url)
        return snapshot

    async def open(self, path_or_url: str) -> str:
        """Open a URL and return a compact text snapshot."""
        logger.info(f"Browser open: {path_or_url}")
        resp = await self.client.get(path_or_url)
        snap = self._parse_response(resp, path_or_url)
        return snap.to_compact_string()

    async def read(self) -> str:
        """Re-read current page."""
        if not self.current_url:
            return "No page currently loaded. Use web_open first."
        resp = await self.client.get(self.current_url)
        snap = self._parse_response(resp, self.current_url)
        return snap.to_compact_string()

    async def click(self, link_id: str) -> str:
        """Click a link by its compact ID (e.g. L1, L2)."""
        if not self.current_snapshot:
            return "Error: No page loaded to click link."
        
        target = next((l for l in self.current_snapshot.links if l["id"].upper() == link_id.upper()), None)
        if not target:
            available = [f"{l['id']} ({l['text']})" for l in self.current_snapshot.links]
            return f"Error: Link '{link_id}' not found. Available links: {', '.join(available)}"

        resp = await self.client.get(target["href"])
        snap = self._parse_response(resp, target["href"])
        return snap.to_compact_string()

    async def submit(self, form_id: str, fields: Dict[str, Any]) -> str:
        """Submit a form by ID (e.g. F1) with specified field dictionary."""
        if not self.current_snapshot:
            return "Error: No page loaded to submit form."

        target_form = next((f for f in self.current_snapshot.forms if f["id"].upper() == form_id.upper()), None)
        if not target_form:
            available = [f["id"] for f in self.current_snapshot.forms]
            return f"Error: Form '{form_id}' not found. Available forms: {', '.join(available)}"

        action = target_form["action"]
        method = target_form["method"]

        logger.info(f"Submitting form {form_id} ({method} {action}) with data: {fields}")

        if method == "POST":
            resp = await self.client.post(action, data=fields)
        else:
            resp = await self.client.get(action, params=fields)

        snap = self._parse_response(resp, action)
        return snap.to_compact_string()
