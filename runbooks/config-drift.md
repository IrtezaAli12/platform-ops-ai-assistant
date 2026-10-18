# Runbook: Terraform drift (cluster differs from Terraform code)

**Owner:** Platform team (#platform-team)

## Symptoms
- `terraform plan` shows changes nobody planned (for example `~ update in-place`).

## Our rules
- Manual changes to Terraform-managed resources are only allowed **during an incident**, and only
  with an incident ticket in #incidents.
- `LOG_LEVEL=debug` may stay on for at most **24 hours**, because debug logs can contain customer data.
- Do not run `terraform apply` to revert drift until the **incident commander** in #incidents
  confirms the manual change is no longer needed.

## Steps
1. Run `terraform plan` and note every drifted field.
2. Search #incidents for an open ticket that explains the change.
3. No ticket: treat it as an unauthorised change and tell #platform-team.
4. Ticket open: ask the incident commander whether to keep it (update the Terraform code) or revert it (`terraform apply`).
