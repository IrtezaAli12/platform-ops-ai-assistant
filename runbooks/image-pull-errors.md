# Runbook: ImagePullBackOff / ErrImagePull

**Owner:** Platform team (#platform-team)

## Symptoms
- Pod status `ImagePullBackOff` or `ErrImagePull`.
- Events say `Failed to pull image ... not found` or `unauthorized`.

## Our rules
- Only images from the **approved list** may run. For nginx the approved tag is `nginx:1.27-alpine`.
- Never fix image tags with `kubectl set image` or `kubectl edit`. All image changes go through a
  pull request to the `k8s/` folder in the platform-ops repo, so the change is reviewed and tracked.

## Steps
1. Run `kubectl describe pod` and read the `Image:` line and the Events.
2. `not found`: the tag is wrong. Compare it with the approved list (typos like `alpinee` are common).
3. `unauthorized`: the registry needs credentials. Ask in #platform-team; never paste registry passwords into a manifest.
4. Open a pull request with the corrected tag and tag @platform-team for review.
