# Starter Pack 文件映射

## V1 必上
- sql/001_task_control_plane.sql
- config/runtime.yaml
- config/policies/*
- config/agents/*
- config/openclaw/*
- schemas/agent_result.schema.json
- schemas/task_state.schema.json
- schemas/handoff.schema.json
- templates/tasks/*
- templates/reports/*

## V1.5 / 稳定化
- env/*
- config/dashboards/push_rules.yaml
- agent-specific schema files

## V2 / Temporal 落地
- config/temporal/workflow_topology.yaml
- config/temporal/queues.yaml
- docker/docker-compose.temporal.dev.yaml
