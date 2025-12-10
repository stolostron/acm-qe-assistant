# acm-qe-assistant

QE Assistant Tool helps to QE's routine works.

## Overview

The QE Assistant Tool is aimed at facilitating QE tasks in RHACM environments, currently, this tool includes two abilities, one is helping to analyse the failed cases to generate the analysis report, another is helping to generate automation scripts following Polarion test cases.

## How to use

### Using with Claude Code (Recommended)

This tool is optimized for Anthropic's Claude Code CLI, providing intelligent automation assistance for QE workflows with custom slash commands. See [CLAUDE.md](CLAUDE.md) for detailed instructions on available capabilities and usage patterns.

#### Prerequisites
1. Python 3.12 or higher
2. VPN required
3. Claude Code CLI installed

#### Quick Start

1. Clone the repository:

```bash
git clone https://github.com/stolostron/acm-qe-assistant.git
cd acm-qe-assistant
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
export POLARION_API="https://polarion.engineering.redhat.com/polarion"
export POLARION_PROJECT="RHACM4K"
export POLARION_TOKEN="xxx"
```

4. Start Claude Code in this directory:

```bash
claude
```

#### Custom Commands

The tool includes two powerful custom slash commands for streamlined workflows:

**1. `/analyze-failed-cases` - Intelligent Failure Analysis**
- Automatically analyzes Jenkins job failures
- Classifies failures as product bugs, automation bugs, or system issues
- Generates detailed HTML analysis reports
- Attempts to fix automation bugs and provides code location
- Supports multiple components: GRC, ALC, CLC, Global Hub, etc.

Usage:
```
/analyze-failed-cases https://your-jenkins-url/job/123
```

**2. `/generate-scripts` - Automation Script Generation**
- Generates automation scripts from Polarion test case IDs
- Leverages existing common functions from component test repositories
- Creates production-ready test scripts following best practices

Usage:
```
/generate-scripts RHACM4K-56952
```

#### Demo

- **Analyze failures**: Input Jenkins job URL or use `/analyze-failed-cases <jenkins-url>`
- **Generate scripts**: Input "generate scripts for RHACM4K-56952" or use `/generate-scripts RHACM4K-56952`

---

### Using with Gemini CLI

This tool is also compatible with Google's Gemini CLI. See [GEMINI.md](GEMINI.md) for detailed instructions on available capabilities and usage patterns when using with Gemini models.

#### Prerequisites
1. Python 3.12 or higher
2. VPN required
3. Gemini CLI installed

#### Steps

1. Clone the repository:

```bash
git clone https://github.com/stolostron/acm-qe-assistant.git
cd acm-qe-assistant
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Make the file named .env with credentials:

```
POLARION_API="https://polarion.engineering.redhat.com/polarion"
POLARION_PROJECT="RHACM4K"
POLARION_TOKEN="xxx"
```

### Demo

- For analyzing failed cases, you just input jenkins job link in the chat.
- For generating scripts, you can input prompt just like “generate scripts for RHACM4K-56952(polation case ID)”

---

## Alternative Methods

### Streamlit Web UI

For users who prefer a web-based chat interface, you can also run the tool with Streamlit UI. See [STREAMLIT.md](STREAMLIT.md) for detailed instructions.

**Note**:
- This method requires additional UI dependencies (streamlit, httpx, truststore)
- These dependencies are included in `requirements.txt` but are optional if you only use Claude Code or Gemini CLI
- For most automation workflows, we recommend using Claude Code or Gemini CLI
