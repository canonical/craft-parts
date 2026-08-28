#!/usr/bin/env bash
#
# find_s390x_failures.sh
#
# Look through GitHub Actions workflow runs for the QA workflow, find runs
# that failed on s390x where at least one other platform succeeded in the same run.
#
# Requires: gh (authenticated), python3
#

set -euo pipefail

usage() {
    cat << 'HELP'
Usage: find_s390x_failures.sh [OPTIONS]

Find GitHub Actions workflow runs where s390x failed but at least one other platform succeeded.

Options:
  -r, --repo REPO          GitHub repository (default: canonical/craft-parts or auto-detected)
  -w, --workflow WORKFLOW  Workflow file or name (default: qa.yaml)
  -n, --limit NUM          Limit number of runs to inspect (default: all)
  -f, --format FORMAT      Output format: table, urls, json, tsv, detailed (default: table)
  -j, --concurrency NUM    Number of concurrent API requests (default: 15)
      --filter-job TEXT    Filter to runs where failed s390x job name contains TEXT (e.g. 'java')
  -o, --output FILE        Write output to file instead of stdout
  -h, --help               Show this help message

Examples:
  ./find_s390x_failures.sh
  ./find_s390x_failures.sh --limit 50 --format table
  ./find_s390x_failures.sh --filter-job java --format urls
  ./find_s390x_failures.sh --format json -o s390x_failures.json
HELP
    exit 0
}

# Default values
REPO=""
WORKFLOW="qa.yaml"
LIMIT=0
FORMAT="table"
CONCURRENCY=15
FILTER_JOB=""
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--repo)
            REPO="$2"
            shift 2
            ;;
        -w|--workflow)
            WORKFLOW="$2"
            shift 2
            ;;
        -n|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -j|--concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        --filter-job)
            FILTER_JOB="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            echo "Use -h or --help for usage." >&2
            exit 1
            ;;
    esac
done

# Ensure gh is available
if ! command -v gh &>/dev/null; then
    echo "Error: 'gh' CLI tool is required but not installed." >&2
    exit 1
fi

# Ensure python3 is available
if ! command -v python3 &>/dev/null; then
    echo "Error: 'python3' is required but not installed." >&2
    exit 1
fi

# Auto-detect repository if not provided
if [[ -z "$REPO" ]]; then
    if git rev-parse --is-inside-work-tree &>/dev/null; then
        REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)
    fi
    if [[ -z "$REPO" ]]; then
        REPO="canonical/craft-parts"
    fi
fi

# Obtain GitHub auth token
GH_TOKEN=$(gh auth token 2>/dev/null || true)
if [[ -z "$GH_TOKEN" ]]; then
    echo "Error: gh CLI is not authenticated. Please run 'gh auth login'." >&2
    exit 1
fi

# Execute embedded Python script for concurrent API queries and analysis
python3 - "$REPO" "$WORKFLOW" "$LIMIT" "$FORMAT" "$CONCURRENCY" "$FILTER_JOB" "$OUTPUT_FILE" "$GH_TOKEN" << 'PYEOF'
import sys
import os
import json
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

repo = sys.argv[1]
workflow = sys.argv[2]
limit = int(sys.argv[3])
fmt = sys.argv[4]
concurrency = int(sys.argv[5])
filter_job = sys.argv[6].lower() if len(sys.argv) > 6 else ""
output_file = sys.argv[7] if len(sys.argv) > 7 else ""
token = sys.argv[8]

def get_headers():
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'craft-parts-s390x-collector'
    }

def fetch_url(url, retries=5):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=get_headers())
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as e:
            if i == retries - 1:
                return None
            time.sleep(1 + i * 2)

# Step 1: Find workflow ID or filename
wf_url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}"
wf_data = fetch_url(wf_url)
if not wf_data:
    # Try searching workflows by name
    all_wf = fetch_url(f"https://api.github.com/repos/{repo}/actions/workflows")
    if all_wf and 'workflows' in all_wf:
        for w in all_wf['workflows']:
            if w['name'].lower() == workflow.lower() or w['path'].endswith(workflow):
                wf_data = w
                break

if not wf_data:
    sys.stderr.write(f"Error: Could not find workflow '{workflow}' in repository '{repo}'.\n")
    sys.exit(1)

wf_id = wf_data['id']
wf_name = wf_data['name']
sys.stderr.write(f"Querying workflow: {wf_name} (ID: {wf_id}) in {repo}...\n")

# Step 2: Fetch runs
runs = []
page = 1
while True:
    per_page = 100
    if limit > 0 and len(runs) + per_page > limit:
        per_page = limit - len(runs)
        
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{wf_id}/runs?per_page={per_page}&page={page}"
    data = fetch_url(url)
    if not data:
        break
    batch = data.get('workflow_runs', [])
    if not batch:
        break
    runs.extend(batch)
    sys.stderr.write(f"Fetched {len(runs)} runs from workflow history...\r")
    if len(batch) < per_page or (limit > 0 and len(runs) >= limit):
        break
    page += 1

sys.stderr.write(f"\nTotal runs fetched: {len(runs)}. Filtering candidate failed/cancelled runs...\n")

candidate_runs = [
    r for r in runs
    if r.get('status') == 'completed' and r.get('conclusion') in ('failure', 'cancelled')
]
sys.stderr.write(f"Inspecting {len(candidate_runs)} candidate runs for s390x failure & other platform success...\n")

