# Runbook: worker crashes because DATABASE_URL is missing

**Owner:** Data team (#data-oncall)

## Symptoms
- `worker` pods in `CrashLoopBackOff`, exit code 1.
- Logs say `ERROR: DATABASE_URL is not set`.

## Our rules
- `DATABASE_URL` must ALWAYS come from the Kubernetes Secret `worker-db` (key `DATABASE_URL`)
  in the same namespace. Never put a connection string directly in a manifest or in `kubectl set env`.
- The `worker-db` Secret is created and rotated by the **data team** from the company vault.
  The platform team must not create or edit it.

## Steps
1. Check the Secret exists: `kubectl get secret worker-db -n <namespace>`.
2. If it is missing, page **#data-oncall** and ask them to provision `worker-db` for that namespace.
3. Make sure the worker Deployment references it with `valueFrom.secretKeyRef`
   (name `worker-db`, key `DATABASE_URL`). Change it via pull request to `k8s/`.
4. After the Secret exists and the Deployment references it, the pod restarts on its own.
