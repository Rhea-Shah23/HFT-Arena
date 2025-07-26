# High-Frequency Trading in the Latency-Constrained Agent Arena

**Author:** Rhea Shah  
**Affiliation:** University of Illinois at Urbana-Champaign  
**Status:** In Progress  

---

## Project Overview

This project simulates a realistic high-frequency trading (HFT) environment where autonomous agents compete in a latency-sensitive, event-driven order book. Each agent—whether rule-based, reinforcement learning-driven, or hybrid—is constrained by network latency, slippage, and competition. The simulation aims to explore emergent behaviors such as bluffing, market making, latency arbitrage, and spoofing detection, offering a platform to study real-world market microstructure and decision-making under pressure

---

## Key Components

### 1. Matching Engine (Core Market Simulator)

- Simulates a fully functional order book with support for:
  - Limit and market orders
  - Order cancellations
  - Timestamps and event sequencing
- Handles **latency-aware order routing** (agents experience unique network delays)
- Written in Python with optional Cython or Rust modules for speed

### 2. Trading Agents

- **Rule-based agents** (market makers, momentum traders)
- **RL agent** trained on real-time feedback (PnL, latency penalty, risk-adjusted returns)
- **Optional LLM agent** that justifies trades using natural language (OpenAI/Mistral)

### 3. Market Environment

- **Event-driven simulator** (not tick-based), reacts to actual agent submissions
- Simulated noise from passive liquidity, adversarial bots, and market news
- Each agent assigned a unique **latency budget**

### 4. Metrics & Analytics

- Sharpe Ratio, Max Drawdown, Win Rate, Latency vs Return correlation
- Order book and agent behavior visualizations (Plotly, Dash)
- Heatmaps showing trade aggressiveness vs profitability
- Trade logs and market snapshots via Pandas or Polars

---

## Use Cases

- Study of emergent HFT tactics under realistic constraints
- Benchmarking RL algorithms in fast-paced trading environments
- Education and research in market microstructure
- AI-agent tournaments and behavioral modeling

---

## Tech Stack

- Python (core logic and simulation)
- Cython or Rust (matching engine optimization)
- RLlib or custom PPO implementation
- Plotly/Dash for front-end market visualization
- Pandas / Polars for analysis and backtesting
- Optional: OpenAI/Mistral API for LLM-based agents

---

## Project Timeline (12 Weeks)

| Week(s) | Milestone |
|---------|-----------|
| 1–2     | Build matching engine with order types and latency simulation |
| 3–4     | Implement slippage models and validate engine behavior |
| 5–6     | Add rule-based agents (market maker, momentum bot, spoofing bot) |
| 7–8     | Train and evaluate reinforcement learning agent under constraints |
| 9–10    | Build real-time dashboards and agent-vs-agent tournament logic |
| 11–12   | Final documentation, polish, and postmortem blog write-up |

---

## Future Work

- Support for multi-asset simulations and cross-venue arbitrage
- Order flow toxicity analysis
- Adversarial RL training scenarios
- Integration of news sentiment modules
- Full-scale competitions with agent upload and replay support

---

## Citation

```bibtex
@misc{shah2024_hftarena,
  title={High-Frequency Trading in the Latency-Constrained Agent Arena},
  author={Rhea Shah},
  year={2024},
  note={Independent Research Project},
  url={https://github.com/your-repo-link}
}
```

---

## Acknowledgments

Inspired by real-world HFT systems and research in market simulation, autonomous agents, and financial reinforcement learning.

---
