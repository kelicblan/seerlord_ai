import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import yaml
from loguru import logger
from langchain_core.tools import tool

from server.core.config import settings
from server.kernel.registry import registry

def get_agent_email(agent_id: str) -> str:
    """
    Get the configured email address for a given agent.
    """
    # 1. Try to get plugin directory from registry
    plugin_dir_name = registry.get_plugin_dir(agent_id)
    if not plugin_dir_name:
        # Fallback: assume directory name matches agent_id
        plugin_dir_name = agent_id
        
    config_path = Path(settings.PLUGIN_DIR) / plugin_dir_name / "config.yaml"
    
    if not config_path.exists():
        logger.warning(f"Config file not found for agent: {agent_id} at {config_path}")
        return None
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            
            email = None
            if config and isinstance(config, dict):
                # Try under configurable first
                if config.get("configurable") and isinstance(config["configurable"], dict):
                     email = config["configurable"].get("agent_email")
                
                # Fallback to top level
                if not email:
                     email = config.get("agent_email")
                 
            return email
    except Exception as e:
        logger.error(f"Error reading config for {agent_id}: {e}")
        return None

@tool
def send_system_email(target_agent_id: str, subject: str, body: str) -> str:
    """
    Send an email to the registered email address of a specific agent.
    
    Args:
        target_agent_id: The ID of the agent to send email to.
        subject: Email subject.
        body: Email content.
    """
    logger.info(f"Attempting to send email to agent: {target_agent_id}")
    
    recipient = get_agent_email(target_agent_id)
    if not recipient:
        return f"Error: No email address configured for agent '{target_agent_id}'."
        
    sender = settings.EMAIL_SERVER_EMAIL_ADDRESS
    password = settings.EMAIL_SERVER_PASSWORD
    smtp_host = settings.EMAIL_SERVER_SMTP_HOST
    smtp_port = settings.EMAIL_SERVER_SMTP_PORT
    
    if not all([sender, password, smtp_host]):
        return "Error: System email configuration is missing (check .env)."
        
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # SSL for 465, STARTTLS for 587
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        logger.success(f"Email sent to {recipient}")
        return f"Email successfully sent to {recipient} ({target_agent_id})."
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return f"Failed to send email: {str(e)}"
