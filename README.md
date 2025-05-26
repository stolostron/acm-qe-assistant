# acm-qe-assistant

QE Assistant Tool helps to QE's routine works.

## Overview 

The QE Assistant Tool is aimed at facilitating QE tasks in RHACM environments, currently, this tool includes two abilities, one is helping to analyse the failed cases to generate the analysis report, another is helping to generate automation scripts following Polarion test cases.

## How to use

### Prerequisites
1. Python 3.10 or higher
2. VPN required
3. You have AI model API token. for example, [Models.corp](https://gitlab.cee.redhat.com/models-corp/user-documentation/-/blob/main/getting-started.md)

### Steps

1. Clone the repository:
 
 ```
 git clone https://github.com/stolostron/acm-qe-assistant.git
 cd acm-qe-assistant
 ```
2. Install dependencies:

```
pip install -r requirements.txt
```
3. Export AI model enviroment variable

```
export API_MODLE="https://granite-3-2-8b-instructxxxx:443/" ---This is located in Models.corp
export API_ID="/data/granite-3.2-8b-instruct"
export API_KEY=="xxxxx"
```
4. Run App

```
python -m streamlit run agents/app.py
```

Then, you will get UI console, you can easily to chat it in this console.

### Demo

- [Generate automation scripts](https://drive.google.com/file/d/1jBSfPllx_QEwB1UDjr3vjssmO_dRKBXE/view?usp=drive_link)


- [Analyse failed cases](https://drive.google.com/file/d/1xm6a0CMnz8d9LcqEORTRJ9IQoR_Qfd9A/view?usp=drive_link)

