import get_result
import sys

if len(sys.argv) > 1:
    urlpath = sys.argv[1]
else:
    urlpath = None
    print("Please provide the jenkins job url")
get_result.get_error_message(urlpath)
