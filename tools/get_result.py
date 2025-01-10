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
    soup = BeautifulSoup(content, 'html.parser')
    return soup

def get_case_error_msg(url):
    
    # Fetch the webpage content
    webpage_content = fetch_webpage(url) 
    if webpage_content:
        # Parse the webpage content
        soup = parse_webpage(webpage_content) 
        # Example: Print the title of the webpage
        title = soup.title.string if soup.title else 'No title found'
        print(f"Title of the webpage: {title}")
        # Search all hidden contents
        hidden_content = soup.find_all('div', class_="failure-summary")
        contains_text = [div for div in hidden_content if 'RHACM4K' in str(div)]
        results = []
        matching_ids = [re.search(r'id="([^"]+)"', str(div)).group(1) for div in contains_text]
        # Find all hidden link contents
        for id_ in matching_ids:     
         real_id = re.sub(r'^test-', '', id_)
         real_id_con = real_id.replace('&amp;quot;', '"')
         error_msg_url = url+"/"+real_id_con+'/summary'
         error_content = fetch_webpage(error_msg_url)
         if error_content:
              error_soup = parse_webpage(error_content)
              error_elements = error_soup.find_all('pre', style='display: ', id=lambda x: x and '-error' in x)
              #print(error_elements)
              for pre_tag in error_elements:
                   error_text = pre_tag.get_text(strip=True)
                   pattern = r'RHACM4K_\d+'
                   match = re.search(pattern, real_id)
                   if match:
                     results.append((match.group(), error_text))
       # print and return results
        for real_id, error_text in results:
            case_id = re.sub(r'_', '-', real_id)
            print(f"\nCase ID: {case_id}\nError Message: \n{error_text}\n")
        return results
