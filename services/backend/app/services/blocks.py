"""
Block Registry — Defines all agent block types with their config schemas.

Each block definition includes id, name, description, icon, color,
config_schema (JSON Schema), input_ports, output_ports, and default_config.
"""

from __future__ import annotations

from typing import Any


# ─── Helper: base port definitions ───────────────────────────────────────────────

def _port(name: str, type_: str = "data", label: str | None = None) -> dict[str, str]:
    return {"name": name, "type": type_, "label": label or name}

INPUT_PORT_DEFAULT = _port("input", "data", "Input")
OUTPUT_PORT_DEFAULT = _port("output", "data", "Output")


# ─── Block Definition ────────────────────────────────────────────────────────────


class BlockDefinition:
    """Describes a single block type available in the agent builder palette."""

    def __init__(
        self,
        block_id: str,
        name: str,
        description: str,
        category: str,
        icon: str,
        color: str,
        config_schema: dict[str, Any],
        input_ports: list[dict[str, str]] | None = None,
        output_ports: list[dict[str, str]] | None = None,
        default_config: dict[str, Any] | None = None,
    ) -> None:
        self.id = block_id
        self.name = name
        self.description = description
        self.category = category  # "trigger" | "ai" | "action" | "logic" | "connector"
        self.icon = icon
        self.color = color
        self.config_schema = config_schema
        self.input_ports = input_ports or [INPUT_PORT_DEFAULT]
        self.output_ports = output_ports or [OUTPUT_PORT_DEFAULT]
        self.default_config = default_config or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "color": self.color,
            "config_schema": self.config_schema,
            "input_ports": self.input_ports,
            "output_ports": self.output_ports,
            "default_config": self.default_config,
        }


# ─── Block Registry (Singleton) ──────────────────────────────────────────────────