def check_run(run):
    run_id = run['id']
    jobs_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    jobs_data = fetch_url(jobs_url)
    if not jobs_data:
        return None
    jobs = jobs_data.get('jobs', [])
    
    failed_s390x_jobs = []
    successful_other_jobs = []
    successful_s390x_jobs = []
    
    for job in jobs:
        name = job.get('name', '')
        conclusion = job.get('conclusion')
        name_lower = name.lower()
        is_s390x = 's390x' in name_lower
        is_platform = any(arch in name_lower for arch in ['ubuntu', 'noble', 'focal', 's390x', 'ppc64el', 'arm', 'amd64'])
        
        if is_s390x:
            if filter_job and filter_job not in name_lower:
                continue
            if conclusion == 'failure':
                failed_s390x_jobs.append(job)
            elif conclusion == 'success':
                successful_s390x_jobs.append(job)
        else:
            if is_platform and conclusion == 'success':
                successful_other_jobs.append(job)

    if failed_s390x_jobs and successful_other_jobs:
        return {
            'run_id': run_id,
            'run_url': run.get('html_url'),
            'display_title': run.get('display_title'),
            'head_branch': run.get('head_branch'),
            'head_sha': run.get('head_sha'),
            'created_at': run.get('created_at'),
            'pr_number': run.get('pull_requests', [{}])[0].get('number') if run.get('pull_requests') else None,
            'failed_s390x_jobs': [{
                'id': j.get('id'),
                'name': j.get('name'),
                'url': j.get('html_url'),
                'conclusion': j.get('conclusion')
            } for j in failed_s390x_jobs],
            'successful_s390x_jobs': [j.get('name') for j in successful_s390x_jobs],
            'successful_other_jobs': [{
                'id': j.get('id'),
                'name': j.get('name'),
                'url': j.get('html_url')
            } for j in successful_other_jobs],
        }
    return None

results = []
processed = 0
with ThreadPoolExecutor(max_workers=concurrency) as executor:
    futures = {executor.submit(check_run, r): r for r in candidate_runs}
    for future in as_completed(futures):
        res = future.result()
        processed += 1
        if processed % 50 == 0 or processed == len(candidate_runs):
            sys.stderr.write(f"Processed {processed}/{len(candidate_runs)} runs (found {len(results)} matches)...\r")
        if res:
            results.append(res)

sys.stderr.write("\nProcessing complete.\n")
results.sort(key=lambda x: x['created_at'], reverse=True)

# Format output
output_text = ""
if fmt == "json":
    output_text = json.dumps(results, indent=2)
elif fmt == "urls":
    lines = [r['run_url'] for r in results]
    output_text = "\n".join(lines)
elif fmt == "tsv":
    lines = ["RunID\tCreatedAt\tPR\tFailedJobs\tRunURL"]
    for r in results:
        pr_str = f"#{r['pr_number']}" if r.get('pr_number') else "-"
        jobs_str = "; ".join([j['name'] for j in r['failed_s390x_jobs']])
        lines.append(f"{r['run_id']}\t{r['created_at']}\t{pr_str}\t{jobs_str}\t{r['run_url']}")
    output_text = "\n".join(lines)
elif fmt == "detailed":
    lines = []
    for r in results:
        pr_str = f" (PR #{r['pr_number']})" if r.get('pr_number') else ""
        lines.append(f"Run ID: {r['run_id']}{pr_str}")
        lines.append(f"Title: {r['display_title']}")
        lines.append(f"Date: {r['created_at']}")
        lines.append(f"Run URL: {r['run_url']}")
        lines.append(f"Failed s390x Jobs ({len(r['failed_s390x_jobs'])}):")
        for j in r['failed_s390x_jobs']:
            lines.append(f"  - {j['name']}")
            lines.append(f"    {j['url']}")
        lines.append(f"Passed Other Platform Jobs ({len(r['successful_other_jobs'])}):")
        for j in r['successful_other_jobs'][:3]:
            lines.append(f"  + {j['name']}")
        if len(r['successful_other_jobs']) > 3:
            lines.append(f"  + ... and {len(r['successful_other_jobs']) - 3} more")
        lines.append("-" * 70)
    output_text = "\n".join(lines)
else: # Table format
    header = f"{'RUN ID':<13} {'DATE':<11} {'PR':<7} {'FAILED S390X JOBS':<45} {'RUN URL'}"
    divider = "-" * len(header)
    lines = [header, divider]
    for r in results:
        pr_str = f"#{r['pr_number']}" if r.get('pr_number') else "-"
        job_names = ", ".join([j['name'].split('/')[0].strip() for j in r['failed_s390x_jobs']])
        if len(job_names) > 42:
            job_names = job_names[:39] + "..."
        date_str = r['created_at'][:10]
        lines.append(f"{r['run_id']:<13} {date_str:<11} {pr_str:<7} {job_names:<45} {r['run_url']}")
    lines.append(f"\nTotal Matching Runs Found: {len(results)}")
    output_text = "\n".join(lines)

if output_file:
    with open(output_file, 'w') as f:
        f.write(output_text + "\n")
    sys.stderr.write(f"Results written to {output_file}\n")
else:
    print(output_text)
PYEOF
chmod +x /home/alex.lowe@canonical.com/Work/Code/craft-parts/find_s390x_failures.sh
