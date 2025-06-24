"""
Tool registry for centralized access to tool documentation and help.
"""
from typing import Dict, List, Optional
from .base_tool import DocumentedTool, ToolDocumentation
from .list_job_searches_tool import ListJobSearchesTool
from .create_job_search_tool import CreateJobSearchTool
from .delete_job_search_tool import DeleteJobSearchTool
from .get_job_search_details_tool import GetJobSearchDetailsTool
from .one_time_search_tool import OneTimeSearchTool

class ToolRegistry:
    """Registry for managing and accessing tool documentation."""
    
    def __init__(self, tools: List[DocumentedTool]):
        """Initialize with a list of documented tools."""
        self.tools = {tool.name: tool for tool in tools}
    
    def get_all_tools_help(self) -> str:
        """Get comprehensive help for all available tools."""
        help_text = "🤖 **Available Operations**\n\n"
        help_text += "I can help you with the following job search operations:\n\n"
        
        for tool in self.tools.values():
            doc = tool.tool_documentation
            help_text += f"🔹 **{doc.name}**\n"
            help_text += f"   {doc.description}\n"
            if doc.examples:
                help_text += f"   💬 Example: \"{doc.examples[0]}\"\n"
            help_text += "\n"
        
        help_text += "\n📝 **How to use:**\n"
        help_text += "Just describe what you want to do in natural language! I'll understand your intent and guide you through the process.\n\n"
        help_text += "📋 **Need detailed help?** Say \"help with [operation]\" for specific guidance.\n"
        
        return help_text
    
    def get_tool_help(self, tool_name: str) -> Optional[str]:
        """Get detailed help for a specific tool."""
        tool = self.tools.get(tool_name)
        if not tool:
            return None
        return tool.get_usage_help()
    
    def get_tool_by_operation(self, operation_description: str) -> Optional[DocumentedTool]:
        """Find a tool based on operation description."""
        operation_lower = operation_description.lower()
        
        # Simple keyword matching - could be enhanced with NLP
        for tool in self.tools.values():
            doc = tool.tool_documentation
            
            # Check tool name
            if any(word in operation_lower for word in doc.name.lower().split()):
                return tool
            
            # Check examples
            for example in doc.examples:
                if any(word in operation_lower for word in example.lower().split()):
                    return tool
        
        return None
    
    def get_parameter_help(self, tool_name: str, parameter_name: str) -> Optional[str]:
        """Get help for a specific parameter of a tool."""
        tool = self.tools.get(tool_name)
        if not tool:
            return None
        
        param_info = tool.get_parameter_help(parameter_name)
        if not param_info:
            return None
        
        return tool.format_parameter_help(param_info)
    
    def get_missing_parameter_prompt(self, tool_name: str, missing_params: List[str]) -> str:
        """Generate a prompt for missing parameters."""
        tool = self.tools.get(tool_name)
        if not tool:
            return "I couldn't find information about that operation."
        
        return tool.get_parameter_prompt(missing_params)

def create_tool_registry(job_search_manager) -> ToolRegistry:
    """Create and configure the tool registry with all available tools."""
    tools = [
        ListJobSearchesTool(job_search_manager),
        CreateJobSearchTool(job_search_manager),
        DeleteJobSearchTool(job_search_manager),
        GetJobSearchDetailsTool(job_search_manager),
        OneTimeSearchTool(job_search_manager),
    ]
    
    return ToolRegistry(tools) 