# Multi-Agent Job Search System - Button-First Implementation Plan

## 🎯 Main Objective
Transform the current conversational LLM interface into a multi-agent system with **button-based UI as primary interface** for Telegram bot, featuring **separate specialized agents** for each write operation and **direct database access** for read operations.

## 📋 Architecture Overview - Separate Agent Strategy

### 🤖 Agent Architecture Requirements
1. **No Generic Agents** - Each write operation has its own dedicated agent
2. **Button-First Interface** - Buttons are primary UI, not enhancement
3. **Direct Database Access** - No LLM for list/details operations
4. **Centralized System Prompts** - Single file managing all agent prompts
5. **Tool Registry Alignment** - Commands mirror registered tools

### 🎛️ Core Components Strategy

#### Separate Specialized Agents
- **CreateJobSearchAgent** - Dedicated agent for job search creation
- **OneTimeSearchAgent** - Dedicated agent for immediate searches  
- **DeleteJobSearchAgent** - Dedicated agent for search deletion
- **No LLM Agents** - Direct operations for list/details

#### Button-First UI
- **TelegramBot** - Button interface as primary interaction method
- **Menu System** - Hierarchical button navigation
- **Callback Handling** - Process all button interactions

#### Centralized Prompt Management
- **AgentPromptsManager** - Single class providing all system prompts
- **Prompt File** - One file containing all agent system prompts

## 📝 Implementation Plan - Separate Agents Approach

### Phase 1: Foundation - Direct Operations (Low Dependencies)

#### Task 1.1: Create Agent Prompts Management System
**Priority**: Critical | **Dependencies**: None

**Subtasks**:
- [ ] **Create `main_project/app/llm/agent_prompts.py`**
  - Create `AgentPromptsManager` class
  - Add `get_create_search_prompt() -> str` method
  - Add `get_one_time_search_prompt() -> str` method  
  - Add `get_delete_search_prompt() -> str` method
  - Add `get_menu_prompt() -> str` method
  - Include validation workflows and confirmation steps in prompts
  - Reference existing tool registry for parameter details

**Files to create**:
- `main_project/app/llm/agent_prompts.py`

#### Task 1.2: Enhance JobSearchManager with Direct Formatting
**Priority**: High | **Dependencies**: None

**Subtasks**:
- [ ] **Extend `main_project/app/core/job_search_manager.py`**
  - Add `get_user_searches_formatted(user_id: int) -> str` method (no LLM)
  - Add `get_search_details_formatted(user_id: int, search_id: str) -> str` method (no LLM)
  - Add `search_exists_for_user(user_id: int, search_id: str) -> bool` method
  - Add `get_user_searches_for_selection(user_id: int) -> List[Dict]` method for buttons
  - Use existing database patterns and formatting logic

**Files to modify**:
- `main_project/app/core/job_search_manager.py`

#### Task 1.3: Create Button-First TelegramBot Enhancement
**Priority**: High | **Dependencies**: Task 1.2

**Subtasks**:
- [ ] **Enhance `main_project/app/bot/telegram_bot.py`**
  - Add `from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery`
  - Add `_create_main_menu_keyboard() -> InlineKeyboardMarkup` method
  - Add `_create_search_selection_keyboard(searches: List[Dict]) -> InlineKeyboardMarkup` method
  - Add `_create_confirmation_keyboard() -> InlineKeyboardMarkup` method
  - Replace `start()` command to show button menu by default
  - Add `callback_query_handler` method for all button interactions
  - Add direct operations: `_handle_list_searches_direct()`, `_handle_search_details_direct()`

**Files to modify**:
- `main_project/app/bot/telegram_bot.py`

### Phase 2: Separate Agent Creation (Medium Dependencies)

#### Task 2.1: Create CreateJobSearchAgent
**Priority**: High | **Dependencies**: Task 1.1

