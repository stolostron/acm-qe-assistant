#!/usr/bin/env python3
"""
Unified PR Test Selector for ACM Components
============================================

Analyzes single or multiple GitHub PRs and intelligently selects relevant
test cases using tag-based mapping, then triggers Jenkins job.

Features:
- Single PR analysis with tag-based test selection
- Multiple PRs batch analysis (same component only)
- Automatic tag extraction from test repository
- Smart file-to-tag mapping
- Unified or batch test selection
- Jenkins job triggering with custom parameters
- HTML report generation

Usage:
    # Single PR
    python unified_pr_test_selector.py \
        --pr "https://github.com/stolostron/multicluster-global-hub/pull/1234"

    # Multiple PRs (same component)
    python unified_pr_test_selector.py \
        --prs "https://github.com/stolostron/multicluster-global-hub/pull/1234" \
              "https://github.com/stolostron/multicluster-global-hub/pull/1235"

    # With Jenkins trigger
    python unified_pr_test_selector.py \
        --pr "..." \
        --trigger \
        --jenkins-job "folder/job-name" \
        --jenkins-params "HUB_CLUSTER_PASSWORD:xxx,TEST_TAGS:auto"
"""

import argparse
import json
import os
import re
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
import requests
from urllib.parse import quote
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Component to test repository mapping
COMPONENT_TEST_REPOS = {
    'global-hub': {
        'repo_url': 'https://github.com/stolostron/acmqe-hoh-e2e.git',
        'test_patterns': ['**/*_test.go'],
        'jenkins_job': 'globalhub-e2e'
    },
    'grc': {
        'repo_url': 'https://github.com/stolostron/acmqe-grc-test.git',
        'test_patterns': ['**/*.cy.js'],
        'jenkins_job': 'qe-acm-automation-poc/grc-e2e-test-execution'

    },
    'alc': {
        'repo_url': 'https://github.com/stolostron/application-ui-test.git',
        'test_patterns': ['**/*.cy.js'],
        'jenkins_job': 'qe-acm-automation-poc/alc_e2e_tests'
    },
    'clc': {
        'repo_url': 'https://github.com/stolostron/clc-ui-e2e.git',
        'test_patterns': ['**/*.cy.js'],
        'jenkins_job': 'qe-acm-automation-poc/clc-e2e-pipeline'
    },
    'search': {
        'repo_url': 'https://github.com/stolostron/search-e2e-test.git',
        'test_patterns': ['**/*.spec.js'],
        'jenkins_job': 'PICS/CI-Jobs/search_tests'
    }
}

# File path to tag mapping rules
FILE_TO_TAG_MAPPINGS = {
    'global-hub': {
        'path_to_tags': {
            r'agent/pkg/status/': ['status', 'migration', 'addon', 'event', 'operand'],
            r'agent/': ['addon', 'migration', 'status'],
            r'operator/': ['operand', 'import', 'create'],
            r'manager/': ['event', 'kafka'],  # NEVER use e2e tag - it contains all tests
            r'pkg/database/': ['postgres', 'migration', 'retention'],
            r'pkg/.*kafka': ['kafka', 'event'],
            r'.*\.(tsx?|jsx?)$': ['grafana'],
            r'.*\.md$': [],  # Docs only
        },
        'critical_patterns': [
            r'pkg/database/models/',  # Database schema changes
            r'.*migration.*',  # Migration code
            r'operator/.*rbac',  # RBAC changes
            r'operator/.*crd',  # CRD changes
            r'pkg/database/dao/',  # Core database operations
        ],
    },
    'grc': {
        'path_to_tags': {
            # config-policy-controller - Configuration policy enforcement
            r'controllers/.*configurationpolicy': ['zstream'],
            r'controllers/.*operatorpolicy': ['operatorpolicy'],
            r'pkg/.*template': [],
            r'.*_test\.go$': [],  # Unit tests don't trigger e2e tests

            # cert-policy-controller - Certificate policy enforcement
            r'controllers/.*certificatepolicy': ['zstream'],
            r'pkg/.*cert': [],

            # governance-policy-framework - Core framework
            r'api/.*policy.*\.go': ['zstream', 'api'],  # CRD/API changes
            r'controllers/.*': [],
            r'.*crd.*\.yaml': ['zstream', 'api'],  # CRD changes are critical

            # governance-policy-propagator - Policy propagation across clusters
            r'controllers/.*propagator': ['zstream'],
            r'controllers/.*rootpolicystatus': [],
            r'controllers/.*policyset': ['policyset'],

            # governance-policy-framework-addon - Framework addon for managed clusters
            r'controllers/.*addon': [],
            r'pkg/.*addon': [],

            # governance-policy-addon-controller - Addon controller
            r'controllers/.*': [],

            # Ansible integration
            r'.*ansible.*': ['ansible'],
            r'controllers/.*policyautomation': ['ansible'],

            # Gatekeeper integration
            r'.*gatekeeper.*': ['gatekeeper'],
            r'controllers/.*constraint': ['gatekeeper'],

            # RBAC related changes
            r'.*rbac.*': ['rbac'],
            r'.*role.*binding': ['rbac'],

            # UI/Console related changes
            r'.*\.(tsx?|jsx?)$': [],
            r'.*console.*': [],

            # Documentation and non-code changes
            r'.*\.md$': [],  # Docs only
            r'.*test/e2e/.*': [],  # E2E test changes don't trigger more tests
            r'.*\.github/.*': [],  # CI/CD changes
        },
        'critical_patterns': [
            r'api/.*\.go',  # API/CRD changes
            r'.*crd.*\.yaml',  # CRD definitions
            r'controllers/.*/.*_controller\.go',  # Core controller logic
            r'pkg/common/.*',  # Shared/common code
        ],
    },
    'search': {
        'path_to_tags': {
            # search-v2-api - GraphQL API and query processing
            r'.*graphql.*': ['BVT', 'SVT'],
            r'.*resolver.*': ['BVT', 'SVT'],
            r'pkg/.*query': ['BVT'],
            r'pkg/.*search': ['BVT', 'SVT'],

            # search-collector - Resource collection from clusters
            r'.*collector.*': ['BVT'],
            r'.*informer.*': ['BVT'],
            r'pkg/.*transforms': ['BVT'],

            # search-indexer - Indexing and storage
            r'.*index.*': ['BVT', 'SVT'],
            r'.*storage.*': ['BVT'],
            r'pkg/.*model': ['BVT'],

            # search-v2-operator - Operator and deployment
            r'controllers/.*': ['BVT'],
            r'.*crd.*\.yaml': ['BVT', 'SVT'],  # CRD changes are critical

            # API/Integration tests
            r'.*test.*': [],  # Unit tests don't trigger e2e

            # Documentation and non-code changes
            r'.*\.md$': [],  # Docs only
            r'.*\.github/.*': [],  # CI/CD changes
        },
        'critical_patterns': [
            r'.*crd.*\.yaml',  # CRD definitions
            r'.*graphql.*schema',  # GraphQL schema changes
            r'pkg/.*model',  # Data model changes
        ],
    },
}


