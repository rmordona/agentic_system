# Stage: block

Description:  
Emergency halt stage triggered when governance rules detect violations or conflicts.

Policy Type: Safety Shutdown  
Priority: 999  
Terminal: True  

Required Agents:
- None

Entry Predicates:
- None

Exit Predicates:
- None

Retry Policy:
- Max Retries: 0

Timeout Seconds: 0

Transition Logic:
- ALWAYS ALLOW terminal