**Subtasks**:
- [ ] **Create `main_project/app/llm/agents/create_job_search_agent.py`**
  - Create `CreateJobSearchAgent` class inheriting from base LLM patterns
  - Add `__init__(self, deepseek_client, tool_registry, prompts_manager)` method
  - Add `start_creation_workflow(user_id: int) -> str` method
  - Add `process_user_input(message: str, user_id: int, workflow_state: dict) -> str` method
  - Add `_validate_and_collect_parameters()` method using existing tool validation
  - Add `_show_confirmation_summary()` method
  - Add `_execute_creation()` method using existing CreateJobSearchTool
  - Implement multi-step validation with user-friendly error messages

**Files to create**:
- `main_project/app/llm/agents/create_job_search_agent.py`
- `main_project/app/llm/agents/__init__.py`

#### Task 2.2: Create OneTimeSearchAgent  
**Priority**: High | **Dependencies**: Task 1.1

**Subtasks**:
- [ ] **Create `main_project/app/llm/agents/one_time_search_agent.py`**
  - Create `OneTimeSearchAgent` class inheriting from base LLM patterns
  - Add `__init__(self, deepseek_client, tool_registry, prompts_manager)` method
  - Add `start_search_workflow(user_id: int) -> str` method
  - Add `process_user_input(message: str, user_id: int, workflow_state: dict) -> str` method
  - Add `_validate_and_collect_parameters()` method using existing tool validation
  - Add `_show_search_summary()` method
  - Add `_execute_search()` method using existing OneTimeSearchTool
  - Implement parameter collection with validation and confirmation

**Files to create**:
- `main_project/app/llm/agents/one_time_search_agent.py`

#### Task 2.3: Create DeleteJobSearchAgent
**Priority**: High | **Dependencies**: Task 1.1, Task 1.2

**Subtasks**:
- [ ] **Create `main_project/app/llm/agents/delete_job_search_agent.py`**
  - Create `DeleteJobSearchAgent` class inheriting from base LLM patterns
  - Add `__init__(self, deepseek_client, tool_registry, prompts_manager)` method
  - Add `start_deletion_workflow(user_id: int) -> str` method
  - Add `process_user_input(message: str, user_id: int, workflow_state: dict) -> str` method
  - Add `_show_available_searches()` method using JobSearchManager
  - Add `_confirm_deletion(search_id: str)` method
  - Add `_execute_deletion()` method using existing DeleteJobSearchTool
  - Implement search selection and confirmation workflow

**Files to create**:
- `main_project/app/llm/agents/delete_job_search_agent.py`

### Phase 3: Agent Integration & State Management (High Dependencies)

#### Task 3.1: Create Agent Factory and Session Management
**Priority**: Critical | **Dependencies**: Task 2.1, 2.2, 2.3

**Subtasks**:
- [ ] **Create `main_project/app/llm/agent_factory.py`**
  - Create `AgentFactory` class
  - Add `create_create_search_agent() -> CreateJobSearchAgent` method
  - Add `create_one_time_search_agent() -> OneTimeSearchAgent` method
  - Add `create_delete_search_agent() -> DeleteJobSearchAgent` method
  - Add dependency injection for shared components (deepseek_client, tool_registry, prompts_manager)
  - Add `AgentSession` dataclass to track current agent and workflow state

**Files to create**:
- `main_project/app/llm/agent_factory.py`

#### Task 3.2: Implement Session State Management  
**Priority**: High | **Dependencies**: Task 3.1

**Subtasks**:
- [ ] **Create `main_project/app/core/session_manager.py`**
  - Create `SessionManager` class
  - Add `get_user_session(user_id: int) -> Optional[AgentSession]` method
  - Add `set_user_session(user_id: int, session: AgentSession)` method
  - Add `clear_user_session(user_id: int)` method
  - Add `is_user_in_workflow(user_id: int) -> bool` method
  - Use in-memory storage with timeout for session cleanup

**Files to create**:
- `main_project/app/core/session_manager.py`

#### Task 3.3: Enhanced Button Navigation System
**Priority**: High | **Dependencies**: Task 3.1, 3.2

