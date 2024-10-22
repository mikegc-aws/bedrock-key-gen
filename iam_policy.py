import boto3
from datetime import datetime, timezone

class IAMPolicy:
    def __init__(self, policy_name, policy_document=None, description=None):
        self.policy_name = policy_name
        self.iam_client = boto3.client('iam')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.policy = self._get_policy()

        if self.policy is None and policy_document:
            self.create(policy_document, description)

    def _get_policy(self):
        try:
            response = self.iam_client.get_policy(PolicyArn=f"arn:aws:iam::{self.account_id}:policy/{self.policy_name}")
            return response['Policy']
        except self.iam_client.exceptions.NoSuchEntityException:
            return None

    def create(self, policy_document, description=None):
        if self.policy is None:
            try:
                params = {
                    'PolicyName': self.policy_name,
                    'PolicyDocument': policy_document
                }
                if description:
                    params['Description'] = description

                print(f"Creating policy {self.policy_name} with document: {policy_document}")

                response = self.iam_client.create_policy(**params)
                self.policy = response['Policy']
                print(f"Policy {self.policy_name} created successfully.")
            except Exception as e:
                print(f"Error creating policy {self.policy_name}: {str(e)}")
        else:
            print(f"Policy {self.policy_name} already exists.")

    def read(self):
        if self.policy:
            return self.policy
        else:
            print(f"Policy {self.policy_name} does not exist.")
            return None

    def update(self, policy_document):
        if self.policy:
            try:
                response = self.iam_client.create_policy_version(
                    PolicyArn=self.policy['Arn'],
                    PolicyDocument=policy_document,
                    SetAsDefault=True
                )
                self.policy = self._get_policy()  # Refresh policy info
                print(f"Policy {self.policy_name} updated successfully.")
            except Exception as e:
                print(f"Error updating policy {self.policy_name}: {str(e)}")
        else:
            print(f"Policy {self.policy_name} does not exist.")

    def delete(self):
        if self.policy:
            try:
                # Delete all non-default versions first
                versions = self.iam_client.list_policy_versions(PolicyArn=self.policy['Arn'])['Versions']
                for version in versions:
                    if not version['IsDefaultVersion']:
                        self.iam_client.delete_policy_version(
                            PolicyArn=self.policy['Arn'],
                            VersionId=version['VersionId']
                        )
                
                # Now delete the policy
                self.iam_client.delete_policy(PolicyArn=self.policy['Arn'])
                self.policy = None
                print(f"Policy {self.policy_name} deleted successfully.")
                return True
            except Exception as e:
                print(f"Error deleting policy {self.policy_name}: {str(e)}")
                return False
        else:
            print(f"Policy {self.policy_name} does not exist.")
            return True  # Consider it deleted if it doesn't exist

    def summary(self):
        if self.policy:
            try:
                policy_version = self.iam_client.get_policy_version(
                    PolicyArn=self.policy['Arn'],
                    VersionId=self.policy['DefaultVersionId']
                )['PolicyVersion']
                
                policy_document = policy_version['Document']
                summary = []

                for statement in policy_document.get('Statement', []):
                    effect = statement.get('Effect', '').upper()
                    action = ', '.join(statement.get('Action', [])) if isinstance(statement.get('Action'), list) else statement.get('Action', '')
                    resources = statement.get('Resource', [])
                    if not isinstance(resources, list):
                        resources = [resources]

                    summary.append(f"{effect}: {action}")
                    for resource in resources:
                        summary.append(f"- {resource}")

                    condition = statement.get('Condition', {})
                    date_less_than = condition.get('DateLessThan', {}).get('aws:CurrentTime')
                    if date_less_than:
                        expiration_time = datetime.strptime(date_less_than, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                        current_time = datetime.now(timezone.utc)
                        if expiration_time > current_time:
                            time_left = expiration_time - current_time
                            hours_left, remainder = divmod(time_left.total_seconds(), 3600)
                            minutes_left = remainder // 60
                            summary.append(f"🕒 Expires in {int(hours_left)} hours and {int(minutes_left)} minutes.")
                        else:
                            summary.append("EXPIRED")

                return f"{self.policy_name}\n" + "\n".join(summary) + "\n"
            except Exception as e:
                return f"Error retrieving policy summary: {str(e)}"
        else:
            return f"Policy {self.policy_name} does not exist."

    def delete_all_policies(self):
        policies_to_delete = self.policies.copy()
        for policy in policies_to_delete:
            try:
                if self.remove_policy(policy.policy_name) and policy.delete():
                    print(f"Policy {policy.policy_name} deleted successfully.")
                else:
                    print(f"Failed to delete policy {policy.policy_name}")
            except Exception as e:
                print(f"Error deleting policy {policy.policy_name}: {str(e)}")
        
        # Double-check if all policies were deleted
        remaining_policies = self.get_policies()
        if remaining_policies:
            print(f"Warning: {len(remaining_policies)} policies could not be deleted.")
            for policy in remaining_policies:
                print(f"- {policy.policy_name}")
        else:
            print("All policies have been successfully deleted.")