class PRAnalyzer:
    """Analyzes GitHub Pull Requests"""

    def __init__(self, github_token: str = None):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.headers = {}
        if self.github_token:
            self.headers['Authorization'] = f'token {self.github_token}'

    def parse_pr_url(self, pr_url: str) -> Tuple[str, str, int]:
        """Extract owner, repo, and PR number from PR URL"""
        pattern = r'github\.com/([^/]+)/([^/]+)/pull/(\d+)'
        match = re.search(pattern, pr_url)
        if not match:
            raise ValueError(f"Invalid GitHub PR URL: {pr_url}")
        owner, repo, pr_number = match.groups()
        return owner, repo, int(pr_number)

    def detect_component(self, repo_name: str) -> str:
        """Detect component from repository name"""
        repo_lower = repo_name.lower()

        # Global Hub component
        if 'global-hub' in repo_lower or 'multicluster-global-hub' in repo_lower or 'glo-grafana' in repo_lower:
            return 'global-hub'

        # GRC component - multiple development repositories
        elif any(x in repo_lower for x in [
            'config-policy-controller',
            'governance-policy-framework-addon',
            'governance-policy-framework',
            'governance-policy-propagator',
            'governance-policy-addon-controller',
            'cert-policy-controller',
            'policy',  # generic policy repos
            'gatekeeper'
        ]):
            return 'grc'

        # Search component - multiple development repositories
        elif any(x in repo_lower for x in [
            'search-v2-api',
            'search-collector',
            'search-v2-operator',
            'search-indexer',
            'search'  # generic search repos
        ]):
            return 'search'

        # Application Lifecycle (ALC) component
        elif 'application' in repo_lower:
            return 'alc'

        # Cluster Lifecycle (CLC) component
        elif 'cluster' in repo_lower or 'lifecycle' in repo_lower:
            return 'clc'

        return 'unknown'

    def get_pr_info(self, pr_url: str) -> Dict:
        """Get PR information and changed files"""
        owner, repo, pr_number = self.parse_pr_url(pr_url)

        print(f"\n{'='*80}")
        print(f"📥 Fetching PR #{pr_number}...")
        print(f"{'='*80}")

        # Get PR basic info
        api_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}'
        response = requests.get(api_url, headers=self.headers)
        response.raise_for_status()
        pr_data = response.json()

        # Detect component
        component = self.detect_component(repo)

        print(f"✅ PR #{pr_number}: {pr_data['title']}")
        print(f"   Repository: {owner}/{repo}")
        print(f"   Component: {component}")
        print(f"   Author: {pr_data['user']['login']}")
        print(f"   Files changed: {pr_data['changed_files']}")

        # Get changed files
        files_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files'
        files_response = requests.get(files_url, headers=self.headers)
        files_response.raise_for_status()
        files_data = files_response.json()

        changed_files = []
        for file_info in files_data:
            changed_files.append({
                'filename': file_info['filename'],
                'status': file_info['status'],
                'additions': file_info['additions'],
                'deletions': file_info['deletions'],
            })

        return {
            'pr_number': pr_number,
            'title': pr_data['title'],
            'author': pr_data['user']['login'],
            'repo': f"{owner}/{repo}",
            'component': component,
            'changed_files': changed_files,
            'url': pr_url,
        }


class TestRepository:
    """Manages test repository operations"""

    def __init__(self, component: str, work_dir: str = None):
        self.component = component
        self.work_dir = work_dir or tempfile.mkdtemp(prefix=f'acm-test-{component}-')
        self.repo_path = None

        if component not in COMPONENT_TEST_REPOS:
            raise ValueError(f"Unknown component: {component}")

        self.repo_config = COMPONENT_TEST_REPOS[component]

    def clone(self) -> str:
        """Clone test repository"""
        repo_url = self.repo_config['repo_url']

        print(f"\n{'='*80}")
        print(f"📦 Cloning test repository...")
        print(f"{'='*80}")
        print(f"   Repository: {repo_url}")

        self.repo_path = os.path.join(self.work_dir, self.component + '-tests')

        try:
            cmd = ['git', 'clone', '--depth', '1', repo_url, self.repo_path]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ Repository cloned successfully")
            return self.repo_path
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to clone repository: {e.stderr}")
            raise

    def extract_test_tags(self) -> Dict[str, List[Dict]]:
        """
        Extract all test tags from repository using Ginkgo Label declarations
        Returns: {tag: [test_case_dicts]}
        """
        if not self.repo_path:
            raise RuntimeError("Repository not cloned yet")

        print(f"\n{'='*80}")
        print(f"🔍 Extracting test tags from repository...")
        print(f"{'='*80}")

        from glob import glob

        tag_to_tests = {}
        all_tags = set()

        # Find all test files
        for pattern in self.repo_config['test_patterns']:
            search_pattern = os.path.join(self.repo_path, pattern)
            test_files = glob(search_pattern, recursive=True)

            for test_file in test_files:
                self._extract_tags_from_file(test_file, tag_to_tests, all_tags)

        print(f"✅ Found {len(all_tags)} unique tags with {sum(len(tests) for tests in tag_to_tests.values())} total test cases")
        print(f"   Tags: {', '.join(sorted(all_tags))}")

        return tag_to_tests

    def _extract_tags_from_file(self, file_path: str, tag_to_tests: Dict, all_tags: Set):
        """Extract test tags and cases from a single file (supports Ginkgo, Cypress, and Cypress spec.js)"""
        rel_path = os.path.relpath(file_path, self.repo_path)

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Detect file type
            is_cypress = file_path.endswith('.cy.js')
            is_spec = file_path.endswith('.spec.js')
            is_ginkgo = file_path.endswith('_test.go')

            if is_spec:
                # Search component format: describe('...', { tags: tags.env }, ...)
                # Tags mapping for search component
                tag_mappings = {
                    'tags.env': ['CANARY', 'ROSA'],
                    'tags.modes': ['BVT', 'SVT'],
                    'tags.required': ['REQUIRED'],
                }

                # Find all describe blocks with tags
                describe_pattern = r'describe\s*\(\s*["\']([^"\']+)["\']\s*,\s*\{\s*tags:\s*(tags\.\w+)\s*\}'
                describe_matches = re.finditer(describe_pattern, content)

                for describe_match in describe_matches:
                    suite_name = describe_match.group(1)
                    tag_ref = describe_match.group(2)

                    # Map tag reference to actual tags
                    labels = tag_mappings.get(tag_ref, [])
                    for label in labels:
                        all_tags.add(label)

                    # Extract it() test cases
                    it_pattern = r"it\s*\(\s*['\"]([^'\"]*(?:RHACM4K|P\d|Sev\d)[^'\"]*)['\"]"
                    it_matches = re.finditer(it_pattern, content, re.IGNORECASE)

                    for match in it_matches:
                        test_name = match.group(1)
                        test_info = {
                            'name': test_name,
                            'suite': suite_name,
                            'file': rel_path,
                            'tags': labels,
                        }

                        # Add to each tag's test list
                        for tag in labels:
                            if tag not in tag_to_tests:
                                tag_to_tests[tag] = []
                            tag_to_tests[tag].append(test_info)

            elif is_cypress:
                # Cypress format:
                # describe('test name', { tags: ['@tag1', '@tag2'] }, () => {
                #   it('RHACM4K-xxxxx: test description', { tags: ['@xxxxx'] }, () => {...})
                # })

                # Extract describe block tags
                describe_pattern = r'describe\s*\(\s*["\']([^"\']+)["\']\s*,\s*\{\s*tags:\s*\[([^\]]+)\]\s*\}'
                describe_match = re.search(describe_pattern, content)

                if not describe_match:
                    return

                suite_name = describe_match.group(1)
                tags_str = describe_match.group(2)

                # Parse describe-level tags (remove @ prefix and quotes)
                describe_tags = []
                for tag in re.findall(r"['\"]([^'\"]+)['\"]", tags_str):
                    tag_clean = tag.lstrip('@')
                    if tag_clean:
                        describe_tags.append(tag_clean)
                        all_tags.add(tag_clean)

                # Extract it() test cases with their individual tags
                # Pattern: it('RHACM4K-12345: test description', { tags: ['@12345', '@other'] }, () => {...})
                # or: it('RHACM4K-12345: test description', () => {...})
                it_pattern = r"it\s*\(\s*['\"]([^'\"]*RHACM4K-(\d+)[^'\"]*)['\"](?:\s*,\s*\{\s*tags:\s*\[([^\]]+)\]\s*\})?"
                it_matches = re.finditer(it_pattern, content, re.IGNORECASE)

                for match in it_matches:
                    test_name = match.group(1)
                    test_number = match.group(2)  # Extract the number part (e.g., "12345")
                    it_tags_str = match.group(3)  # Optional it-level tags

                    # Parse it-level tags
                    it_tags = []
                    if it_tags_str:
                        for tag in re.findall(r"['\"]([^'\"]+)['\"]", it_tags_str):
                            tag_clean = tag.lstrip('@')
                            if tag_clean:
                                it_tags.append(tag_clean)
                                all_tags.add(tag_clean)

                    # Combine describe tags and it tags
                    # Filter out generic tags like 'non-ui' and 'uitest'
                    combined_tags = []
                    for tag in describe_tags + it_tags:
                        if tag not in ['non-ui', 'uitest', 'ui']:
                            combined_tags.append(tag)

                    # Always add the test case number as a tag (without @ prefix)
                    if test_number and test_number not in combined_tags:
                        combined_tags.append(test_number)
                        all_tags.add(test_number)

                    test_info = {
                        'name': test_name,
                        'suite': suite_name,
                        'file': rel_path,
                        'tags': combined_tags,
                    }

                    # Add to each tag's test list
                    for tag in combined_tags:
                        if tag not in tag_to_tests:
                            tag_to_tests[tag] = []
                        tag_to_tests[tag].append(test_info)

            elif is_ginkgo:
                # Ginkgo format: ginkgo.Describe("suite name", ginkgo.Label("tag1", "tag2"), ...)
                describe_pattern = r'ginkgo\.Describe\("([^"]+)",\s*ginkgo\.Label\(([^)]+)\)'
                describe_match = re.search(describe_pattern, content)

                if not describe_match:
                    return

                suite_name = describe_match.group(1)
                labels_str = describe_match.group(2)

                # Parse Ginkgo labels
                labels = []
                for label in labels_str.split(','):
                    label = label.strip().strip('"').strip("'")
                    if label:
                        labels.append(label)
                        all_tags.add(label)

                # Extract It() test cases within this suite
                # Pattern: It("RHACM4K-xxxxx: test description", ...)
                it_pattern = r'It\("(RHACM4K-\d+:[^"]+)"'
                it_matches = re.finditer(it_pattern, content)

                for match in it_matches:
                    test_name = match.group(1)
                    test_info = {
                        'name': test_name,
                        'suite': suite_name,
                        'file': rel_path,
                        'tags': labels,
                    }

                    # Add to each tag's test list
                    for tag in labels:
                        if tag not in tag_to_tests:
                            tag_to_tests[tag] = []
                        tag_to_tests[tag].append(test_info)

        except Exception as e:
            print(f"⚠️  Error reading {rel_path}: {e}")

    def cleanup(self):
        """Clean up cloned repository"""
        if self.work_dir and os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir, ignore_errors=True)
            print(f"🗑️  Cleaned up: {self.work_dir}")


