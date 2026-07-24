import json
import os
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


API_URL = os.environ.get("ZABBIX_API_URL", "http://zabbix-web:8080/api_jsonrpc.php")
USERNAME = os.environ.get("ZABBIX_USERNAME", "Admin")
PASSWORD = os.environ.get("ZABBIX_PASSWORD", "zabbix")
IMPORT_FILE = Path(os.environ.get("ZABBIX_IMPORT_FILE", "/opt/zabbix/exports/hw12-web-monitor-template.yaml"))
HOST_GROUP = os.environ.get("ZABBIX_HOST_GROUP", "HW12")
HOST_NAME = os.environ.get("ZABBIX_HOST_NAME", "hw12-web-monitor")
VISIBLE_NAME = os.environ.get("ZABBIX_VISIBLE_NAME", "HW12 Web Monitor")
TEMPLATE_NAME = os.environ.get("ZABBIX_TEMPLATE_NAME", "HW12 Website Monitoring Template")
MAX_ATTEMPTS = int(os.environ.get("ZABBIX_BOOTSTRAP_MAX_ATTEMPTS", "120"))
SLEEP_SECONDS = int(os.environ.get("ZABBIX_BOOTSTRAP_SLEEP_SECONDS", "5"))


def api_request(method, params=None, token=None):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1,
    }
    headers = {"Content-Type": "application/json-rpc"}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "error" in result:
        error = result["error"]
        message = error.get("data") or error.get("message") or json.dumps(error)
        raise RuntimeError(f"{method} failed: {message}")

    return result.get("result")


def wait_for_api():
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            version = api_request("apiinfo.version")
            print(f"Zabbix API is ready: {version}", flush=True)
            return
        except (RuntimeError, URLError, TimeoutError, OSError) as error:
            last_error = error
            print(f"Waiting for Zabbix API attempt {attempt}/{MAX_ATTEMPTS}: {error}", flush=True)
            time.sleep(SLEEP_SECONDS)

    raise RuntimeError(f"Zabbix API did not become ready: {last_error}")


def import_template(token):
    source = IMPORT_FILE.read_text(encoding="utf-8")
    rules = {
        "template_groups": {"createMissing": True, "updateExisting": True},
        "templates": {"createMissing": True, "updateExisting": True},
        "httptests": {"createMissing": True, "updateExisting": True},
        "triggers": {"createMissing": True, "updateExisting": True},
        "templateLinkage": {"createMissing": True},
    }

    api_request(
        "configuration.import",
        {
            "format": "yaml",
            "rules": rules,
            "source": source,
        },
        token,
    )
    print(f"Imported template from {IMPORT_FILE}", flush=True)


def ensure_host_group(token):
    groups = api_request("hostgroup.get", {"output": ["groupid"], "filter": {"name": [HOST_GROUP]}}, token)

    if groups:
        return groups[0]["groupid"]

    result = api_request("hostgroup.create", {"name": HOST_GROUP}, token)
    group_id = result["groupids"][0]
    print(f"Created host group {HOST_GROUP}", flush=True)
    return group_id


def get_template(token):
    templates = api_request("template.get", {"output": ["templateid"], "filter": {"host": [TEMPLATE_NAME]}}, token)

    if not templates:
        raise RuntimeError(f"Template not found after import: {TEMPLATE_NAME}")

    return templates[0]["templateid"]


def ensure_host(token, group_id, template_id):
    hosts = api_request("host.get", {"output": ["hostid"], "filter": {"host": [HOST_NAME]}}, token)
    payload = {
        "host": HOST_NAME,
        "name": VISIBLE_NAME,
        "groups": [{"groupid": group_id}],
        "templates": [{"templateid": template_id}],
        "status": 0,
    }

    if hosts:
        host_id = hosts[0]["hostid"]
        api_request("host.update", {"hostid": host_id, **payload}, token)
        print(f"Updated host {HOST_NAME}", flush=True)
        return host_id

    result = api_request("host.create", payload, token)
    host_id = result["hostids"][0]
    print(f"Created host {HOST_NAME}", flush=True)
    return host_id


def main():
    wait_for_api()
    token = api_request("user.login", {"username": USERNAME, "password": PASSWORD})
    import_template(token)
    group_id = ensure_host_group(token)
    template_id = get_template(token)
    host_id = ensure_host(token, group_id, template_id)
    print(f"HW12 Zabbix bootstrap completed for host ID {host_id}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"HW12 Zabbix bootstrap failed: {error}", file=sys.stderr, flush=True)
        sys.exit(1)
