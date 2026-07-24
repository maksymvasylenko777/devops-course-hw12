# HW12: Zabbix Web Monitoring

## Goal

Run Zabbix with Docker Compose and create a web scenario for monitoring a website.

## Structure

```text
HW12/
  docker-compose.yml
  .env.example
  exports/
    hw12-web-monitor-template.yaml
  scripts/
    bootstrap-zabbix.py
```

## Start Zabbix

Create local environment file:

```bash
cp .env.example .env
```

Start services:

```bash
docker compose up -d
```

Check services:

```bash
docker compose ps
```

Check bootstrap logs:

```bash
docker compose logs zabbix-bootstrap
```

Open Zabbix:

```text
http://localhost:8085
```

Default Zabbix login:

```text
Admin
zabbix
```

## Web Scenario

The `zabbix-bootstrap` service automatically imports [exports/hw12-web-monitor-template.yaml](exports/hw12-web-monitor-template.yaml), creates the `HW12` host group, creates the `hw12-web-monitor` host, and links the imported template.

Verify in Zabbix UI:

```text
Data collection -> Hosts -> hw12-web-monitor
Web scenarios -> Google homepage availability
Triggers -> Google homepage is unavailable
Monitoring -> Hosts -> hw12-web-monitor
```

## Stop Zabbix

Stop services without deleting the database volume:

```bash
docker compose down
```

Delete services and database volume:

```bash
docker compose down -v
```
