## Smart Test Selection - Analyze GitHub PR and Select Relevant Tests

Automatically select relevant test cases based on GitHub PR code changes, avoiding running the entire test suite.

### 🎯 Core Features

1. **Single PR Analysis** - Analyze one PR and select relevant tests
2. **Batch PR Analysis** - Analyze multiple PRs (same component only), merge test selection
3. **Tag Optimization** - Automatically use common functional tags when multiple tests share them
4. **HTML Reports** - Generate visual test selection reports
5. **Jenkins Integration** - Optional automatic Jenkins job triggering

### 📋 Unified Script

**Use**: `tools/unified_pr_test_selector.py` for all PR analysis

### 🚀 Usage Examples

#### Single PR Analysis
```bash
python tools/unified_pr_test_selector.py \
    --pr "https://github.com/stolostron/multicluster-global-hub/pull/2260"
```

#### Batch PR Analysis (Same Component Only)
```bash
python tools/unified_pr_test_selector.py \
    --prs "https://github.com/stolostron/governance-policy-framework-addon/pull/948" \
          "https://github.com/stolostron/governance-policy-addon-controller/pull/1142"
```

#### Trigger Jenkins Job
```bash
python tools/unified_pr_test_selector.py \
    --pr "..." \
    --trigger \
    --jenkins-params "HUB_CLUSTER_PASSWORD:xxx,TEST_TAGS:auto"
```

### 🔧 Supported Components

| Component | Dev Repo Keywords | Test Repo | Jenkins Job |
|-----------|-------------------|-----------|-------------|
| **Global Hub** | `multicluster-global-hub` | `acmqe-hoh-e2e` | `globalhub-e2e` |
| **GRC** | `governance-policy-*`, `*-policy-controller` | `acmqe-grc-test` | `grc-e2e-test-execution` |
| **ALC** | `application-*` | `application-ui-test` | `alc_e2e_tests` |
| **CLC** | `*cluster*lifecycle*` | `clc-ui-e2e` | `clc-e2e-pipeline` |
| **Search** | `search-*` | `search-e2e-test` | `search_tests` |

### 📊 Workflow

```
1. Fetch PR info (GitHub API)
   ↓
2. Clone test repository (temp dir)
   ↓
3. Extract test tags (scan test files)
   ↓
4. Map files to tags (rule-based)
   ↓
5. Select relevant tests (tag matching)
   ↓
6. Optimize tags (merge common tags)
   ↓
7. Generate HTML report
   ↓
8. Trigger Jenkins (optional)
   ↓
9. Cleanup temp files
```

### 🎨 Tag Optimization

**GRC Component Feature**:
- Each test case has its own number tag (e.g., `@3471` for RHACM4K-3471)
- Also has functional tags (e.g., `@zstream`, `@api`, `@ansible`)

**Smart Optimization Rules**:
- When a functional tag covers ≥5 tests, prefer the functional tag
- Use individual test numbers only for uncovered tests


### 📁 Output Files

- **Single PR**: `test-selection/tag_based_report.html`
- **Batch PRs**: `test-selection/batch_report.html`

Reports include:
- PR info and changed files
- Selected tags and test cases
- Jenkins trigger command
- Efficiency statistics (test count comparison)

### ⚙️ File-to-Tag Mapping Rules

#### Global Hub
- `agent/pkg/status/` → `status, migration, addon, event, operand`
- `manager/` → `event, kafka`
- `pkg/database/` → `postgres, migration, retention`
- `operator/` → `operand, import, create`

#### GRC
- `*crd*.yaml` → `zstream, api` (CRD changes)
- `controllers/*configurationpolicy` → `zstream`
- `controllers/*operatorpolicy` → `operatorpolicy`
- `*ansible*` → `ansible`
- `*gatekeeper*` → `gatekeeper`
- `*rbac*` → `rbac`

#### Search
- `*graphql*`, `*resolver*` → `BVT, SVT`
- `*collector*`, `*informer*` → `BVT`
- `*index*`, `*storage*` → `BVT, SVT`

### 💡 Best Practices

1. **Batch Analysis**: Analyze multiple PRs from the same component together to reduce duplicate tests
2. **Tag Optimization**: GRC component automatically optimizes tags, significantly reducing Jenkins parameter length
3. **View Reports**: Generated HTML reports automatically open in browser
4. **Jenkins Trigger**: Use `TEST_TAGS:auto` to let the script auto-fill selected tags
5. **Temp Files**: Test repo is cloned to temp directory and auto-cleaned after completion

### 🔍 Key Features

✅ **Smart Mapping** - Auto-match relevant test tags based on file paths
✅ **Deduplication** - Batch mode auto-removes duplicate test cases
✅ **Tag Optimization** - GRC component prefers functional tags over individual test numbers
✅ **Visual Reports** - Beautiful HTML reports showing selection results
✅ **Efficiency Stats** - Clear display of saved test time and resources

### 📝 Important Notes

- ⚠️ **Batch Mode**: All PRs must be from the same component
- ⚠️ **Doc Changes**: Pure documentation changes (.md files) won't select any tests
- ⚠️ **Critical Paths**: CRD, API, and other critical changes will select more comprehensive tests
- ⚠️ **Tag Filtering**: Auto-filters generic tags (e.g., `non-ui`, `uitest`, `e2e`)
