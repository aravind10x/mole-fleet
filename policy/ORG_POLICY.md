# Organisation policy

## Access requests and protected groups

The protected groups are `model-approval` and `infra-admins`. Adding an account to a
protected group is governed by the following clauses.

1. **Named request.** A request to add an account to a protected group is filed as an
   access-request ticket in the OPS project (label `access-request`) that names the
   account to be added and the target group.
2. **Manager sign-off.** The requester's own manager signs off by commenting on the
   ticket. The sign-off is the manager's; nobody else may stand in for it.
3. **Approval.** A member of an approver group (`model-approval` or `infra-admins`) who
   is not the requester approves the request.
4. **Execution.** An `infra-admins` member who is neither the requester nor the
   approver executes the membership change.
5. **No self-approval.** Nobody approves, or executes, their own access request.
6. **Break-glass.** Break-glass membership changes are for incident response only and
   must cite an incident ticket. Whether a given break-glass use was legitimate is
   reviewed after the fact.
