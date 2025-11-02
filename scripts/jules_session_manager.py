import os
import requests

# 1. Configuration from CI environment variables
JULES_API_KEY = os.getenv("JULES_API_KEY")
REPO_NAME = os.getenv("REPO_NAME")
BRANCH_NAME = os.getenv("BRANCH_NAME")
ERROR_MESSAGE = os.getenv("ERROR_MESSAGE")

# Jules API Base URL
BASE_URL = "https://jules.googleapis.com/v1alpha"
HEADERS = {
    "X-Goog-Api-Key": JULES_API_KEY,
    "Content-Type": "application/json"
}

def find_active_session():
    """Searches for an existing Active/Paused session for the current branch."""
    list_url = f"{BASE_URL}/sessions"

    # NOTE: The API may not allow filtering by branch directly via query parameters.
    # If not, you must fetch all sessions and filter them client-side.
    # We'll assume client-side filtering based on the 'sourceContext' in the response.
    print(f"Searching for active sessions in {REPO_NAME} on branch {BRANCH_NAME}...")

    try:
        response = requests.get(list_url, headers=HEADERS, params={"pageSize": 50})
        response.raise_for_status()
        sessions_data = response.json().get("sessions", [])
    except requests.exceptions.RequestException as e:
        print(f"Error listing sessions: {e}")
        return None

    for session in sessions_data:
        # Check repository match
        source = session.get("sourceContext", {}).get("source", "")
        if REPO_NAME in source:
            # Check branch match
            github_context = session.get("sourceContext", {}).get("githubRepoContext", {})
            starting_branch = github_context.get("startingBranch")

            if starting_branch == BRANCH_NAME:
                state = session.get("state")
                # The 'state' is the key—we are only interested in active/paused sessions
                if state in ["ACTIVE", "PAUSED", "PLANNING"]:
                    print(f"Found existing session: {session['name']} in state {state}")
                    return session['name']

    print("No active or paused session found for this branch.")
    return None

def send_fix_message(session_name):
    """Sends a message to an existing session to resume work."""
    send_message_url = f"{BASE_URL}/{session_name}:sendMessage"

    prompt = (
        f"[Automated CI Message] The Continuous Integration (CI) pipeline failed after a new commit was pushed to this branch. "
        f"**Please analyze the codebase and push a fix commit to this existing branch (`{BRANCH_NAME}`).** "
        f"The CI reported the following issues:\n\n{ERROR_MESSAGE}\n\n"
        f"Please address all reported failures (linting, building, testing/coverage) in a new commit."
    )

    payload = {"message": prompt}

    print(f"Sending message to session {session_name} to initiate fix...")
    try:
        response = requests.post(send_message_url, headers=HEADERS, json=payload)
        response.raise_for_status()
        print("Successfully sent fix message to existing session.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        # Log error but don't fail the CI step itself
        pass

if __name__ == "__main__":
    if not JULES_API_KEY or not REPO_NAME or not BRANCH_NAME:
        print("ERROR: Missing required environment variables (API Key, Repo, or Branch). Skipping Jules Fix.")
        exit(0)

    # 1. Check for an existing session
    session_id = find_active_session()

    if session_id:
        # 2. If session exists, send a new message to resume/steer it
        send_fix_message(session_id)
    else:
        # 3. If no session exists, this is the time to create a new one,
        # but based on your request, we skip this step to avoid task limits.
        print("Task not started. If needed, a new session would be created here, which would consume a task quota.")
