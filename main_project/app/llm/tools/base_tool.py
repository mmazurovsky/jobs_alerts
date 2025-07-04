"""
Base tool class with standardized documentation and input requirements.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class InputType(Enum):
    """Types of input parameters."""
    TEXT = "text"
    SELECT = "select"
    MULTISELECT = "multiselect"
    BOOLEAN = "boolean"
    NUMBER = "number"

@dataclass
class ParameterInfo:
    """Information about a tool parameter."""
    name: str
    description: str
    type: InputType
    required: bool
    default: Optional[Any] = None
    options: Optional[List[str]] = None
    example: Optional[str] = None
    validation_rules: Optional[str] = None

@dataclass
class ToolDocumentation:
    """Complete documentation for a tool."""
    name: str
    description: str
    purpose: str
    parameters: List[ParameterInfo]
    examples: List[str]
    confirmation_required: bool = False
    
class DocumentedTool(ABC):
    """Base class for tools with comprehensive documentation."""
    
    @property
    @abstractmethod
    def tool_documentation(self) -> ToolDocumentation:
        """Return complete tool documentation."""
        pass
    
    def get_parameter_help(self, parameter_name: str) -> Optional[ParameterInfo]:
        """Get help for a specific parameter."""
        for param in self.tool_documentation.parameters:
            if param.name == parameter_name:
                return param
        return None
    
    def get_required_parameters(self) -> List[ParameterInfo]:
        """Get list of required parameters."""
        return [p for p in self.tool_documentation.parameters if p.required]
    
    def get_optional_parameters(self) -> List[ParameterInfo]:
        """Get list of optional parameters."""
        return [p for p in self.tool_documentation.parameters if not p.required]
    
    def format_parameter_help(self, parameter: ParameterInfo) -> str:
        """Format parameter help for display."""
        help_text = f"**{parameter.name}** ({parameter.type.value})"
        if parameter.required:
            help_text += " - *Required*"
        else:
            help_text += " - *Optional*"
        
        help_text += f"\n  {parameter.description}"
        
        if parameter.options:
            help_text += f"\n  Options: {', '.join(parameter.options)}"
        
        if parameter.example:
            help_text += f"\n  Example: {parameter.example}"
        
        if parameter.default is not None:
            help_text += f"\n  Default: {parameter.default}"
        
        if parameter.validation_rules:
            help_text += f"\n  Rules: {parameter.validation_rules}"
        
        return help_text
    
    def get_usage_help(self) -> str:
        """Get comprehensive usage help for this tool."""
        doc = self.tool_documentation
        
        help_text = f"🛠️ **{doc.name}**\n"
        help_text += f"{doc.purpose}\n\n"
        help_text += f"📝 **Description:** {doc.description}\n\n"
        
        if doc.confirmation_required:
            help_text += "⚠️ **Note:** This operation requires confirmation before execution.\n\n"
        
        # Required parameters
        required_params = self.get_required_parameters()
        if required_params:
            help_text += "📋 **Required Parameters:**\n"
            for param in required_params:
                help_text += f"• {self.format_parameter_help(param)}\n\n"
        
        # Optional parameters
        optional_params = self.get_optional_parameters()
        if optional_params:
            help_text += "🔧 **Optional Parameters:**\n"
            for param in optional_params:
                help_text += f"• {self.format_parameter_help(param)}\n\n"
        
        # Examples
        if doc.examples:
            help_text += "💬 **Example Usage:**\n"
            for i, example in enumerate(doc.examples, 1):
                help_text += f"{i}. \"{example}\"\n"
        
        return help_text
    
    def get_parameter_prompt(self, missing_params: List[str]) -> str:
        """Generate prompt for missing parameters."""
        if not missing_params:
            return ""
        
        prompt = "I need some additional information:\n\n"
        
        for param_name in missing_params:
            param_info = self.get_parameter_help(param_name)
            if param_info:
                prompt += f"• **{param_info.name}**: {param_info.description}"
                if param_info.example:
                    prompt += f" (e.g., {param_info.example})"
                if param_info.options:
                    prompt += f"\n  Choose from: {', '.join(param_info.options)}"
                prompt += "\n\n"
        
        prompt += "Please provide these details and I'll help you proceed."
        return prompt 