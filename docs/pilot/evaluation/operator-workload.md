# Operator Workload & Triage Capacity Evaluation

## 1. SOC Analyst Capacity Assumptions
For rural ISPs with lean engineering teams, threat detection systems must not introduce excessive operational burden.
- Target Triage Duration: $\le 4.0\text{ minutes}$ per grouped incident.
- Daily Analyst Triage Budget: $\le 20.0\text{ minutes}$ total review time per ISP shift ($5\text{ incidents} \times 4\text{ mins}$).

## 2. Evaluation Findings
Under the 7-day shadow monitoring evaluation:
- Average triage time per incident: $3.8\text{ minutes}$ ($228\text{ seconds}$).
- Daily average analyst triage burden: $14.7\text{ minutes/day}$.
- Peak day triage burden (Day 5 multi-vector burst): $19.5\text{ minutes}$.
- **Conclusion:** The triage burden remains strictly within the $20\text{ min/day}$ budget, making the system viable for single-analyst rural operations centers.
