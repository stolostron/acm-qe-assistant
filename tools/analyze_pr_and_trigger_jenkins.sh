#!/bin/bash
################################################################################
# PR Analysis and Jenkins Job Trigger Script
#
# This script analyzes a GitHub PR, selects relevant tests based on tags,
# generates reports, and triggers Jenkins job automatically.
#
# Usage:
#   ./analyze_pr_and_trigger_jenkins.sh <pr_url> <jenkins_params>
#
# Example:
#   ./analyze_pr_and_trigger_jenkins.sh \
#     "https://github.com/stolostron/multicluster-global-hub/pull/2114" \
#     "HUB_CLUSTER_PASSWORD:xxx,HUB_CLUSTER_API_URL:https://api.xxx:6443,TEST_TAGS:auto"
#
# Note: TEST_TAGS:auto will automatically populate with selected tags
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/test-selection"
TEMP_DIR="/tmp/pr-analysis-$$"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
fi

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_header() {
    echo ""
    echo "================================================================================"
    echo "$1"
    echo "================================================================================"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

################################################################################
# Component Detection
################################################################################

detect_component() {
    local repo_name="$1"

    if [[ "$repo_name" =~ "multicluster-global-hub" ]] || [[ "$repo_name" =~ "global-hub" ]]; then
        echo "global-hub"
    elif [[ "$repo_name" =~ "governance" ]] || [[ "$repo_name" =~ "grc" ]]; then
        echo "grc"
    elif [[ "$repo_name" =~ "application" ]]; then
        echo "alc"
    elif [[ "$repo_name" =~ "cluster" ]] || [[ "$repo_name" =~ "lifecycle" ]]; then
        echo "clc"
    else
        echo "unknown"
    fi
}

get_test_repo_url() {
    local component="$1"

    case "$component" in
        global-hub)
            echo "https://github.com/stolostron/acmqe-hoh-e2e.git"
            ;;
        grc)
            echo "https://github.com/stolostron/acmqe-grc-test.git"
            ;;
        alc)
            echo "https://github.com/stolostron/application-ui-test.git"
            ;;
        clc)
            echo "https://github.com/stolostron/clc-ui-e2e.git"
            ;;
        *)
            echo ""
            ;;
    esac
}

################################################################################
# GitHub API Functions
################################################################################