class TagBasedSelector:
    """Selects tests based on file-to-tag mapping with priority levels"""

    def __init__(self, component: str):
        self.component = component
        self.mapping_rules = FILE_TO_TAG_MAPPINGS.get(component, {})

    def is_docs_only_change(self, changed_files: List[Dict]) -> bool:
        """Check if all changes are documentation only"""
        if not changed_files:
            return False

        return all(
            f['filename'].endswith('.md') or
            f['filename'].endswith('.txt') or
            'docs/' in f['filename']
            for f in changed_files
        )

    def is_critical_change(self, changed_files: List[Dict]) -> bool:
        """Check if changes are in critical paths"""
        critical_patterns = self.mapping_rules.get('critical_patterns', [])

        for file_info in changed_files:
            filename = file_info['filename']
            for pattern in critical_patterns:
                if re.search(pattern, filename):
                    return True
        return False

    def map_files_to_tags(self, changed_files: List[Dict]) -> Dict:
        """
        Map changed file paths to relevant test tags with priority detection

        Returns:
            Dict with keys: tags (Set[str]), is_critical (bool), is_docs_only (bool)
        """
        print(f"\n{'='*80}")
        print(f"🎯 Mapping changed files to test tags...")
        print(f"{'='*80}")

        # Check special cases first
        is_docs_only = self.is_docs_only_change(changed_files)
        is_critical = self.is_critical_change(changed_files)

        if is_docs_only:
            print(f"📝 Docs-only changes detected - skipping test selection")
            return {
                'tags': set(),
                'is_critical': False,
                'is_docs_only': True,
            }

        if is_critical:
            print(f"⚠️  Critical path changes detected - will run comprehensive tests")

        matched_tags = set()
        path_to_tags = self.mapping_rules.get('path_to_tags', {})

        for file_info in changed_files:
            filename = file_info['filename']
            file_tags = set()

            # Match file path against mapping rules
            for pattern, tags in path_to_tags.items():
                if re.search(pattern, filename):
                    file_tags.update(tags)

            if file_tags:
                matched_tags.update(file_tags)
                print(f"   {filename} → {', '.join(sorted(file_tags))}")
            else:
                print(f"   {filename} → [no tags matched]")

        # IMPORTANT: Never use 'e2e' tag as it contains all test cases
        # Remove e2e tag if accidentally added
        if 'e2e' in matched_tags:
            matched_tags.remove('e2e')
            print(f"⚠️  Removed 'e2e' tag (contains all tests, defeats smart selection)")

        if not matched_tags and not is_docs_only:
            print(f"⚠️  No specific tags matched - PR may need manual review for test selection")

        print(f"\n✅ Selected {len(matched_tags)} tags: {', '.join(sorted(matched_tags))}")

        return {
            'tags': matched_tags,
            'is_critical': is_critical,
            'is_docs_only': is_docs_only,
        }

    def select_tests_by_tags(self, tags: Set[str], tag_to_tests: Dict[str, List[Dict]],
                            is_critical: bool = False) -> Dict[str, List[Dict]]:
        """
        Select tests by tags with priority levels (must_run vs should_run)

        Args:
            tags: Set of selected tags
            tag_to_tests: Mapping of tag to test cases
            is_critical: If True, all tests are must_run

        Returns:
            Dict with keys: must_run (List[Dict]), should_run (List[Dict])
        """
        print(f"\n{'='*80}")
        print(f"📋 Selecting tests by tags...")
        print(f"{'='*80}")

        must_run = []
        should_run = []
        test_names_seen = set()

        for tag in sorted(tags):
            if tag in tag_to_tests:
                tests = tag_to_tests[tag]
                tag_status = "🔥 [CRITICAL]" if is_critical else ""
                print(f"   Tag '{tag}': {len(tests)} test(s) {tag_status}")

                for test in tests:
                    # Avoid duplicates
                    if test['name'] not in test_names_seen:
                        test_names_seen.add(test['name'])
                        test_copy = test.copy()
                        test_copy['matched_tags'] = [tag]
                        test_copy['match_score'] = 0

                        # Determine priority
                        if is_critical:
                            # Critical changes = must_run
                            test_copy['priority'] = 'must_run'
                            test_copy['match_score'] = 10
                            must_run.append(test_copy)
                        elif tag in tags:
                            # Direct tag match = must_run
                            test_copy['priority'] = 'must_run'
                            test_copy['match_score'] = 3
                            must_run.append(test_copy)
                        else:
                            # Indirect match = should_run
                            test_copy['priority'] = 'should_run'
                            test_copy['match_score'] = 1
                            should_run.append(test_copy)
                    else:
                        # Test already selected, update matched_tags and score
                        for existing_test in must_run + should_run:
                            if existing_test['name'] == test['name']:
                                existing_test['matched_tags'].append(tag)
                                existing_test['match_score'] += 1
                                # Promote to must_run if score is high enough
                                if existing_test['match_score'] >= 2 and existing_test in should_run:
                                    should_run.remove(existing_test)
                                    existing_test['priority'] = 'must_run'
                                    must_run.append(existing_test)
                                break
            else:
                print(f"   Tag '{tag}': 0 test(s) [tag not found]")

        print(f"\n✅ Selected tests:")
        print(f"   Must run: {len(must_run)} tests")
        print(f"   Should run: {len(should_run)} tests")
        print(f"   Total: {len(must_run) + len(should_run)} unique test cases")

        return {
            'must_run': must_run,
            'should_run': should_run,
        }


