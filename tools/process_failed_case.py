import tools.get_result_from_jenkins as get_result_from_jenkins
import sys

if len(sys.argv) > 1:
    urlpath = sys.argv[1]
else:
    urlpath = None
    print("Please provide the jenkins job url")
get_result_from_jenkins.get_error_message(urlpath)
