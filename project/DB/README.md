# GreenField AgroWorks Database

## Overview

This database is designed for the GreenField AgroWorks MCP Project.

It stores information about:

- Farms
- Fields
- Crops
- Chemicals
- Workers
- Chemical Application Requests
- Approval Records
- Safety Policies

The database supports safe AI-assisted farm management through an MCP Server.

---

## Tables

### Farms
Stores information about company farms.

### Fields
Stores farm fields and the crops planted in each field.

### Crops
Stores crop information and growth stages.

### Chemicals
Stores chemical information.

Important fields:
- is_restricted
- reentry_hours

Restricted chemicals require approval before use.

### Workers
Stores employee information.

Important field:
- is_certified

Only certified workers can approve restricted chemical requests.

### Chemical_Applications

Stores all spraying requests.

Status values:
- Pending
- Approved
- Rejected
- Completed

### Approvals

Stores approval decisions made by certified workers.

### Safety_Policies

Stores company safety rules that can be exposed as MCP Resources.

---

## Database Safety

The database supports MCP safety requirements by storing:

- Restricted chemicals
- Certified workers
- Approval workflow
- Application status
- Safety policies

The MCP Server uses these tables to decide whether an action requires human approval.

---

## Files

- schema.sql
- seed.sql
- ERD.png
- README.md