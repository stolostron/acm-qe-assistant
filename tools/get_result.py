import re
import requests
from bs4 import BeautifulSoup


def fetch_webpage(url):
    """
    Fetch the content of a webpage.

    :param url: The URL of the webpage to fetch.
    :return: The content of the webpage as a string.
    """
    try:
        # Send a GET request to the specified URL
        response = requests.get(url, verify=False)
        # Check if the request was successful (status code 200)
        response.raise_for_status()
        # Get the content of the webpage
        webpage_content = response.text
        return webpage_content
    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return None


def parse_webpage(content):
    soup = BeautifulSoup(content, "html.parser")
    return soup


def get_error_message(url):
    """
    Retrieves error messages from a given URL and extracts case IDs along with their corresponding error messages.

    Args:
        url (str): The URL of the webpage from which to fetch and extract error messages.

    Returns:
        list: A list of tuples containing case IDs and their associated error messages.
              Each tuple is in the format (error_id, error_text).
    """

    # Fetch the webpage content
    webpage_content = fetch_webpage(url+"/testReport/")
    if webpage_content:
        # Parse the webpage content
        soup = parse_webpage(webpage_content)
        # Example: Print the title of the webpage
        title = soup.title.string if soup.title else "No title found"
        print(f"Title of the webpage: {title}")
        # Search all hidden contents
        hidden_content = soup.find_all("div", class_="failure-summary")
        contains_text = [div for div in hidden_content if "RHACM4K" in str(div)]
        results = []
        matching_ids = [
            re.search(r'id="([^"]+)"', str(div)).group(1) for div in contains_text
        ]
        # Find all hidden link contents
        for id_ in matching_ids:
            real_id = re.sub(r"^test-", "", id_)
            real_id_con = real_id.replace("&amp;quot;", '"')
            error_msg_url = url + "/testReport/" + real_id_con + "/summary"
            error_content = fetch_webpage(error_msg_url)
            if error_content:
                error_soup = parse_webpage(error_content)
                error_elements = error_soup.find_all(
                    "pre", style="display: ", id=lambda x: x and "-error" in x
                )
                if error_elements:
                    for pre_tag in error_elements:
                        error_text = pre_tag.get_text(strip=True)
                        pattern = r"RHACM4K_\d+"
                        match = re.search(pattern, real_id)
                        if match:
                            results.append((match.group(), error_text, real_id_con))
                else:
                    stacktrace_elements = error_soup.find_all(
                        "pre", id=lambda x: x and "-stacktrace" in x
                    )
                    for pre_tag_s in stacktrace_elements:
                        error_text = pre_tag_s.get_text(strip=True)
                        pattern = r"RHACM4K_\d+"
                        match = re.search(pattern, real_id)
                        if match:
                            results.append((match.group(), error_text, real_id_con))
        # print and return results
        final_results = []
        for real_id, error_text, real_id_con in results:
            case_id = re.sub(r"_", "-", real_id)
            index = real_id_con.find(real_id) 
            substring = real_id_con[index + len(real_id):] 
            substring=substring[substring.find("__", substring.find("__") + 2) + 2:]
            substring = substring.replace("_", " ").replace("/", " ")
            title =  " ".join(substring.split())
            final_results.append({
            "ID": case_id,
            "Title": title,
            "Error Message": error_text
        })
            print(f"ID: {case_id}\nTitle: {title}\nError Message: \n{error_text}\n")
        return final_results

def get_failed_case_summary(case_id, failedurl):
    result = [] 
    consoleurl=f"{failedurl}/consoleText"
    webpage_content = fetch_webpage(consoleurl)
    if webpage_content:
        # Parse the webpage content
        #soup = parse_webpage(webpage_content)
    #   failed_tests = soup.find_all('span', style="color: #00CD00;")
    #    content = [span.get_text() for span in failed_tests]
    #    print(content)        
        case_log = []  
        capture = False  

        for line in webpage_content.splitlines():
           if case_id in line:  
              capture = True
           if capture:
              case_log.append(line)
              if line.strip() == "FAILED":  
                 break
    return "\n".join(case_log)


