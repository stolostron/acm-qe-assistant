# Using with Streamlit UI (Alternative Method)

This document describes how to use the QE Assistant with a web-based Streamlit UI interface. This is an alternative method that provides a chat-based web interface.

> **Note**: For most use cases, we recommend using Gemini CLI or Claude Code instead. See [README.md](README.md) for details.

## Prerequisites

1. Python 3.10 or higher
2. VPN required

## Installation Steps

1. Clone the repository:

```bash
git clone https://github.com/stolostron/acm-qe-assistant.git
cd acm-qe-assistant
```

2. Install core dependencies first:

```bash
pip install -r requirements.txt
```

3. Install Streamlit-specific dependencies:

```bash
pip install streamlit==1.41.1 httpx==0.27.2 truststore
```

4. Set up environment variables in `.env` file:

```
POLARION_API="https://polarion.engineering.redhat.com/polarion"
POLARION_PROJECT="RHACM4K"
POLARION_TOKEN="xxx"
```

Or export them directly:

```bash
export POLARION_API="https://polarion.engineering.redhat.com/polarion"
export POLARION_PROJECT="RHACM4K"
export POLARION_TOKEN="xxx"
```

> **Note**: If you use POLARION_USER and POLARION_PASSWORD instead of POLARION_TOKEN, you should have a polarion certificate named "redhatcert.pem" in the directory.

## Running the Application

Start the Streamlit app:

```bash
python -m streamlit run agents/app.py
```

Then open your browser and navigate to the URL shown in the terminal (typically `http://localhost:8501`).

## Usage

In the web UI, you can:

- **Analyze failed cases**: Input a Jenkins job link in the chat
- **Generate automation scripts**: Input a prompt like "generate scripts for RHACM4K-56952" (Polarion case ID)

## When to Use This Method

The Streamlit UI is useful when you:
- Prefer a graphical web interface over CLI
- Want to see the conversation history visually
- Need to share the interface with team members on a local network
- Are exploring the tool's capabilities interactively

For automation workflows and CI/CD integration, Gemini CLI or Claude Code are recommended.
