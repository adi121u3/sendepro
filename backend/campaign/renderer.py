import re
import logging

logger = logging.getLogger("email_sender_pro.renderer")

class TemplateRenderer:
    @staticmethod
    def render(template_text: str, lead, account, fallback_value: str = "") -> str:
        if not template_text:
            return ""
        
        variables = {
            "firstname": lead.first_name if lead and lead.first_name else fallback_value,
            "lastname": lead.last_name if lead and lead.last_name else fallback_value,
            "first_name": lead.first_name if lead and lead.first_name else fallback_value,
            "last_name": lead.last_name if lead and lead.last_name else fallback_value,
            "email": lead.email if lead and lead.email else fallback_value,
            "company": lead.company if lead and lead.company else fallback_value,
            "position": lead.position if lead and lead.position else fallback_value,
            "sendername": lead.sender_name or (account.from_name if account else "") or "Sender",
            "sender_name": lead.sender_name or (account.from_name if account else "") or "Sender",
            "senderfullname": lead.sender_full_name or lead.sender_name or (account.from_name if account else "") or "Sender",
            "sender_full_name": lead.sender_full_name or lead.sender_name or (account.from_name if account else "") or "Sender",
        }

        def replace_var(match):
            key = match.group(1).strip().lower().replace("_", "")
            return str(variables.get(key, fallback_value))

        # Match both {{variable}} and {{ variable }}
        rendered = re.sub(r'\{\{\s*([^}]+)\s*\}\}', replace_var, template_text)
        return rendered