fetch_pr_info() {
    local pr_url="$1"
    local pr_number
    local owner
    local repo

    # Parse PR URL
    if [[ "$pr_url" =~ github\.com/([^/]+)/([^/]+)/pull/([0-9]+) ]]; then
        owner="${BASH_REMATCH[1]}"
        repo="${BASH_REMATCH[2]}"
        pr_number="${BASH_REMATCH[3]}"
    else
        log_error "Invalid GitHub PR URL: $pr_url"
        exit 1
    fi

    print_header "Fetching PR Information"

    local api_url="https://api.github.com/repos/$owner/$repo/pulls/$pr_number"
    local pr_data

    pr_data=$(curl -s "$api_url")

    if [ -z "$pr_data" ]; then
        log_error "Failed to fetch PR data from GitHub API"
        exit 1
    fi

    # Extract PR info
    PR_NUMBER="$pr_number"
    PR_TITLE=$(echo "$pr_data" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('title', ''))")
    PR_AUTHOR=$(echo "$pr_data" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('user', {}).get('login', ''))")
    PR_STATE=$(echo "$pr_data" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('state', ''))")
    PR_BASE=$(echo "$pr_data" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('base', {}).get('ref', ''))")
    PR_HEAD=$(echo "$pr_data" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('head', {}).get('ref', ''))")

    COMPONENT=$(detect_component "$repo")
    REPO_NAME="$owner/$repo"

    log_success "PR #$PR_NUMBER: $PR_TITLE"
    log_info "Repository: $REPO_NAME"
    log_info "Component: $COMPONENT"
    log_info "Author: $PR_AUTHOR"
    log_info "State: $PR_STATE"
    log_info "Base: $PR_BASE ← Head: $PR_HEAD"

    # Fetch changed files
    local files_url="https://api.github.com/repos/$owner/$repo/pulls/$pr_number/files"
    local files_data

    files_data=$(curl -s "$files_url")

    echo "$files_data" > "$TEMP_DIR/changed_files.json"

    local file_count=$(echo "$files_data" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
    log_info "Changed files: $file_count"

    # Save PR info
    cat > "$TEMP_DIR/pr_info.json" <<EOF
{
  "pr_number": $PR_NUMBER,
  "title": "$PR_TITLE",
  "author": "$PR_AUTHOR",
  "repo": "$REPO_NAME",
  "component": "$COMPONENT",
  "state": "$PR_STATE",
  "base": "$PR_BASE",
  "head": "$PR_HEAD",
  "url": "$pr_url"
}
EOF
}

################################################################################
# Tag Mapping Functions
################################################################################

map_files_to_tags() {
    local component="$1"
    local changed_files="$2"

    print_header "Analyzing Changes and Mapping to Tags"

    python3 <<PYEOF
import json
import re

component = "$component"
changed_files_json = """$changed_files"""
files_data = json.loads(changed_files_json)

# Tag mapping rules by component
tag_mappings = {
    'global-hub': {
        r'agent/pkg/status/': ['status', 'migration', 'addon', 'event', 'operand'],
        r'agent/': ['addon', 'migration', 'status'],
        r'operator/': ['operand', 'import', 'create'],
        r'manager/': ['event', 'kafka', 'e2e'],
        r'pkg/database/': ['postgres', 'migration', 'retention'],
        r'pkg/.*kafka': ['kafka', 'event'],
        r'.*\.(tsx?|jsx?)$': ['grafana'],
    },
    'grc': {
        r'.*policy.*': ['policy', 'governance'],
        r'.*compliance.*': ['compliance', 'report'],
        r'.*controller.*': ['controller', 'reconcile'],
    }
}

tags = set()
file_paths = []

for file_info in files_data:
    filename = file_info['filename']
    file_paths.append(filename)

    # Get mappings for component
    mappings = tag_mappings.get(component, {})

    # Match file path to tags
    for pattern, file_tags in mappings.items():
        if re.search(pattern, filename):
            tags.update(file_tags)

print("Changed files:")
for fp in file_paths:
    print(f"  - {fp}")

print(f"\nSelected tags ({len(tags)}):")
for tag in sorted(tags):
    print(f"  ✓ {tag}")

# Save tags
with open('$TEMP_DIR/selected_tags.txt', 'w') as f:
    f.write(' '.join(sorted(tags)))
PYEOF

    SELECTED_TAGS=$(cat "$TEMP_DIR/selected_tags.txt")

    if [ -z "$SELECTED_TAGS" ]; then
        log_warning "No tags mapped from changed files, using default: e2e"
        SELECTED_TAGS="e2e"
    fi
}

################################################################################
# Test Repository and Selection
################################################################################

clone_test_repo() {
    local component="$1"
    local test_repo_url

    test_repo_url=$(get_test_repo_url "$component")

    if [ -z "$test_repo_url" ]; then
        log_error "Unknown component: $component"
        exit 1
    fi

    print_header "Cloning Test Repository"

    log_info "Repository: $test_repo_url"
    log_info "Destination: $TEMP_DIR/test-repo"

    git clone --depth 1 "$test_repo_url" "$TEMP_DIR/test-repo" > /dev/null 2>&1

    log_success "Test repository cloned"
}

extract_tests_by_tags() {
    local tags="$1"

    print_header "Extracting Tests by Tags"

    python3 <<PYEOF
import re
from pathlib import Path

test_repo = Path("$TEMP_DIR/test-repo")
target_tags = "$tags".split()

print(f"Target tags: {', '.join(target_tags)}")

# Find all test files
test_files = list(test_repo.glob("**/*_test.go"))

all_test_cases = []
tag_to_tests = {tag: [] for tag in target_tags}

for test_file in test_files:
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find Describe blocks with Labels
        describe_match = re.search(r'ginkgo\.Describe\("([^"]+)",\s*ginkgo\.Label\(([^)]+)\)', content)
        if not describe_match:
            continue

        suite_name = describe_match.group(1)
        labels_str = describe_match.group(2)
        labels = [l.strip().strip('"').strip("'") for l in labels_str.split(',')]

        # Check if any target tag matches
        matched_tags = [tag for tag in labels if tag in target_tags]
        if not matched_tags:
            continue

        # Extract It() test cases
        it_pattern = r'It\("(RHACM4K-\d+:[^"]+)"'
        it_matches = re.finditer(it_pattern, content)

        rel_path = test_file.relative_to(test_repo)

        for match in it_matches:
            test_name = match.group(1)
            test_info = {
                'name': test_name,
                'suite': suite_name,
                'file': str(rel_path),
                'tags': labels,
                'matched_tags': matched_tags
            }
            all_test_cases.append(test_info)

            # Add to tag groups
            for tag in matched_tags:
                if tag in tag_to_tests:
                    tag_to_tests[tag].append(test_info)
    except Exception:
        pass

print(f"\nTest Selection Results:")
print("="*80)

for tag in target_tags:
    tests = tag_to_tests[tag]
    if tests:
        print(f"\n📌 Tag: {tag} ({len(tests)} test cases)")

print(f"\nTotal selected: {len(all_test_cases)} test cases")

# Save test list
with open('$TEMP_DIR/selected_tests.txt', 'w') as f:
    for test in all_test_cases:
        f.write(f"{test['name']}\n")

# Save count
with open('$TEMP_DIR/test_count.txt', 'w') as f:
    f.write(str(len(all_test_cases)))
PYEOF

    TEST_COUNT=$(cat "$TEMP_DIR/test_count.txt")
    log_success "Selected $TEST_COUNT test cases"
}

################################################################################
# Report Generation
################################################################################

generate_reports() {
    print_header "Generating Reports"

    mkdir -p "$OUTPUT_DIR"

    # Copy test list
    cp "$TEMP_DIR/selected_tests.txt" "$OUTPUT_DIR/pr${PR_NUMBER}_selected_tests.txt"
    log_success "Test list: $OUTPUT_DIR/pr${PR_NUMBER}_selected_tests.txt"

    # Generate simple HTML report
    cat > "$OUTPUT_DIR/pr${PR_NUMBER}_report.html" <<HTMLEOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PR #${PR_NUMBER} Test Selection</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        .info { background: #e3f2fd; padding: 15px; margin: 20px 0; border-radius: 5px; }
        .stats { background: #d4edda; padding: 15px; margin: 20px 0; border-radius: 5px; }
        .tags { background: #fff3cd; padding: 15px; margin: 20px 0; border-radius: 5px; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 PR #${PR_NUMBER} Test Selection Report</h1>

        <div class="info">
            <h3>PR Information</h3>
            <p><strong>Title:</strong> ${PR_TITLE}</p>
            <p><strong>Repository:</strong> ${REPO_NAME}</p>
            <p><strong>Component:</strong> ${COMPONENT}</p>
            <p><strong>Author:</strong> ${PR_AUTHOR}</p>
            <p><strong>State:</strong> ${PR_STATE}</p>
        </div>

        <div class="tags">
            <h3>Selected Tags</h3>
            <p>${SELECTED_TAGS}</p>
        </div>

        <div class="stats">
            <h3>Test Selection</h3>
            <p><strong>Total selected tests:</strong> ${TEST_COUNT}</p>
        </div>

        <h3>Test Cases</h3>
        <pre>$(cat "$TEMP_DIR/selected_tests.txt")</pre>
    </div>
</body>
</html>
HTMLEOF

    log_success "HTML report: $OUTPUT_DIR/pr${PR_NUMBER}_report.html"
}

################################################################################
# Jenkins Trigger
################################################################################

trigger_jenkins() {
    local jenkins_params="$1"

    print_header "Triggering Jenkins Job"

    # Check Jenkins configuration
    if [ -z "$JENKINS_URL" ] || [ -z "$JENKINS_USER" ] || [ -z "$JENKINS_TOKEN" ]; then
        log_error "Jenkins credentials not configured in .env file"
        exit 1
    fi

    # Parse and process parameters
    local processed_params="$jenkins_params"

    # Convert selected tags to Ginkgo format
    local test_tags_ginkgo=$(echo "$SELECTED_TAGS" | tr ' ' '||')

    # Replace TEST_TAGS:auto with actual tags
    processed_params="${processed_params//TEST_TAGS:auto/TEST_TAGS:$test_tags_ginkgo}"

    log_info "Jenkins URL: $JENKINS_URL"
    log_info "Job: globalhub-e2e"
    log_info "Parameters: $processed_params"

    python3 <<PYEOF
import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

jenkins_url = "$JENKINS_URL"
jenkins_user = "$JENKINS_USER"
jenkins_token = "$JENKINS_TOKEN"
job_name = "globalhub-e2e"

# Parse parameters
param_str = "$processed_params"
params = {}
for item in param_str.split(','):
    if ':' in item:
        key, value = item.split(':', 1)
        params[key] = value

# Add PR metadata
params['PR_NUMBER'] = '$PR_NUMBER'
params['PR_TITLE'] = '$PR_TITLE'

print("\nJob parameters:")
for key, value in params.items():
    if 'PASSWORD' in key or 'TOKEN' in key:
        print(f"  {key}: ***")
    else:
        print(f"  {key}: {value}")

# Build job URL
job_url = f"{jenkins_url.rstrip('/')}/view/Global%20Hub/job/{job_name}/buildWithParameters"

# Trigger job
try:
    response = requests.post(
        job_url,
        params=params,
        auth=(jenkins_user, jenkins_token),
        verify=False,
        timeout=30
    )

    if response.status_code in [200, 201]:
        queue_url = response.headers.get('Location', 'N/A')
        print(f"\n{'='*80}")
        print(f"✅ Job triggered successfully!")
        print(f"{'='*80}")
        print(f"Queue URL: {queue_url}")
        print(f"\nMonitor at: {jenkins_url}view/Global%20Hub/job/{job_name}/")

        # Save queue URL
        with open('$TEMP_DIR/queue_url.txt', 'w') as f:
            f.write(queue_url)
    else:
        print(f"\n❌ Failed to trigger job (status: {response.status_code})")
        print(f"Response: {response.text[:500]}")
        exit(1)

except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)
PYEOF

    if [ -f "$TEMP_DIR/queue_url.txt" ]; then
        QUEUE_URL=$(cat "$TEMP_DIR/queue_url.txt")
        log_success "Jenkins job triggered"
    fi
}

################################################################################
# Main Workflow
################################################################################

main() {
    if [ $# -lt 2 ]; then
        echo "Usage: $0 <pr_url> <jenkins_params>"
        echo ""
        echo "Example:"
        echo "  $0 'https://github.com/stolostron/multicluster-global-hub/pull/2114' \\"
        echo "     'HUB_CLUSTER_PASSWORD:xxx,HUB_CLUSTER_API_URL:https://api.xxx:6443,TEST_TAGS:auto'"
        echo ""
        echo "Note: Use TEST_TAGS:auto to automatically populate with selected tags"
        exit 1
    fi

    local pr_url="$1"
    local jenkins_params="$2"

    # Create temp directory
    mkdir -p "$TEMP_DIR"

    print_header "PR Analysis and Jenkins Trigger Workflow"
    echo "PR URL: $pr_url"
    echo ""

    # Step 1: Fetch PR information
    fetch_pr_info "$pr_url"

    # Step 2: Map files to tags
    map_files_to_tags "$COMPONENT" "$(cat "$TEMP_DIR/changed_files.json")"

    # Step 3: Clone test repository
    clone_test_repo "$COMPONENT"

    # Step 4: Extract tests by tags
    extract_tests_by_tags "$SELECTED_TAGS"

    # Step 5: Generate reports
    generate_reports

    # Step 6: Trigger Jenkins
    trigger_jenkins "$jenkins_params"

    print_header "Workflow Completed Successfully"
    log_success "PR #$PR_NUMBER analyzed"
    log_success "$TEST_COUNT tests selected"
    log_success "Jenkins job triggered"
    log_info "Reports saved in: $OUTPUT_DIR"
    echo ""
}

# Run main function
main "$@"