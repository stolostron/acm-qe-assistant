import webbrowser
import os
import argparse
import json

# --- Main execution ---
def main():
    parser = argparse.ArgumentParser(description='Generate an HTML report for failed test cases.')
    parser.add_argument('--data', type=str, required=True, help='A JSON string of the failed cases data.')
    args = parser.parse_args()

    try:
        failed_cases = json.loads(args.data)
    except json.JSONDecodeError:
        print("Error: Invalid JSON data provided.")
        return

    # HTML template
    html_content = """
    <html>
    <head>
    <title>Test Failure Analysis Report</title>
    <style>
      body { font-family: sans-serif; }
      table { border-collapse: collapse; width: 100%; }
      th, td { border: 1px solid #dddddd; text-align: left; padding: 8px; }
      th { background-color: #f2f2f2; }
    </style>
    </head>
    <body>

    <h2>Test Failure Analysis Report</h2>

    <table>
      <tr>
        <th>ID</th>
        <th>Title</th>
        <th>Error Message</th>
        <th>Analysis</th>
      </tr>
    """

    # Populate the table with data
    for case in failed_cases:
        html_content += f"""
      <tr>
        <td>{case.get('ID', 'N/A')}</td>
        <td>{case.get('Title', 'N/A')}</td>
        <td>{case.get('Error Message', 'N/A')}</td>
        <td>{case.get('Analysis', 'N/A')}</td>
      </tr>
    """

    # Close the HTML tags
    html_content += """
    </table>

    </body>
    </html>
    """

    # Write the HTML content to a file
    file_path = "failure_analysis_report.html"
    with open(file_path, "w") as f:
        f.write(html_content)

    # Open the HTML file in a web browser
    webbrowser.open('file://' + os.path.realpath(file_path))

if __name__ == "__main__":
    main()