**Subtasks**:
- [ ] **Enhance TelegramBot with complete button handling**
  - Add `_route_callback_query(query: CallbackQuery)` method
  - Add `_handle_main_menu_selection(query: CallbackQuery)` method
  - Add `_handle_agent_workflow_button(query: CallbackQuery)` method
  - Add `_handle_search_selection_button(query: CallbackQuery)` method
  - Add `_handle_confirmation_button(query: CallbackQuery)` method
  - Add agent initialization and workflow management
  - Add session state integration for workflow continuity

**Files to modify**:
- `main_project/app/bot/telegram_bot.py`

### Phase 4: Complete Integration (Highest Dependencies)

#### Task 4.1: Integrate All Agents with TelegramBot
**Priority**: Critical | **Dependencies**: All previous tasks

**Subtasks**:
- [ ] **Complete TelegramBot agent integration**
  - Add `agent_factory: AgentFactory` to TelegramBot initialization
  - Add `session_manager: SessionManager` to TelegramBot initialization
  - Modify `handle_message()` to route to appropriate agent based on session state
  - Add `_start_agent_workflow(user_id: int, agent_type: str)` method
  - Add `_continue_agent_workflow(user_id: int, message: str)` method
  - Add `_end_agent_workflow(user_id: int)` method
  - Integrate direct database operations with button responses
  - Preserve existing rate limiting and error handling

**Files to modify**:
- `main_project/app/bot/telegram_bot.py`

#### Task 4.2: Update Container and Main Application
**Priority**: Medium | **Dependencies**: Task 4.1

**Subtasks**:
- [ ] **Update `main_project/app/core/container.py`**
  - Add `agent_prompts_manager: AgentPromptsManager` dependency
  - Add `agent_factory: AgentFactory` dependency  
  - Add `session_manager: SessionManager` dependency
  - Update TelegramBot initialization with new dependencies
  - Maintain existing dependency injection patterns

**Files to modify**:
- `main_project/app/core/container.py`

#### Task 4.3: Remove or Refactor Existing JobSearchAgent
**Priority**: Low | **Dependencies**: Task 4.2

**Subtasks**:
- [ ] **Decide on `main_project/app/llm/job_search_agent.py`**
  - Option A: Remove completely (preferred for clean separation)
  - Option B: Keep as fallback for text-only interactions
  - Update any remaining references to use new specialized agents
  - Remove from container if not needed

**Files to modify or remove**:
- `main_project/app/llm/job_search_agent.py` (potentially remove)
- Update any imports/references

### Phase 5: Testing & Validation (Final Phase)

#### Task 5.1: Create Button Workflow Tests
**Priority**: High | **Dependencies**: Task 4.2

**Subtasks**:
- [ ] **Create `main_project/tests/test_button_workflows.py`**
  - Add test cases for button navigation
  - Add test cases for each agent workflow (create, search, delete)
  - Add test cases for session state management
  - Add test cases for direct database operations
  - Mock CallbackQuery and InlineKeyboard interactions
  - Test validation and error handling in agent workflows

**Files to create**:
- `main_project/tests/test_button_workflows.py`

#### Task 5.2: Create Separate Agent Tests
**Priority**: Medium | **Dependencies**: Task 5.1

**Subtasks**:
- [ ] **Create `main_project/tests/test_specialized_agents.py`**
  - Add unit tests for CreateJobSearchAgent
  - Add unit tests for OneTimeSearchAgent  
  - Add unit tests for DeleteJobSearchAgent
  - Add unit tests for AgentPromptsManager
  - Add unit tests for AgentFactory
  - Mock external dependencies (DeepSeek, tool registry)

**Files to create**:
- `main_project/tests/test_specialized_agents.py`

#### Task 5.3: Update Existing Tests
**Priority**: Medium | **Dependencies**: Task 5.2

**Subtasks**:
- [ ] **Update `main_project/tests/test_conversation_integration.py`**
  - Add button interaction test scenarios
  - Update existing tests to work with new agent system
  - Add session state tests
  - Ensure backward compatibility tests if keeping old agent

**Files to modify**:
- `main_project/tests/test_conversation_integration.py`

## 🎯 Implementation Order Summary

