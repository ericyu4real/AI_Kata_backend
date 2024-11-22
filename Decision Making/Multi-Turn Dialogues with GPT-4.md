# Requirement: Multi-Turn Dialogues with GPT-4

## Status
Declined

## Context
-   **Initial Approach**: Early attempts focused on leveraging GPT-4's capabilities for multi-turn dialogues by providing chat history as `MessagePlaceholder` in the prompts.
-   **Observed Issue**: While GPT-4 could maintain some continuity, it exhibited extreme hallucinations when formulating follow-up questions to clarify the query context.
-   **Explored Alternatives**:
    -   A separate "Intent Agent" was introduced to determine the user's intent and ask follow-up questions for context clarification. However, this approach caused the agent to hallucinate, generating queries that could be answered directly using existing chat history and user input.
    -   The system was later restructured to use a single "Multi-Action Agent," which provided context by including chat history in the system prompt. This agent was more effective but had limitations in specific edge cases.

## Decision
Abandon the use of GPT-4 alone for handling multi-turn dialogues directly.

## Rationale
1.   **Ineffectiveness**: GPT-4 struggles to accurately interpret or follow up based solely on the provided chat history, often hallucinating unnecessary or irrelevant context.
2.   **Complexity**: Separate intent and entity agents created additional operational overhead and failed to address the hallucination problem effectively.
3.   **Performance**: A single Multi-Action Agent showed promise but did not fully eliminate GPT-4's limitations in handling multi-turn dialogues.

## Consequences
Alternative solutions, such as cache mechanism, will need to be explored to ensure robust multi-turn dialogue capabilities.