class JenkinsJobTrigger:
    """Triggers Jenkins job with parameters"""

    def __init__(self, jenkins_url: str, jenkins_user: str = None, jenkins_token: str = None):
        self.jenkins_url = jenkins_url.rstrip('/')
        self.jenkins_user = jenkins_user or os.getenv('JENKINS_USER')
        self.jenkins_token = jenkins_token or os.getenv('JENKINS_TOKEN')

        self.auth = None
        if self.jenkins_user and self.jenkins_token:
            self.auth = (self.jenkins_user, self.jenkins_token)

    def trigger_job(self, job_name: str, parameters: Dict = None) -> Dict:
        """Trigger Jenkins job with parameters"""
        print(f"\n{'='*80}")
        print(f"🚀 Triggering Jenkins job...")
        print(f"{'='*80}")

        parameters = parameters or {}

        # Mask sensitive parameters in log
        safe_params = {}
        for key, value in parameters.items():
            if any(s in key.upper() for s in ['PASSWORD', 'TOKEN', 'SECRET']):
                safe_params[key] = '***'
            else:
                safe_params[key] = value

        print(f"   Job: {job_name}")
        print(f"   Parameters: {json.dumps(safe_params, indent=2)}")

        # Build trigger URL - handle nested job paths
        job_path = '/job/'.join(job_name.split('/'))
        trigger_url = f"{self.jenkins_url}/job/{job_path}/buildWithParameters"

        try:
            response = requests.post(
                trigger_url,
                params=parameters,
                auth=self.auth,
                verify=False,
                timeout=30
            )
            response.raise_for_status()

            queue_url = response.headers.get('Location', '')
            print(f"✅ Job triggered successfully")
            print(f"   Queue URL: {queue_url}")

            return {
                'job_name': job_name,
                'queue_url': queue_url,
                'status': 'QUEUED'
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to trigger job: {e}"
            print(f"❌ {error_msg}")
            raise


class ReportGenerator:
    """Generates HTML reports"""

    def _optimize_tags_for_report(self, selected_tests: List[Dict], component: str,
                                  min_tests_per_tag: int = 5) -> str:
        """
        Optimize tags for report by preferring common functional tags over individual test numbers

        Args:
            selected_tests: List of selected test cases
            component: Component name (e.g., 'grc')
            min_tests_per_tag: Minimum number of tests to use a common tag (default: 5)

        Returns:
            Optimized tag string for display (e.g., "@api ||  @zstream")
        """
        if not selected_tests:
            return ''

        # For GRC component: Analyze functional tags vs test numbers
        if component == 'grc':
            # Build mapping: functional_tag -> set of test numbers
            functional_tag_coverage = {}
            test_to_functional_tags = {}  # test_number -> [functional_tags]

            for test in selected_tests:
                # Extract test number
                match = re.search(r'RHACM4K-(\d+)', test['name'])
                if not match:
                    continue

                test_number = match.group(1)

                # Get all tags for this test (both functional and test number)
                all_tags = test.get('tags', [])

                # Separate functional tags from test numbers
                functional_tags = [t for t in all_tags if not t.isdigit()]

                # Record functional tags for this test number
                test_to_functional_tags[test_number] = functional_tags

                # Track which tests each functional tag covers
                for func_tag in functional_tags:
                    if func_tag not in functional_tag_coverage:
                        functional_tag_coverage[func_tag] = set()
                    functional_tag_coverage[func_tag].add(test_number)

            # Find functional tags that cover enough tests
            optimized_tags = set()
            covered_test_numbers = set()

            # Sort by coverage (descending) to prioritize tags that cover more tests
            sorted_functional_tags = sorted(
                functional_tag_coverage.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )

            for func_tag, test_numbers in sorted_functional_tags:
                # Only use this functional tag if it covers enough tests
                if len(test_numbers) >= min_tests_per_tag:
                    # Check how many uncovered tests this tag would cover
                    uncovered_tests = test_numbers - covered_test_numbers

                    # If it covers at least min_tests_per_tag uncovered tests, use it
                    if len(uncovered_tests) >= min_tests_per_tag:
                        optimized_tags.add(func_tag)
                        covered_test_numbers.update(test_numbers)

            # Add individual test numbers for uncovered tests
            all_test_numbers = set(test_to_functional_tags.keys())
            uncovered_test_numbers = all_test_numbers - covered_test_numbers

            for test_num in uncovered_test_numbers:
                optimized_tags.add(test_num)

            # Format tags for display (with @ prefix)
            jenkins_tags = []
            for tag in sorted(optimized_tags, key=lambda x: (x.isdigit(), int(x) if x.isdigit() else 0, x)):
                jenkins_tags.append(f'@{tag}')

            return ' || '.join(jenkins_tags)

        else:
            # For other components: Use tags as-is
            tags = set()
            for test in selected_tests:
                tags.update(test.get('matched_tags', []))
            return ' || '.join(sorted(tags))

    def generate_single_pr_report(self, pr_info: Dict, selected_tags: Set[str],
                                   selected_tests: Dict, total_tags: int,
                                   output_file: str):
        """Generate tag-based report for single PR with priority levels"""

        must_run = selected_tests.get('must_run', [])
        should_run = selected_tests.get('should_run', [])
        all_tests = must_run + should_run

        # For GRC component: Extract test case numbers and group by them
        # For other components: Group by functional tags
        component = pr_info.get('component', '')

        if component == 'grc':
            # Extract test case numbers from test names
            test_case_numbers = set()
            for test in all_tests:
                # Extract number from test name (e.g., "RHACM4K-3471: ..." → "3471")
                match = re.search(r'RHACM4K-(\d+)', test['name'])
                if match:
                    test_case_numbers.add(match.group(1))

            # Group tests by their test case numbers
            tag_groups = {}
            for test in all_tests:
                match = re.search(r'RHACM4K-(\d+)', test['name'])
                if match:
                    test_num = match.group(1)
                    if test_num not in tag_groups:
                        tag_groups[test_num] = []
                    tag_groups[test_num].append(test)

            # Update selected_tags to use test numbers for display
            display_tags = test_case_numbers
        else:
            # Group tests by tags (original behavior)
            tag_groups = {}
            for test in all_tests:
                for tag in test.get('matched_tags', []):
                    if tag not in tag_groups:
                        tag_groups[tag] = []
                    tag_groups[tag].append(test)
            display_tags = selected_tags

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PR #{pr_info['pr_number']} Tag-Based Test Selection</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #1a1a1a; margin-bottom: 10px; }}
        .subtitle {{ color: #666; margin-bottom: 30px; }}
        .pr-card {{ background: white; padding: 25px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .pr-card h2 {{ margin-top: 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .pr-meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 15px; }}
        .pr-meta-item {{ padding: 10px; background: #f8f9fa; border-radius: 5px; }}
        .pr-meta-label {{ font-weight: bold; color: #555; font-size: 0.9em; }}
        .pr-meta-value {{ color: #333; margin-top: 5px; }}

        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .stat-card h3 {{ margin: 0 0 10px 0; font-size: 0.9em; opacity: 0.9; font-weight: normal; }}
        .stat-card .value {{ font-size: 2.5em; font-weight: bold; margin: 0; }}

        .tag-section {{ background: white; padding: 25px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .tag-header {{ display: flex; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e9ecef; }}
        .tag-badge {{ display: inline-block; background: #3498db; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-right: 15px; }}
        .tag-count {{ color: #666; }}

        .test-list {{ margin-top: 15px; }}
        .test-item {{ padding: 12px; margin-bottom: 8px; background: #f8f9fa; border-left: 4px solid #3498db; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 0.9em; }}
        .test-item:hover {{ background: #e9ecef; }}

        .efficiency {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 25px; border-radius: 10px; margin: 20px 0; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .efficiency h3 {{ margin: 0 0 10px 0; }}
        .efficiency .big {{ font-size: 2.5em; font-weight: bold; }}

        .next-steps {{ background: #fff3cd; border: 1px solid #ffc107; padding: 20px; border-radius: 8px; margin-top: 20px; }}
        .next-steps h3 {{ margin-top: 0; color: #856404; }}
        .next-steps ol {{ margin: 10px 0; padding-left: 20px; }}
        .next-steps li {{ margin: 8px 0; color: #856404; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Tag-Based Test Selection Report</h1>
        <p class="subtitle">Intelligent test selection using Ginkgo labels</p>

        <div class="pr-card">
            <h2>📋 Pull Request Information</h2>
            <div class="pr-meta">
                <div class="pr-meta-item">
                    <div class="pr-meta-label">PR Number</div>
                    <div class="pr-meta-value"><a href="{pr_info['url']}" target="_blank">#{pr_info['pr_number']}</a></div>
                </div>
                <div class="pr-meta-item">
                    <div class="pr-meta-label">Title</div>
                    <div class="pr-meta-value">{pr_info['title']}</div>
                </div>
                <div class="pr-meta-item">
                    <div class="pr-meta-label">Repository</div>
                    <div class="pr-meta-value">{pr_info['repo']}</div>
                </div>
                <div class="pr-meta-item">
                    <div class="pr-meta-label">Component</div>
                    <div class="pr-meta-value">{pr_info['component']}</div>
                </div>
                <div class="pr-meta-item">
                    <div class="pr-meta-label">Author</div>
                    <div class="pr-meta-value">{pr_info['author']}</div>
                </div>
                <div class="pr-meta-item">
                    <div class="pr-meta-label">Files Changed</div>
                    <div class="pr-meta-value">{len(pr_info['changed_files'])} file(s)</div>
                </div>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>Total Tags Available</h3>
                <div class="value">{total_tags}</div>
            </div>
            <div class="stat-card">
                <h3>Selected Tags</h3>
                <div class="value">{len(display_tags)}</div>
            </div>
            <div class="stat-card">
                <h3>Selected Tests</h3>
                <div class="value">{len(all_tests)}</div>
            </div>
            <div class="stat-card">
                <h3>Tag Coverage</h3>
                <div class="value">{len(display_tags)/total_tags*100:.0f}%</div>
            </div>
        </div>

        <div class="efficiency">
            <h3>⚡ Smart Selection Efficiency</h3>
            <p class="big">{len(display_tags)} / {total_tags} tags selected</p>
            <p>Running targeted tests instead of full test suite</p>
        </div>

        <h2 style="margin-top: 40px; color: #2c3e50;">📊 Test Cases by {'Test Number' if component == 'grc' else 'Tag'}</h2>
"""

        # Render each tag group (sorted numerically for GRC, alphabetically for others)
        if component == 'grc':
            sorted_tags = sorted(tag_groups.keys(), key=lambda x: int(x) if x.isdigit() else 0)
        else:
            sorted_tags = sorted(tag_groups.keys())

        for tag in sorted_tags:
            tests = tag_groups[tag]
            tag_label = f"@{tag}" if component == 'grc' else tag
            html += f"""
        <div class="tag-section">
            <div class="tag-header">
                <span class="tag-badge">{tag_label}</span>
                <span class="tag-count">{len(tests)} test case(s)</span>
            </div>
            <div class="test-list">
"""
            for test in tests:
                html += f'                <div class="test-item">✓ {test["name"]}</div>\n'

            html += """
            </div>
        </div>
"""

        # Generate Jenkins tags format
        if component == 'grc':
            jenkins_tags = ' || '.join([f'@{t}' for t in sorted(display_tags, key=lambda x: int(x) if x.isdigit() else 0)])
        else:
            jenkins_tags = ' || '.join(sorted(display_tags))

        html += f"""
        <div class="next-steps">
            <h3>📝 Next Steps</h3>
            <ol>
                <li>Review the selected {len(all_tests)} test cases above</li>
                <li>Trigger Jenkins job with selected tags: <code>{jenkins_tags}</code></li>
                <li>Monitor test execution and results</li>
                <li>Update test selection rules if needed</li>
            </ol>
        </div>

        <p style="text-align: center; color: #999; margin-top: 40px; font-size: 0.9em;">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>
"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"📄 Report saved: {output_file}")

    def generate_batch_report(self, prs_info: List[Dict], all_selected_tags: Set[str],
                              all_selected_tests: List[Dict], total_tags: int,
                              output_file: str, component: str = ''):
        """Generate batch report for multiple PRs"""

        # For GRC component: Extract test case numbers
        if component == 'grc':
            # Extract test case numbers from test names
            test_case_numbers = set()
            for test in all_selected_tests:
                match = re.search(r'RHACM4K-(\d+)', test['name'])
                if match:
                    test_case_numbers.add(match.group(1))

            # Group tests by their test case numbers
            tag_groups = {}
            for test in all_selected_tests:
                match = re.search(r'RHACM4K-(\d+)', test['name'])
                if match:
                    test_num = match.group(1)
                    if test_num not in tag_groups:
                        tag_groups[test_num] = []
                    tag_groups[test_num].append(test)

            display_tags = test_case_numbers
        else:
            # Group tests by tag (original behavior)
            tag_groups = {}
            for test in all_selected_tests:
                for tag in test.get('matched_tags', []):
                    if tag not in tag_groups:
                        tag_groups[tag] = []
                    tag_groups[tag].append(test)
            display_tags = all_selected_tags

        # Calculate per-PR stats
        pr_stats = []
        for pr_info in prs_info:
            # For GRC, extract test numbers from the PR's selected tests
            if component == 'grc':
                pr_test_numbers = set()
                for test_group in pr_info.get('selected_tests', {}).values():
                    for test in test_group:
                        match = re.search(r'RHACM4K-(\d+)', test['name'])
                        if match:
                            pr_test_numbers.add(match.group(1))
                pr_tags = pr_test_numbers
            else:
                pr_tags = pr_info.get('selected_tags', set())

            pr_stats.append({
                'pr_number': pr_info['pr_number'],
                'title': pr_info['title'],
                'author': pr_info['author'],
                'url': pr_info['url'],
                'tags': pr_tags,
                'test_count': len(pr_info.get('selected_tests', {}).get('must_run', [])) +
                             len(pr_info.get('selected_tests', {}).get('should_run', []))
            })

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Batch PR Test Selection Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #1a1a1a; margin-bottom: 10px; }}
        .subtitle {{ color: #666; margin-bottom: 30px; }}

        .summary-card {{ background: white; padding: 25px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .summary-card h2 {{ margin-top: 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}

        .pr-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .pr-table th {{ background: #f8f9fa; padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6; font-weight: 600; }}
        .pr-table td {{ padding: 12px; border-bottom: 1px solid #dee2e6; }}
        .pr-table tr:hover {{ background: #f8f9fa; }}
        .pr-link {{ color: #3498db; text-decoration: none; }}
        .pr-link:hover {{ text-decoration: underline; }}
        .tag-list {{ font-size: 0.85em; color: #666; }}

        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .stat-card h3 {{ margin: 0 0 10px 0; font-size: 0.9em; opacity: 0.9; font-weight: normal; }}
        .stat-card .value {{ font-size: 2.5em; font-weight: bold; margin: 0; }}

        .tag-section {{ background: white; padding: 25px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .tag-header {{ display: flex; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e9ecef; }}
        .tag-badge {{ display: inline-block; background: #3498db; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-right: 15px; }}
        .tag-count {{ color: #666; }}

        .test-list {{ margin-top: 15px; }}
        .test-item {{ padding: 12px; margin-bottom: 8px; background: #f8f9fa; border-left: 4px solid #3498db; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 0.9em; }}
        .test-item:hover {{ background: #e9ecef; }}

        .efficiency {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 25px; border-radius: 10px; margin: 20px 0; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .efficiency h3 {{ margin: 0 0 10px 0; }}
        .efficiency .big {{ font-size: 2.5em; font-weight: bold; }}

        .next-steps {{ background: #fff3cd; border: 1px solid #ffc107; padding: 20px; border-radius: 8px; margin-top: 20px; }}
        .next-steps h3 {{ margin-top: 0; color: #856404; }}
        .next-steps ol {{ margin: 10px 0; padding-left: 20px; }}
        .next-steps li {{ margin: 8px 0; color: #856404; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Batch PR Test Selection Report</h1>
        <p class="subtitle">Combined test selection from multiple pull requests</p>

        <div class="summary-card">
            <h2>📋 Pull Requests Analyzed</h2>
            <table class="pr-table">
                <thead>
                    <tr>
                        <th>PR #</th>
                        <th>Title</th>
                        <th>Author</th>
                        <th>Selected Tags</th>
                        <th>Tests</th>
                    </tr>
                </thead>
                <tbody>
"""

        for pr_stat in pr_stats:
            # For GRC, add @ prefix to tag numbers
            if component == 'grc' and pr_stat['tags']:
                tags_str = ', '.join([f"@{t}" for t in sorted(pr_stat['tags'], key=lambda x: int(x) if x.isdigit() else 0)])
            else:
                tags_str = ', '.join(sorted(pr_stat['tags'])) if pr_stat['tags'] else 'None'

            html += f"""
                    <tr>
                        <td><a href="{pr_stat['url']}" class="pr-link" target="_blank">#{pr_stat['pr_number']}</a></td>
                        <td>{pr_stat['title']}</td>
                        <td>{pr_stat['author']}</td>
                        <td class="tag-list">{tags_str}</td>
                        <td>{pr_stat['test_count']}</td>
                    </tr>
"""

        html += f"""
                </tbody>
            </table>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>PRs Analyzed</h3>
                <div class="value">{len(prs_info)}</div>
            </div>
            <div class="stat-card">
                <h3>Total Tags</h3>
                <div class="value">{len(display_tags)}</div>
            </div>
            <div class="stat-card">
                <h3>Combined Tests</h3>
                <div class="value">{len(all_selected_tests)}</div>
            </div>
            <div class="stat-card">
                <h3>Tag Coverage</h3>
                <div class="value">{len(display_tags)/total_tags*100:.0f}%</div>
            </div>
        </div>

        <div class="efficiency">
            <h3>⚡ Batch Processing Efficiency</h3>
            <p class="big">{len(prs_info)} PRs → {len(all_selected_tests)} tests</p>
            <p>Unified test execution for multiple changes</p>
        </div>

        <h2 style="margin-top: 40px; color: #2c3e50;">📊 Combined Test Cases by {'Test Number' if component == 'grc' else 'Tag'}</h2>
"""

        # Render each tag group (sorted numerically for GRC, alphabetically for others)
        if component == 'grc':
            sorted_tags = sorted(tag_groups.keys(), key=lambda x: int(x) if x.isdigit() else 0)
        else:
            sorted_tags = sorted(tag_groups.keys())

        for tag in sorted_tags:
            tests = tag_groups[tag]
            # Remove duplicates
            unique_tests = list({test['name']: test for test in tests}.values())
            tag_label = f"@{tag}" if component == 'grc' else tag

            html += f"""
        <div class="tag-section">
            <div class="tag-header">
                <span class="tag-badge">{tag_label}</span>
                <span class="tag-count">{len(unique_tests)} test case(s)</span>
            </div>
            <div class="test-list">
"""
            for test in unique_tests:
                html += f'                <div class="test-item">✓ {test["name"]}</div>\n'

            html += """
            </div>
        </div>
"""

        # Generate optimized Jenkins tags format
        if component == 'grc' and all_selected_tests:
            # Use tag optimization for GRC
            jenkins_tags = self._optimize_tags_for_report(all_selected_tests, component)
        elif component == 'grc':
            jenkins_tags = ' || '.join([f'@{t}' for t in sorted(display_tags, key=lambda x: int(x) if x.isdigit() else 0)])
        else:
            jenkins_tags = ' || '.join(sorted(display_tags))

        html += f"""
        <div class="next-steps">
            <h3>📝 Next Steps</h3>
            <ol>
                <li>Review the combined {len(all_selected_tests)} test cases from {len(prs_info)} PRs</li>
                <li>Trigger single Jenkins job with tags: <code>{jenkins_tags}</code></li>
                <li>Monitor test execution for all PRs</li>
                <li>Report results back to each PR</li>
            </ol>
        </div>

        <p style="text-align: center; color: #999; margin-top: 40px; font-size: 0.9em;">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>
"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"📄 Report saved: {output_file}")


class UnifiedPRTestSelector:
    """Main orchestrator for single or multiple PR analysis"""

    def __init__(self, github_token: str = None, jenkins_url: str = None):
        self.pr_analyzer = PRAnalyzer(github_token)
        self.jenkins_url = jenkins_url or os.getenv('JENKINS_URL')

    def run_single_pr(self, pr_url: str, trigger_jenkins: bool = False,
                      jenkins_job: str = None, jenkins_params: str = None,
                      output_dir: str = None) -> Dict:
        """
        Analyze single PR and select tests

        Args:
            pr_url: GitHub PR URL
            trigger_jenkins: Whether to trigger Jenkins
            jenkins_job: Jenkins job name (optional, uses default if not specified)
            jenkins_params: Jenkins parameters as "KEY:VALUE,KEY2:VALUE2"
            output_dir: Output directory

        Returns:
            Results dictionary
        """
        print(f"\n{'='*80}")
        print(f"🎯 SINGLE PR ANALYSIS MODE")
        print(f"{'='*80}")

        # Step 1: Analyze PR
        pr_info = self.pr_analyzer.get_pr_info(pr_url)
        component = pr_info['component']

        if component == 'unknown':
            raise ValueError(f"Could not detect component from repository: {pr_info['repo']}")

        # Step 2: Clone test repository and extract tags
        test_repo = TestRepository(component)
        try:
            test_repo.clone()
            tag_to_tests = test_repo.extract_test_tags()

            # Step 3: Map changed files to tags
            selector = TagBasedSelector(component)
            tag_result = selector.map_files_to_tags(pr_info['changed_files'])

            # Handle docs-only changes
            if tag_result['is_docs_only']:
                print(f"\n📝 Docs-only PR - no tests selected")
                return {
                    'mode': 'single',
                    'pr_info': pr_info,
                    'selected_tags': set(),
                    'selected_tests': {'must_run': [], 'should_run': []},
                    'total_tags': len(tag_to_tests),
                    'is_docs_only': True,
                }

            selected_tags = tag_result['tags']
            is_critical = tag_result['is_critical']

            # Step 4: Select tests by tags
            selected_tests = selector.select_tests_by_tags(selected_tags, tag_to_tests, is_critical)

            # Step 5: Generate report
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

                report_file = os.path.join(output_dir, 'tag_based_report.html')
                reporter = ReportGenerator()
                reporter.generate_single_pr_report(
                    pr_info, selected_tags, selected_tests,
                    len(tag_to_tests), report_file
                )

            # Step 6: Trigger Jenkins (optional)
            if trigger_jenkins:
                all_tests = selected_tests.get('must_run', []) + selected_tests.get('should_run', [])
                self._trigger_jenkins_job(
                    component, jenkins_job, jenkins_params,
                    selected_tags, pr_info, False, 1, all_tests
                )

            return {
                'mode': 'single',
                'pr_info': pr_info,
                'selected_tags': selected_tags,
                'selected_tests': selected_tests,
                'total_tags': len(tag_to_tests),
            }

        finally:
            test_repo.cleanup()

    def run_multiple_prs(self, pr_urls: List[str], trigger_jenkins: bool = False,
                         jenkins_job: str = None, jenkins_params: str = None,
                         output_dir: str = None) -> Dict:
        """
        Analyze multiple PRs and combine test selection

        Args:
            pr_urls: List of GitHub PR URLs (must be same component)
            trigger_jenkins: Whether to trigger Jenkins
            jenkins_job: Jenkins job name
            jenkins_params: Jenkins parameters
            output_dir: Output directory

        Returns:
            Results dictionary
        """
        print(f"\n{'='*80}")
        print(f"🎯 MULTIPLE PRs BATCH ANALYSIS MODE")
        print(f"{'='*80}")
        print(f"Analyzing {len(pr_urls)} PRs")

        # Step 1: Analyze all PRs
        prs_info = []
        components = set()

        for pr_url in pr_urls:
            pr_info = self.pr_analyzer.get_pr_info(pr_url)
            prs_info.append(pr_info)
            components.add(pr_info['component'])

        # Step 2: Validate same component
        if len(components) > 1:
            raise ValueError(
                f"PRs are from different components: {components}. "
                f"Please group by component and run separately."
            )

        if 'unknown' in components:
            raise ValueError("Could not detect component from one or more repositories")

        component = components.pop()

        print(f"\n✅ All PRs are from component: {component}")

        # Step 3: Clone test repository once
        test_repo = TestRepository(component)
        try:
            test_repo.clone()
            tag_to_tests = test_repo.extract_test_tags()

            # Step 4: Analyze each PR and collect tags/tests
            selector = TagBasedSelector(component)
            all_selected_tags = set()
            all_selected_tests = []
            test_names_seen = set()

            all_must_run = []
            all_should_run = []
            is_any_critical = False

            for pr_info in prs_info:
                # Map files to tags
                tag_result = selector.map_files_to_tags(pr_info['changed_files'])

                # Skip docs-only PRs
                if tag_result['is_docs_only']:
                    pr_info['selected_tags'] = set()
                    pr_info['selected_tests'] = {'must_run': [], 'should_run': []}
                    pr_info['is_docs_only'] = True
                    continue

                pr_tags = tag_result['tags']
                is_critical = tag_result['is_critical']
                is_any_critical = is_any_critical or is_critical

                all_selected_tags.update(pr_tags)

                # Select tests
                pr_tests_result = selector.select_tests_by_tags(pr_tags, tag_to_tests, is_critical)

                # Store in pr_info
                pr_info['selected_tags'] = pr_tags
                pr_info['selected_tests'] = pr_tests_result
                pr_info['is_critical'] = is_critical

                # Merge into all_selected_tests (avoiding duplicates)
                for test in pr_tests_result['must_run']:
                    if test['name'] not in test_names_seen:
                        test_names_seen.add(test['name'])
                        all_must_run.append(test)

                for test in pr_tests_result['should_run']:
                    if test['name'] not in test_names_seen:
                        test_names_seen.add(test['name'])
                        all_should_run.append(test)

            all_selected_tests = all_must_run + all_should_run

            # Step 5: Generate batch report
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

                report_file = os.path.join(output_dir, 'batch_report.html')
                reporter = ReportGenerator()
                reporter.generate_batch_report(
                    prs_info, all_selected_tags, all_selected_tests,
                    len(tag_to_tests), report_file, component
                )

            # Step 6: Trigger Jenkins once (optional)
            if trigger_jenkins:
                # Use first PR info for metadata
                self._trigger_jenkins_job(
                    component, jenkins_job, jenkins_params,
                    all_selected_tags, prs_info[0],
                    batch_mode=True, pr_count=len(prs_info),
                    selected_tests=all_selected_tests
                )

            return {
                'mode': 'batch',
                'prs_info': prs_info,
                'component': component,
                'all_selected_tags': all_selected_tags,
                'all_selected_tests': all_selected_tests,
                'total_tags': len(tag_to_tests),
            }

        finally:
            test_repo.cleanup()

    def _optimize_tags_for_jenkins(self, selected_tests: List[Dict], component: str,
                                   min_tests_per_tag: int = 5) -> str:
        """
        Optimize tags for Jenkins by preferring common functional tags over individual test numbers

        Args:
            selected_tests: List of selected test cases
            component: Component name (e.g., 'grc')
            min_tests_per_tag: Minimum number of tests to use a common tag (default: 5)

        Returns:
            Optimized tag string for Jenkins (e.g., "@zstream || @3471 || @3472")
        """
        if not selected_tests:
            return ''

        print(f"\n{'='*80}")
        print(f"🎯 Optimizing tags for Jenkins...")
        print(f"{'='*80}")

        # For GRC component: Analyze functional tags vs test numbers
        if component == 'grc':
            # Build mapping: functional_tag -> set of test numbers
            functional_tag_coverage = {}
            test_to_functional_tags = {}  # test_number -> [functional_tags]

            for test in selected_tests:
                # Extract test number
                match = re.search(r'RHACM4K-(\d+)', test['name'])
                if not match:
                    continue

                test_number = match.group(1)

                # Get all tags for this test (both functional and test number)
                all_tags = test.get('tags', [])

                # Separate functional tags from test numbers
                functional_tags = [t for t in all_tags if not t.isdigit()]

                # Record functional tags for this test number
                test_to_functional_tags[test_number] = functional_tags

                # Track which tests each functional tag covers
                for func_tag in functional_tags:
                    if func_tag not in functional_tag_coverage:
                        functional_tag_coverage[func_tag] = set()
                    functional_tag_coverage[func_tag].add(test_number)

            # Find functional tags that cover enough tests
            optimized_tags = set()
            covered_test_numbers = set()

            # Sort by coverage (descending) to prioritize tags that cover more tests
            sorted_functional_tags = sorted(
                functional_tag_coverage.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )

            for func_tag, test_numbers in sorted_functional_tags:
                # Only use this functional tag if it covers enough tests
                if len(test_numbers) >= min_tests_per_tag:
                    # Check how many uncovered tests this tag would cover
                    uncovered_tests = test_numbers - covered_test_numbers

                    # If it covers at least min_tests_per_tag uncovered tests, use it
                    if len(uncovered_tests) >= min_tests_per_tag:
                        optimized_tags.add(func_tag)
                        covered_test_numbers.update(test_numbers)
                        print(f"   ✅ Using functional tag '{func_tag}' (covers {len(test_numbers)} tests)")

            # Add individual test numbers for uncovered tests
            all_test_numbers = set(test_to_functional_tags.keys())
            uncovered_test_numbers = all_test_numbers - covered_test_numbers

            if uncovered_test_numbers:
                print(f"   📋 Using individual test numbers for {len(uncovered_test_numbers)} uncovered tests")
                for test_num in uncovered_test_numbers:
                    optimized_tags.add(test_num)

            # Format tags for Jenkins (with @ prefix for test numbers)
            jenkins_tags = []
            for tag in sorted(optimized_tags, key=lambda x: (x.isdigit(), int(x) if x.isdigit() else 0, x)):
                if tag.isdigit():
                    jenkins_tags.append(f'@{tag}')
                else:
                    jenkins_tags.append(f'@{tag}')

            result = '||'.join(jenkins_tags)

            print(f"\n✅ Optimized tags summary:")
            print(f"   Total tests: {len(all_test_numbers)}")
            print(f"   Functional tags used: {len([t for t in optimized_tags if not t.isdigit()])}")
            print(f"   Individual test numbers: {len(uncovered_test_numbers)}")
            print(f"   Final tag count: {len(optimized_tags)} (vs {len(all_test_numbers)} without optimization)")

            return result

        else:
            # For other components: Use tags as-is
            tags = set()
            for test in selected_tests:
                tags.update(test.get('matched_tags', []))
            return '||'.join(sorted(tags))

    def _trigger_jenkins_job(self, component: str, jenkins_job: str = None,
                            jenkins_params: str = None, selected_tags: Set[str] = None,
                            pr_info: Dict = None, batch_mode: bool = False,
                            pr_count: int = 1, selected_tests: List[Dict] = None):
        """Trigger Jenkins job with parameters"""

        if not self.jenkins_url:
            print("⚠️  Jenkins URL not configured, skipping trigger")
            return

        # Use default job name if not specified
        if not jenkins_job:
            jenkins_job = COMPONENT_TEST_REPOS[component]['jenkins_job']

        # Parse custom parameters
        parameters = {}
        if jenkins_params:
            for param in jenkins_params.split(','):
                if ':' in param:
                    key, value = param.split(':', 1)
                    parameters[key.strip()] = value.strip()

        # Optimize tags for Jenkins (prefer common functional tags over individual test numbers)
        if component == 'grc' and selected_tests:
            tags_ginkgo = self._optimize_tags_for_jenkins(selected_tests, component)
        elif selected_tags:
            # Convert tags to Ginkgo format (other components)
            # NEVER use e2e tag as default - it runs ALL tests
            tags_ginkgo = '||'.join(sorted(selected_tags))
        else:
            tags_ginkgo = ''

        # For global-hub, only set TEST_TAGS parameter
        if component == 'global-hub':
            parameters = {'TEST_TAGS': tags_ginkgo}
        else:
            # Replace TEST_TAGS:auto with actual tags for other components
            if 'TEST_TAGS' in parameters and parameters['TEST_TAGS'] == 'auto':
                parameters['TEST_TAGS'] = tags_ginkgo

            # Add PR metadata for other components
            if pr_info:
                parameters['PR_NUMBER'] = str(pr_info['pr_number'])
                parameters['PR_TITLE'] = pr_info['title']

            if batch_mode:
                parameters['BATCH_MODE'] = 'true'
                parameters['PR_COUNT'] = str(pr_count)

        # Trigger job
        jenkins = JenkinsJobTrigger(self.jenkins_url)
        jenkins.trigger_job(jenkins_job, parameters)


def main():
    parser = argparse.ArgumentParser(
        description='Unified PR Test Selector - Single or Multiple PRs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single PR analysis
  %(prog)s --pr "https://github.com/stolostron/multicluster-global-hub/pull/1234"

  # Multiple PRs batch analysis
  %(prog)s --prs "https://github.com/.../pull/1234" "https://github.com/.../pull/1235"

  # With Jenkins trigger
  %(prog)s --pr "..." --trigger --jenkins-params "HUB_PASSWORD:xxx,TEST_TAGS:auto"
        """
    )

    # PR input (mutually exclusive: either --pr or --prs)
    pr_group = parser.add_mutually_exclusive_group(required=True)
    pr_group.add_argument('--pr', help='Single GitHub PR URL')
    pr_group.add_argument('--prs', nargs='+', help='Multiple GitHub PR URLs (same component)')

    # Jenkins options
    parser.add_argument('--trigger', action='store_true', help='Trigger Jenkins job')
    parser.add_argument('--jenkins-url', help='Jenkins URL')
    parser.add_argument('--jenkins-job', help='Jenkins job name (uses default if not specified)')
    parser.add_argument('--jenkins-params', help='Jenkins parameters (KEY:VALUE,KEY2:VALUE2)')

    # Other options
    parser.add_argument('--output', help='Output directory', default='./test-selection')
    parser.add_argument('--github-token', help='GitHub API token')

    args = parser.parse_args()

    try:
        selector = UnifiedPRTestSelector(
            github_token=args.github_token,
            jenkins_url=args.jenkins_url
        )

        if args.pr:
            # Single PR mode
            result = selector.run_single_pr(
                pr_url=args.pr,
                trigger_jenkins=args.trigger,
                jenkins_job=args.jenkins_job,
                jenkins_params=args.jenkins_params,
                output_dir=args.output
            )

            print(f"\n{'='*80}")
            print(f"✅ SINGLE PR ANALYSIS COMPLETED")
            print(f"{'='*80}")
            print(f"PR: #{result['pr_info']['pr_number']}")
            print(f"Component: {result['pr_info']['component']}")
            print(f"Selected tags: {', '.join(sorted(result['selected_tags']))}")
            print(f"Selected tests: {len(result['selected_tests'])}")
            print(f"Tag coverage: {len(result['selected_tags'])}/{result['total_tags']}")

        else:
            # Multiple PRs mode
            result = selector.run_multiple_prs(
                pr_urls=args.prs,
                trigger_jenkins=args.trigger,
                jenkins_job=args.jenkins_job,
                jenkins_params=args.jenkins_params,
                output_dir=args.output
            )

            print(f"\n{'='*80}")
            print(f"✅ BATCH PR ANALYSIS COMPLETED")
            print(f"{'='*80}")
            print(f"PRs analyzed: {len(result['prs_info'])}")
            print(f"Component: {result['component']}")
            print(f"Combined tags: {', '.join(sorted(result['all_selected_tags']))}")
            print(f"Combined tests: {len(result['all_selected_tests'])}")
            print(f"Tag coverage: {len(result['all_selected_tags'])}/{result['total_tags']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