### Phase 1 (Foundation) - Days 1-2
1. Create AgentPromptsManager system
2. Enhance JobSearchManager with direct formatting 
3. Create button-first TelegramBot enhancement

### Phase 2 (Separate Agents) - Days 3-5
1. Create CreateJobSearchAgent
2. Create OneTimeSearchAgent
3. Create DeleteJobSearchAgent

### Phase 3 (Integration) - Days 6-7
1. Create AgentFactory and session management
2. Implement session state management
3. Enhanced button navigation system

### Phase 4 (Complete Integration) - Days 8-9
1. Integrate all agents with TelegramBot
2. Update container and main application
3. Remove or refactor existing JobSearchAgent

### Phase 5 (Testing) - Days 10-11
1. Create button workflow tests
2. Create separate agent tests
3. Update existing tests

## 📊 Key Differences from Previous Approach

### Separate Agents (Required)
- **CreateJobSearchAgent**: Dedicated agent with specific system prompt
- **OneTimeSearchAgent**: Dedicated agent with specific system prompt  
- **DeleteJobSearchAgent**: Dedicated agent with specific system prompt
- **No Generic Agent**: Each write operation has its own agent class

### Button-First Design (Required)
- **Primary Interface**: Buttons are the main interaction method
- **Menu Navigation**: Hierarchical button-based menus
- **Direct Operations**: List/details bypass LLM completely
- **Callback Routing**: All interactions route through button callbacks

### Centralized Prompt Management (Required)
- **AgentPromptsManager**: Single class providing all agent system prompts
- **Single File**: All prompts defined in one location
- **Tool Registry Integration**: Prompts reference existing tool documentation

### Direct Database Access (Required)
- **No LLM for List**: Direct database formatting for search lists
- **No LLM for Details**: Direct database formatting for search details
- **Fast Operations**: Immediate responses for read operations
- **Formatted Output**: Pre-formatted strings without LLM processing

## 🔧 Technical Implementation Details

### AgentPromptsManager Structure
```python
class AgentPromptsManager:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
    
    def get_create_search_prompt(self) -> str:
        """System prompt for CreateJobSearchAgent with validation workflow."""
        
    def get_one_time_search_prompt(self) -> str:
        """System prompt for OneTimeSearchAgent with parameter collection."""
        
    def get_delete_search_prompt(self) -> str:
        """System prompt for DeleteJobSearchAgent with confirmation workflow."""
```

### Button Navigation Structure
```python
# Main menu buttons
MAIN_MENU_BUTTONS = [
    [InlineKeyboardButton("📝 Create Job Search", callback_data="create_search")],
    [InlineKeyboardButton("🔍 One-Time Search", callback_data="one_time_search")],
    [InlineKeyboardButton("📋 List My Searches", callback_data="list_searches")],
    [InlineKeyboardButton("🗑️ Delete Search", callback_data="delete_search")],
    [InlineKeyboardButton("❓ Help", callback_data="help")]
]
```

### Agent Workflow Pattern
```python
class CreateJobSearchAgent:
    def start_creation_workflow(self, user_id: int) -> str:
        """Start the job search creation process."""
        
    def process_user_input(self, message: str, user_id: int, workflow_state: dict) -> str:
        """Process user input in current workflow step."""
        
    def _validate_and_collect_parameters(self, input_data: str, current_step: str) -> dict:
        """Validate input using existing tool validation patterns."""
```

## 🚨 Breaking Changes from Previous Plan

### Complete Architecture Change
- **Previous**: Single agent with modes
- **New**: Separate agents for each operation  

### UI Priority Change  
- **Previous**: Text-first with button enhancement
- **New**: Button-first with text as secondary

### Agent Management Change
- **Previous**: One JobSearchAgent with mode switching
- **New**: Specialized agents managed by factory pattern

### Prompt Management Change
- **Previous**: Embedded prompts in agent class
- **New**: Centralized AgentPromptsManager class

This approach fully meets the user requirements for separate agents, button-first UI, direct database access for read operations, and centralized prompt management while maintaining the existing codebase patterns and validation systems. 