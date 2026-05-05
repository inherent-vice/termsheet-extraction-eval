# Security Policy

## Supported scope

This repository is a sanitized reference architecture for evaluating LLM-extracted structured financial data. It intentionally ships only synthetic fixtures and deterministic mock extraction data.

## Reporting a vulnerability

Please report security issues through GitHub Issues with a minimal reproduction and mark the report as security-related. Do not include real customer data, proprietary term sheets, API keys, credentials, private prompts, or database connection details in the report.

## Data and credential handling

- No proprietary KAP data is included.
- No production SQL Server schemas, private prompts, or customer documents are included.
- Optional provider integrations must read credentials from environment variables or local secret stores.
- Never commit `.env`, provider API keys, connection strings, screenshots containing private data, or generated artifacts derived from real term sheets.

## Intended use

This project is intended for portfolio review, local experimentation, and architecture discussion. It is not a production valuation or audit system.