class BlockRegistry:
    """Singleton that holds all block type definitions."""

    _instance: BlockRegistry | None = None
    _blocks: dict[str, BlockDefinition] = {}
    _initialized: bool = False

    def __new__(cls) -> BlockRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._blocks = {}
            self._register_defaults()
            self._initialized = True

    def _register_defaults(self) -> None:
        """Register all built-in block definitions."""
        self._register_trigger_blocks()
        self._register_ai_blocks()
        self._register_action_blocks()
        self._register_logic_blocks()

    # ── Trigger Blocks ─────────────────────────────────────────────────────────

    def _register_trigger_blocks(self) -> None:
        self.register(BlockDefinition(
            block_id="trigger.schedule",
            name="Schedule",
            description="Run on a recurring schedule using cron syntax",
            category="trigger",
            icon="Clock",
            color="#22C55E",
            config_schema={
                "type": "object",
                "required": ["cron"],
                "properties": {
                    "cron": {
                        "type": "string",
                        "title": "Cron Expression",
                        "description": "Standard cron syntax (e.g., '0 9 * * 1-5' for weekdays at 9am)",
                        "default": "0 9 * * *",
                        "pattern": r"^(\S+\s+){4}\S+$",
                    },
                    "timezone": {
                        "type": "string",
                        "title": "Timezone",
                        "description": "IANA timezone (e.g., 'Africa/Lagos')",
                        "default": "UTC",
                    },
                    "label": {
                        "type": "string",
                        "title": "Label",
                        "description": "Human-readable description of this schedule",
                    },
                },
            },
            output_ports=[_port("triggered", "event", "Triggered")],
            default_config={"cron": "0 9 * * *", "timezone": "UTC"},
        ))

        self.register(BlockDefinition(
            block_id="trigger.webhook",
            name="Webhook",
            description="Receive HTTP POST requests to trigger this agent",
            category="trigger",
            icon="Webhook",
            color="#22C55E",
            config_schema={
                "type": "object",
                "required": [],
                "properties": {
                    "method": {
                        "type": "string",
                        "title": "HTTP Method",
                        "enum": ["POST", "GET", "PUT", "PATCH"],
                        "default": "POST",
                    },
                    "payload_schema": {
                        "type": "object",
                        "title": "Expected Payload Schema (JSON Schema)",
                        "description": "Optional validation schema for incoming webhook payloads",
                        "default": {},
                    },
                    "secret": {
                        "type": "string",
                        "title": "Verification Secret",
                        "description": "Optional HMAC secret to verify webhook authenticity",
                    },
                },
            },
            output_ports=[_port("payload", "data", "Payload")],
            default_config={"method": "POST"},
        ))

        self.register(BlockDefinition(
            block_id="trigger.email_received",
            name="Email Received",
            description="Trigger when a new email matching your filters arrives",
            category="trigger",
            icon="Mail",
            color="#22C55E",
            config_schema={
                "type": "object",
                "required": [],
                "properties": {
                    "from_filter": {
                        "type": "string",
                        "title": "From (sender filter)",
                        "description": "Email address or domain to filter (e.g., '@company.com')",
                    },
                    "subject_filter": {
                        "type": "string",
                        "title": "Subject Contains",
                        "description": "Only trigger if subject contains this text",
                    },
                    "has_attachments": {
                        "type": "boolean",
                        "title": "Has Attachments",
                        "default": False,
                    },
                    "folder": {
                        "type": "string",
                        "title": "Folder",
                        "description": "Email folder to watch (INBOX, SENT, etc.)",
                        "default": "INBOX",
                    },
                },
            },
            output_ports=[_port("email", "data", "Email Data")],
            default_config={"folder": "INBOX"},
        ))

        self.register(BlockDefinition(
            block_id="trigger.message_received",
            name="Message Received",
            description="Trigger when a message is received on a connected channel",
            category="trigger",
            icon="MessageSquare",
            color="#22C55E",
            config_schema={
                "type": "object",
                "required": ["channel"],
                "properties": {
                    "channel": {
                        "type": "string",
                        "title": "Channel",
                        "enum": ["whatsapp", "slack", "telegram", "discord", "any"],
                        "default": "any",
                    },
                    "keyword_filter": {
                        "type": "string",
                        "title": "Keyword Filter",
                        "description": "Only trigger if message contains this keyword",
                    },
                    "from_contact": {
                        "type": "string",
                        "title": "From Contact",
                        "description": "Only trigger from a specific contact ID or number",
                    },
                },
            },
            output_ports=[_port("message", "data", "Message")],
            default_config={"channel": "any"},
        ))

        self.register(BlockDefinition(
            block_id="trigger.file_changed",
            name="File Changed",
            description="Trigger when a file is created, modified, or deleted",
            category="trigger",
            icon="File",
            color="#22C55E",
            config_schema={
                "type": "object",
                "required": ["path", "event"],
                "properties": {
                    "path": {
                        "type": "string",
                        "title": "File Path or Pattern",
                        "description": "Path or glob pattern to watch (e.g., '/data/reports/*.csv')",
                    },
                    "event": {
                        "type": "string",
                        "title": "Event Type",
                        "enum": ["created", "modified", "deleted", "any"],
                        "default": "any",
                    },
                    "recursive": {
                        "type": "boolean",
                        "title": "Watch Subdirectories",
                        "default": False,
                    },
                },
            },
            output_ports=[_port("file_info", "data", "File Info")],
            default_config={"event": "any", "recursive": False},
        ))

        self.register(BlockDefinition(
            block_id="trigger.form_submitted",
            name="Form Submitted",
            description="Trigger when a web form is submitted",
            category="trigger",
            icon="ClipboardList",
            color="#22C55E",
            config_schema={
                "type": "object",
                "required": ["form_id"],
                "properties": {
                    "form_id": {
                        "type": "string",
                        "title": "Form ID",
                        "description": "Unique identifier for this form",
                    },
                    "fields": {
                        "type": "array",
                        "title": "Expected Fields",
                        "description": "List of field names expected in the form submission",
                        "items": {"type": "string"},
                    },
                    "require_all_fields": {
                        "type": "boolean",
                        "title": "Require All Fields",
                        "default": False,
                    },
                },
            },
            output_ports=[_port("submission", "data", "Form Submission Data")],
            default_config={"require_all_fields": False},
        ))

        self.register(BlockDefinition(
            block_id="trigger.event",
            name="Platform Event",
            description="Trigger on internal Anansi platform events",
            category="trigger",
            icon="Zap",
            color="#22C55E",
            config_schema={
                "type": "object",
                "required": ["event_type"],
                "properties": {
                    "event_type": {
                        "type": "string",
                        "title": "Event Type",
                        "enum": [
                            "agent.completed", "user.login", "integration.connected",
                            "integration.disconnected", "billing.updated", "payment.received",
                            "brain.node_created", "brain.link_created", "daily_note.generated",
                        ],
                        "default": "agent.completed",
                    },
                    "filter": {
                        "type": "object",
                        "title": "Event Data Filter",
                        "description": "Key-value pairs to match against event data",
                        "default": {},
                    },
                },
            },
            output_ports=[_port("event_data", "data", "Event Data")],
            default_config={"event_type": "agent.completed", "filter": {}},
        ))

    # ── AI Blocks ──────────────────────────────────────────────────────────────

    def _register_ai_blocks(self) -> None:
        self.register(BlockDefinition(
            block_id="ai.conversation",
            name="AI Conversation",
            description="Free-form conversation with an AI model using a system prompt",
            category="ai",
            icon="Brain",
            color="#8B5CF6",
            config_schema={
                "type": "object",
                "required": ["system_prompt"],
                "properties": {
                    "system_prompt": {
                        "type": "string",
                        "title": "System Prompt",
                        "description": "Instructions that define the AI's behavior and context",
                        "default": "You are a helpful assistant.",
                        "x-ui": {"widget": "textarea", "rows": 6},
                    },
                    "model": {
                        "type": "string",
                        "title": "AI Model",
                        "enum": ["claude-sonnet-4", "claude-haiku-3", "gpt-4o", "gpt-4o-mini", "llama3"],
                        "default": "claude-sonnet-4",
                    },
                    "temperature": {
                        "type": "number",
                        "title": "Temperature",
                        "minimum": 0,
                        "maximum": 2,
                        "default": 0.7,
                    },
                    "max_tokens": {
                        "type": "integer",
                        "title": "Max Tokens",
                        "minimum": 1,
                        "maximum": 128000,
                        "default": 4096,
                    },
                    "memory_context": {
                        "type": "boolean",
                        "title": "Include Memory Context",
                        "description": "Include relevant memories from the user's Second Brain",
                        "default": False,
                    },
                },
            },
            default_config={
                "system_prompt": "You are a helpful assistant.",
                "model": "claude-sonnet-4",
                "temperature": 0.7,
                "max_tokens": 4096,
                "memory_context": False,
            },
        ))

        self.register(BlockDefinition(
            block_id="ai.extract",
            name="AI Extract",
            description="Extract structured data from unstructured text using a prompt",
            category="ai",
            icon="FileSearch",
            color="#8B5CF6",
            config_schema={
                "type": "object",
                "required": ["prompt", "output_schema"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "title": "Extraction Prompt",
                        "description": "Describe what data to extract",
                        "x-ui": {"widget": "textarea", "rows": 4},
                    },
                    "output_schema": {
                        "type": "object",
                        "title": "Output Schema (JSON Schema)",
                        "description": "Define the structure of extracted data",
                        "default": {
                            "type": "object",
                            "properties": {"result": {"type": "string"}},
                        },
                    },
                    "model": {
                        "type": "string",
                        "title": "AI Model",
                        "enum": ["claude-haiku-3", "gpt-4o-mini", "claude-sonnet-4"],
                        "default": "claude-haiku-3",
                    },
                },
            },
            default_config={
                "prompt": "Extract the key information from the text.",
                "output_schema": {
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                },
                "model": "claude-haiku-3",
            },
        ))

        self.register(BlockDefinition(
            block_id="ai.classify",
            name="AI Classify",
            description="Classify input into one or more predefined categories",
            category="ai",
            icon="Tags",
            color="#8B5CF6",
            config_schema={
                "type": "object",
                "required": ["categories", "prompt"],
                "properties": {
                    "categories": {
                        "type": "array",
                        "title": "Categories",
                        "description": "List of categories to classify into",
                        "items": {
                            "type": "object",
                            "required": ["name", "description"],
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                            },
                        },
                        "default": [
                            {"name": "urgent", "description": "Requires immediate attention"},
                            {"name": "normal", "description": "Routine item"},
                            {"name": "low", "description": "Can be handled later"},
                        ],
                    },
                    "prompt": {
                        "type": "string",
                        "title": "Classification Prompt",
                        "description": "Additional context for classification",
                        "x-ui": {"widget": "textarea", "rows": 3},
                    },
                    "multi_label": {
                        "type": "boolean",
                        "title": "Allow Multiple Categories",
                        "default": False,
                    },
                    "model": {
                        "type": "string",
                        "title": "AI Model",
                        "enum": ["claude-haiku-3", "gpt-4o-mini"],
                        "default": "claude-haiku-3",
                    },
                },
            },
            default_config={
                "categories": [
                    {"name": "urgent", "description": "Requires immediate attention"},
                    {"name": "normal", "description": "Routine item"},
                    {"name": "low", "description": "Can be handled later"},
                ],
                "multi_label": False,
                "model": "claude-haiku-3",
            },
        ))

        self.register(BlockDefinition(
            block_id="ai.summarize",
            name="AI Summarize",
            description="Generate a concise summary of input text",
            category="ai",
            icon="FileText",
            color="#8B5CF6",
            config_schema={
                "type": "object",
                "required": [],
                "properties": {
                    "length": {
                        "type": "string",
                        "title": "Summary Length",
                        "enum": ["short", "medium", "long", "bullet_points"],
                        "default": "medium",
                    },
                    "style": {
                        "type": "string",
                        "title": "Style",
                        "enum": ["concise", "detailed", "executive", "simple"],
                        "default": "concise",
                    },
                    "focus": {
                        "type": "string",
                        "title": "Focus Area",
                        "description": "What to focus the summary on (e.g., 'key decisions, action items')",
                    },
                    "model": {
                        "type": "string",
                        "title": "AI Model",
                        "enum": ["claude-haiku-3", "claude-sonnet-4", "gpt-4o-mini"],
                        "default": "claude-haiku-3",
                    },
                },
            },
            default_config={
                "length": "medium",
                "style": "concise",
                "model": "claude-haiku-3",
            },
        ))

        self.register(BlockDefinition(
            block_id="ai.generate",
            name="AI Generate",
            description="Generate content (text, code, JSON) from a prompt",
            category="ai",
            icon="Sparkles",
            color="#8B5CF6",
            config_schema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "title": "Generation Prompt",
                        "description": "Describe what to generate",
                        "x-ui": {"widget": "textarea", "rows": 6},
                    },
                    "format": {
                        "type": "string",
                        "title": "Output Format",
                        "enum": ["text", "json", "markdown", "html", "code"],
                        "default": "text",
                    },
                    "model": {
                        "type": "string",
                        "title": "AI Model",
                        "enum": ["claude-sonnet-4", "gpt-4o", "claude-haiku-3"],
                        "default": "claude-sonnet-4",
                    },
                    "temperature": {
                        "type": "number",
                        "title": "Temperature",
                        "minimum": 0,
                        "maximum": 2,
                        "default": 0.8,
                    },
                },
            },
            default_config={
                "prompt": "Generate content based on the input.",
                "format": "text",
                "model": "claude-sonnet-4",
                "temperature": 0.8,
            },
        ))

        self.register(BlockDefinition(
            block_id="ai.transform",
            name="AI Transform",
            description="Apply a transformation to input data using AI",
            category="ai",
            icon="Shuffle",
            color="#8B5CF6",
            config_schema={
                "type": "object",
                "required": ["transformation"],
                "properties": {
                    "transformation": {
                        "type": "string",
                        "title": "Transformation",
                        "description": "Describe how to transform the input data (e.g., 'Translate to French', 'Convert to formal tone')",
                        "x-ui": {"widget": "textarea", "rows": 3},
                    },
                    "input_field": {
                        "type": "string",
                        "title": "Input Field",
                        "description": "JSON path to the field to transform (e.g., 'content.body')",
                        "default": "",
                    },
                    "model": {
                        "type": "string",
                        "title": "AI Model",
                        "enum": ["claude-haiku-3", "claude-sonnet-4", "gpt-4o-mini"],
                        "default": "claude-haiku-3",
                    },
                },
            },
            default_config={
                "transformation": "Translate to English",
                "input_field": "",
                "model": "claude-haiku-3",
            },
        ))

    # ── Action Blocks ──────────────────────────────────────────────────────────

    def _register_action_blocks(self) -> None:
        self.register(BlockDefinition(
            block_id="action.send_email",
            name="Send Email",
            description="Send an email via the connected email service",
            category="action",
            icon="Send",
            color="#F59E0B",
            config_schema={
                "type": "object",
                "required": ["to", "subject"],
                "properties": {
                    "to": {
                        "type": "string",
                        "title": "To",
                        "description": "Recipient email address(es). Multiple addresses separated by comma.",
                    },
                    "subject": {
                        "type": "string",
                        "title": "Subject",
                    },
                    "body": {
                        "type": "string",
                        "title": "Body",
                        "description": "Email body content (supports markdown)",
                        "x-ui": {"widget": "textarea", "rows": 8},
                    },
                    "cc": {
                        "type": "string",
                        "title": "CC",
                    },
                    "bcc": {
                        "type": "string",
                        "title": "BCC",
                    },
                    "draft_only": {
                        "type": "boolean",
                        "title": "Save as Draft Only",
                        "description": "Create draft without sending",
                        "default": False,
                    },
                },
            },
            default_config={"draft_only": False},
        ))

        self.register(BlockDefinition(
            block_id="action.send_whatsapp",
            name="Send WhatsApp",
            description="Send a WhatsApp message via connected WhatsApp account",
            category="action",
            icon="MessageCircle",
            color="#F59E0B",
            config_schema={
                "type": "object",
                "required": ["to", "message"],
                "properties": {
                    "to": {
                        "type": "string",
                        "title": "Recipient",
                        "description": "Phone number with country code (e.g., '+2348012345678')",
                    },
                    "message": {
                        "type": "string",
                        "title": "Message",
                        "x-ui": {"widget": "textarea", "rows": 4},
                    },
                    "media_url": {
                        "type": "string",
                        "title": "Media URL",
                        "description": "Optional URL to image, video, or document",
                    },
                },
            },
        ))

        self.register(BlockDefinition(
            block_id="action.create_crm_record",
            name="Create CRM Record",
            description="Create a record in the connected CRM service",
            category="action",
            icon="UserPlus",
            color="#F59E0B",
            config_schema={
                "type": "object",
                "required": ["service"],
                "properties": {
                    "service": {
                        "type": "string",
                        "title": "CRM Service",
                        "enum": ["hubspot", "salesforce", "pipedrive", "zoho", "custom"],
                        "default": "hubspot",
                    },
                    "object_type": {
                        "type": "string",
                        "title": "Object Type",
                        "enum": ["contact", "deal", "company", "lead", "task"],
                        "default": "contact",
                    },
                    "fields": {
                        "type": "object",
                        "title": "Field Values",
                        "description": "Key-value pairs of field names and values",
                        "default": {},
                    },
                },
            },
            default_config={"service": "hubspot", "object_type": "contact", "fields": {}},
        ))

        self.register(BlockDefinition(
            block_id="action.update_sheet",
            name="Update Sheet",
            description="Add or update data in a spreadsheet (Google Sheets, Excel)",
            category="action",
            icon="Table",
            color="#F59E0B",
            config_schema={
                "type": "object",
                "required": ["spreadsheet_id"],
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "title": "Spreadsheet ID / URL",
                    },
                    "sheet_name": {
                        "type": "string",
                        "title": "Sheet Name",
                        "default": "Sheet1",
                    },
                    "data": {
                        "type": "array",
                        "title": "Data Rows",
                        "description": "Array of row objects to append",
                        "items": {"type": "object"},
                        "default": [],
                    },
                    "mode": {
                        "type": "string",
                        "title": "Mode",
                        "enum": ["append", "overwrite", "update"],
                        "default": "append",
                    },
                },
            },
            default_config={"sheet_name": "Sheet1", "mode": "append"},
        ))

        self.register(BlockDefinition(
            block_id="action.http_request",
            name="HTTP Request",
            description="Make an HTTP request to any URL",
            category="action",
            icon="Globe",
            color="#F59E0B",
            config_schema={
                "type": "object",
                "required": ["url", "method"],
                "properties": {
                    "url": {
                        "type": "string",
                        "title": "URL",
                        "description": "Full URL including protocol (e.g., 'https://api.example.com/data')",
                    },
                    "method": {
                        "type": "string",
                        "title": "HTTP Method",
                        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                        "default": "GET",
                    },
                    "headers": {
                        "type": "object",
                        "title": "Headers",
                        "description": "Key-value pairs of HTTP headers",
                        "default": {},
                    },
                    "body": {
                        "type": "string",
                        "title": "Request Body",
                        "description": "JSON or text body for POST/PUT/PATCH requests",
                        "x-ui": {"widget": "textarea", "rows": 6},
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "title": "Timeout (seconds)",
                        "minimum": 1,
                        "maximum": 300,
                        "default": 30,
                    },
                    "response_parser": {
                        "type": "string",
                        "title": "Response Field (JSON path)",
                        "description": "Optional JSONPath to extract from response (e.g., 'data.results')",
                    },
                },
            },
            default_config={"method": "GET", "timeout_seconds": 30},
        ))

        self.register(BlockDefinition(
            block_id="action.create_file",
            name="Create File",
            description="Create a file in the connected storage service",
            category="action",
            icon="FilePlus",
            color="#F59E0B",
            config_schema={
                "type": "object",
                "required": ["path", "content"],
                "properties": {
                    "path": {
                        "type": "string",
                        "title": "File Path",
                        "description": "Path including filename (e.g., '/reports/daily-summary.md')",
                    },
                    "content": {
                        "type": "string",
                        "title": "Content",
                        "x-ui": {"widget": "textarea", "rows": 8},
                    },
                    "mime_type": {
                        "type": "string",
                        "title": "MIME Type",
                        "description": "Optional MIME type (auto-detected from extension if not provided)",
                    },
                },
            },
        ))

        self.register(BlockDefinition(
            block_id="action.post_slack",
            name="Post to Slack",
            description="Send a message to a Slack channel",
            category="action",
            icon="Slack",
            color="#F59E0B",
            config_schema={
                "type": "object",
                "required": ["channel", "message"],
                "properties": {
                    "channel": {
                        "type": "string",
                        "title": "Channel",
                        "description": "Channel name (e.g., '#general') or ID",
                    },
                    "message": {
                        "type": "string",
                        "title": "Message",
                        "description": "Message text (supports Slack markdown)",
                        "x-ui": {"widget": "textarea", "rows": 4},
                    },
                    "as_bot": {
                        "type": "boolean",
                        "title": "Post as Bot",
                        "description": "Post as the connected bot instead of a user",
                        "default": True,
                    },
                },
            },
            default_config={"as_bot": True},
        ))

    # ── Logic Blocks ───────────────────────────────────────────────────────────

    def _register_logic_blocks(self) -> None:
        self.register(BlockDefinition(
            block_id="logic.condition",
            name="Condition",
            description="Route execution based on a conditional expression (if/then/else)",
            category="logic",
            icon="GitBranch",
            color="#14B8A6",
            config_schema={
                "type": "object",
                "required": ["expression"],
                "properties": {
                    "expression": {
                        "type": "string",
                        "title": "Condition Expression",
                        "description": "Python expression using 'data' variable. Example: 'data.score > 50'",
                        "x-ui": {"widget": "textarea", "rows": 2},
                    },
                    "label_true": {
                        "type": "string",
                        "title": "True Output Label",
                        "default": "True",
                    },
                    "label_false": {
                        "type": "string",
                        "title": "False Output Label",
                        "default": "False",
                    },
                },
            },
            input_ports=[_port("input", "data", "Input")],
            output_ports=[
                _port("true", "data", "True"),
                _port("false", "data", "False"),
            ],
            default_config={
                "expression": "data.score > 50",
                "label_true": "True",
                "label_false": "False",
            },
        ))

        self.register(BlockDefinition(
            block_id="logic.filter",
            name="Filter",
            description="Filter an array of items based on a condition",
            category="logic",
            icon="Filter",
            color="#14B8A6",
            config_schema={
                "type": "object",
                "required": ["condition"],
                "properties": {
                    "condition": {
                        "type": "string",
                        "title": "Filter Condition",
                        "description": "Python expression using 'item' variable. Items where expression is True are kept.",
                        "x-ui": {"widget": "textarea", "rows": 2},
                    },
                    "input_array_field": {
                        "type": "string",
                        "title": "Input Array Field (JSON path)",
                        "description": "Path to the array in the input data. Leave empty to use entire input as array.",
                        "default": "",
                    },
                },
            },
            default_config={"condition": "True", "input_array_field": ""},
        ))

        self.register(BlockDefinition(
            block_id="logic.router",
            name="Router",
            description="Route to different paths based on multiple cases (switch/case)",
            category="logic",
            icon="GitFork",
            color="#14B8A6",
            config_schema={
                "type": "object",
                "required": ["cases"],
                "properties": {
                    "cases": {
                        "type": "array",
                        "title": "Cases",
                        "description": "List of cases with expressions and labels",
                        "items": {
                            "type": "object",
                            "required": ["label", "expression"],
                            "properties": {
                                "label": {"type": "string", "title": "Label"},
                                "expression": {"type": "string", "title": "Expression"},
                            },
                        },
                        "default": [
                            {"label": "Case 1", "expression": "data.type == 'a'"},
                            {"label": "Case 2", "expression": "data.type == 'b'"},
                        ],
                    },
                    "default_case": {
                        "type": "string",
                        "title": "Default Case Label",
                        "default": "Other",
                    },
                    "input_field": {
                        "type": "string",
                        "title": "Input Field (JSON path)",
                        "description": "Path to the value to route on. Leave empty to use entire input.",
                        "default": "",
                    },
                },
            },
            output_ports=[_port("default", "data", "Default")],
            default_config={
                "cases": [
                    {"label": "Case 1", "expression": "data.type == 'a'"},
                    {"label": "Case 2", "expression": "data.type == 'b'"},
                ],
                "default_case": "Other",
                "input_field": "",
            },
        ))

        self.register(BlockDefinition(
            block_id="logic.delay",
            name="Delay",
            description="Pause execution for a specified duration",
            category="logic",
            icon="Hourglass",
            color="#14B8A6",
            config_schema={
                "type": "object",
                "required": ["duration"],
                "properties": {
                    "duration": {
                        "type": "integer",
                        "title": "Duration",
                        "description": "Delay duration in the selected unit",
                        "minimum": 0,
                        "default": 5,
                    },
                    "unit": {
                        "type": "string",
                        "title": "Unit",
                        "enum": ["seconds", "minutes", "hours"],
                        "default": "seconds",
                    },
                },
            },
            default_config={"duration": 5, "unit": "seconds"},
        ))

        self.register(BlockDefinition(
            block_id="logic.loop",
            name="Loop",
            description="Iterate over an array, executing connected blocks for each item",
            category="logic",
            icon="Repeat2",
            color="#14B8A6",
            config_schema={
                "type": "object",
                "required": [],
                "properties": {
                    "iterations": {
                        "type": "integer",
                        "title": "Max Iterations",
                        "description": "Maximum number of loop iterations (0 = unlimited)",
                        "minimum": 0,
                        "maximum": 1000,
                        "default": 10,
                    },
                    "input_array_field": {
                        "type": "string",
                        "title": "Input Array Field (JSON path)",
                        "description": "Path to the array to iterate over",
                        "default": "",
                    },
                    "batch_size": {
                        "type": "integer",
                        "title": "Batch Size",
                        "description": "Number of items to process in parallel (1 = sequential)",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 1,
                    },
                },
            },
            default_config={"iterations": 10, "input_array_field": "", "batch_size": 1},
        ))

        self.register(BlockDefinition(
            block_id="logic.wait",
            name="Wait For",
            description="Pause execution until a condition is met or timeout",
            category="logic",
            icon="Pause",
            color="#14B8A6",
            config_schema={
                "type": "object",
                "required": [],
                "properties": {
                    "condition": {
                        "type": "string",
                        "title": "Wait Condition",
                        "description": "Python expression that must evaluate to True to continue",
                        "x-ui": {"widget": "textarea", "rows": 2},
                    },
                    "check_interval_seconds": {
                        "type": "integer",
                        "title": "Check Interval (seconds)",
                        "minimum": 1,
                        "maximum": 3600,
                        "default": 10,
                    },
                    "timeout_minutes": {
                        "type": "integer",
                        "title": "Timeout (minutes)",
                        "minimum": 1,
                        "maximum": 1440,
                        "default": 60,
                    },
                },
            },
            default_config={
                "check_interval_seconds": 10,
                "timeout_minutes": 60,
            },
        ))

    # ── Registration ───────────────────────────────────────────────────────────

    def register(self, block: BlockDefinition) -> None:
        """Register a block definition."""
        self._blocks[block.id] = block

    def get(self, block_id: str) -> BlockDefinition | None:
        """Get a block definition by its ID."""
        return self._blocks.get(block_id)

    def get_by_category(self, category: str) -> list[BlockDefinition]:
        """Get all block definitions in a category."""
        return [b for b in self._blocks.values() if b.category == category]

    def list_all(self) -> list[BlockDefinition]:
        """Return all registered block definitions."""
        return list(self._blocks.values())

    def list_all_dicts(self) -> list[dict[str, Any]]:
        """Return all block definitions as dicts."""
        return [b.to_dict() for b in self._blocks.values()]


# ─── Singleton Instance ─────────────────────────────────────────────────────────

block_registry = BlockRegistry()

__all__ = [
    "block_registry",
    "BlockRegistry",
    "BlockDefinition",
]
