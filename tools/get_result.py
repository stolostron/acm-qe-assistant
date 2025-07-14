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
    real_url = re.match(r"(.*?/\d+)(?:/|$)", url).group(0)
    webpage_content = fetch_webpage(real_url+"/testReport/")
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
        error_dict = {}
        for id_ in matching_ids:
            real_id = re.sub(r"^test-", "", id_)
            real_id_con = real_id.replace("&amp;quot;", '"')
            error_msg_url = real_url + "/testReport/" + real_id_con + "/summary"
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
                            key = (match.group(), real_id_con)
                            if key not in error_dict:
                               error_dict[key] = {"error_text": "", "stacktrace_text": ""}
                            error_dict[key]["error_text"] = error_text
                 
               
                stacktrace_elements = error_soup.find_all(
                        "pre", id=lambda x: x and "-stacktrace" in x
                    )
                if stacktrace_elements:
                    for pre_tag in stacktrace_elements:
                        stack_text = pre_tag.get_text(strip=True)
                        pattern = r"RHACM4K_\d+"
                        match = re.search(pattern, real_id)
                        if match:
                            key = (match.group(), real_id_con)
                            if key not in error_dict:
                               error_dict[key] = {"error_text": "", "stacktrace_text": ""}
                            error_dict[key]["stacktrace_text"] = stack_text
        # print and return results
        final_results = []
        #for item in results:
        #  if len(item) == 4:
        #    real_id, error_text, stack_text, real_id_con=item
        #  elif len(item) == 3:
        #    real_id, error_text, real_id_con=item
        #    stack_text = ""
        #  else:
        #    continue
        for (real_id, real_id_con), texts in error_dict.items():  
          case_id = re.sub(r"_", "-", real_id)
          index = real_id_con.find(real_id) 
          substring = real_id_con[index + len(real_id):] 
          substring=substring[substring.find("__", substring.find("__") + 2) + 2:]
          substring = substring.replace("_", " ").replace("/", " ")
          title =  " ".join(substring.split())
          error_text = texts.get("error_text", "")
          stack_text = texts.get("stacktrace_text", "")
          final_results.append({
            "ID": case_id,
            "Title": title,
            "Error Message": error_text,
            "Stacktrace Message": stack_text
        })
          print(f"ID: {case_id}\nTitle: {title}\nError Message: \n{error_text}\nStacktrace Message: \n{stack_text}\n")
    return final_results



if __name__ == "__main__":
   url = "https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/qe-acm-automation-poc/job/grc-e2e-test-execution/2737/console"
   get_error_message(url)


